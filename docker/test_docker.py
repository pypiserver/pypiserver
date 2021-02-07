"""Tests for the Pypiserver Docker image."""

import contextlib
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import typing as t
from pathlib import Path

import httpx
import pypiserver
import pytest


THIS_DIR = Path(__file__).parent
ROOT_DIR = THIS_DIR.parent
DOCKERFILE = ROOT_DIR / "Dockerfile"
FIXTURES = ROOT_DIR / "fixtures"
MYPKG_ROOT = FIXTURES / "mypkg"
HTPASS_FILE = FIXTURES / "htpasswd.a.a"


# This is largely useless when using pytest because of the need to use the name
# of the fixture as an argument to the test function or fixture using it
# pylint: disable=redefined-outer-name
#
# Also useless for our test context, where we may want to group test functions
# in a class to share common fixtures, but where we don't care about the
# `self` instance.
# pylint: disable=no-self-use


@pytest.fixture(scope="session")
def image() -> str:
    """Build the docker image for pypiserver.

    Return the tag.
    """
    tag = "pypiserver:test"
    run(
        "docker",
        "build",
        "--file",
        str(DOCKERFILE),
        "--tag",
        tag,
        str(ROOT_DIR),
        cwd=ROOT_DIR,
    )
    return tag


@pytest.fixture(scope="session")
def mypkg_build() -> None:
    """Ensure the mypkg test fixture package is build."""
    # Use make for this so that it will skip the build step if it's not needed
    run("make", "mypkg", cwd=ROOT_DIR)


@pytest.fixture(scope="session")
def mypkg_paths(
    mypkg_build: None,  # pylint: disable=unused-argument
) -> t.Dict[str, Path]:
    """The path to the mypkg sdist file."""
    dist_dir = Path(MYPKG_ROOT) / "dist"
    assert dist_dir.exists()

    sdist = dist_dir / "pypiserver_mypkg-1.0.0.tar.gz"
    assert sdist.exists()

    wheel = dist_dir / "pypiserver_mypkg-1.0.0-py2.py3-none-any.whl"
    assert wheel.exists()

    return {
        "dist_dir": dist_dir,
        "sdist": sdist,
        "wheel": wheel,
    }


def wait_for_container(port: int) -> None:
    """Wait for the container to be available."""
    for _ in range(60):
        try:
            httpx.get(f"http://localhost:{port}").raise_for_status()
        except (httpx.RequestError, httpx.HTTPStatusError):
            time.sleep(1)
        else:
            return

    # If we reach here, we've tried 60 times without success, meaning either
    # the container is broken or it took more than about a minute to become
    # functional, either of which cases is something we will want to look into.
    raise RuntimeError("Could not connect to pypiserver container")


def get_socket() -> int:
    """Find a random, open socket and return it."""
    # Close the socket automatically upon exiting the block
    with contextlib.closing(
        socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    ) as sock:
        # Bind to a random open socket >=1024
        sock.bind(("", 0))
        # Return the socket number
        return sock.getsockname()[1]


class RunReturn(t.NamedTuple):
    """Simple wrapper around a simple subprocess call's results."""

    returncode: int
    out: str
    err: str


def run(
    *cmd: str,
    capture: bool = False,
    raise_on_err: bool = True,
    check_code: t.Callable[[int], bool] = lambda c: c == 0,
    **popen_kwargs: t.Any,
) -> RunReturn:
    """Run a command to completion."""
    stdout = subprocess.PIPE if capture else None
    stderr = subprocess.PIPE if capture else None
    proc = subprocess.Popen(cmd, stdout=stdout, stderr=stderr, **popen_kwargs)
    out, err = proc.communicate()
    result = RunReturn(
        proc.returncode,
        "" if out is None else out.decode(),
        "" if err is None else err.decode(),
    )
    if raise_on_err and not check_code(result.returncode):
        raise RuntimeError(result)
    return result


def uninstall_pkgs() -> None:
    """Uninstall any packages we've installed."""
    res = run("pip", "freeze", capture=True)
    if any(
        ln.strip().startswith("pypiserver-mypkg") for ln in res.out.splitlines()
    ):
        run("pip", "uninstall", "-y", "pypiserver-mypkg")


@pytest.fixture(scope="session", autouse=True)
def session_cleanup() -> t.Iterator[None]:
    """Deal with any pollution of the local env."""
    yield
    uninstall_pkgs()


@pytest.fixture()
def cleanup() -> t.Iterator[None]:
    """Clean up after tests that may have affected the env."""
    yield
    uninstall_pkgs()


class TestCommands:
    """Test commands other than `run`."""

    def test_help(self, image: str) -> None:
        """We can get help from the docker container."""
        res = run("docker", "run", image, "--help", capture=True)
        assert "pypi-server" in res.out

    def test_version(self, image: str) -> None:
        """We can get the version from the docker container."""
        res = run("docker", "run", image, "--version", capture=True)
        assert res.out.strip() == pypiserver.__version__


class TestPermissions:
    """Test permission validation, especially with mounted volumes."""

    @pytest.mark.parametrize("perms", (0o706, 0o701, 0o704))
    def test_needs_rx_on_data(self, image: str, perms: int) -> None:
        """Read and execute permissions are required on /data."""
        # Note we can't run this one as root because then we have to make a file
        # that even we can't delete.
        with tempfile.TemporaryDirectory() as tmpdir:
            # Make sure the directory is not readable for anyone other than
            # the owner
            data_dir = Path(tmpdir) / "data"
            data_dir.mkdir(mode=perms)

            res = run(
                "docker",
                "run",
                "--rm",
                "--user",
                # Run as a not us user ID, so access to /data will be
                # determined by the "all other users" setting
                str(os.getuid() + 1),
                "-v",
                # Mount the temporary directory as the /data directory
                f"{data_dir}:/data",
                image,
                capture=True,
                # This should error out, so we check that the code is non-zero
                check_code=lambda c: c != 0,
            )

            assert "must have read/execute access" in res.err

    @pytest.mark.parametrize(
        "extra_args",
        (("--user", str(os.getuid())), ("--user", str(os.getuid() + 1))),
    )
    def test_needs_rwx_on_packages(self, image: str, extra_args: tuple) -> None:
        """RWX permission is required on /data/packages."""
        with tempfile.TemporaryDirectory() as tmpdir:
            td_path = Path(tmpdir)
            # Make the /data directory read/writable by anyone
            td_path.chmod(0o777)
            # Add the /data/packages directory, and make it readable by anyone,
            # but writable only by the owner
            (td_path / "packages").mkdir(mode=0o444)

            res = run(
                "docker",
                "run",
                "--rm",
                *extra_args,
                "-v",
                # Mount the temporary directory as the /data directory
                f"{tmpdir}:/data",
                image,
                capture=True,
                # We should error out in this case
                check_code=lambda c: c != 0,
            )
            assert "must have read/write/execute access" in res.err

    def test_runs_as_pypiserver_user(self, image: str) -> None:
        """Test that the default run uses the pypiserver user."""
        host_port = get_socket()
        res = run(
            "docker",
            "run",
            "--rm",
            "--detach",
            "--publish",
            f"{host_port}:8080",
            image,
            capture=True,
        )
        container_id = res.out.strip()
        try:
            wait_for_container(host_port)
            res = run(
                "docker",
                "container",
                "exec",
                container_id,
                "ps",
                "a",
                capture=True,
            )
            proc_line = next(
                filter(
                    # grab the process line for the pypi-server process
                    lambda ln: "pypi-server" in ln,
                    res.out.splitlines(),
                )
            )
            user = proc_line.split()[1]
            # the ps command on these alpine containers doesn't always show the
            # full user name, so we only check for the first bit
            assert user.startswith("pypi")
        finally:
            run("docker", "container", "rm", "-f", container_id)


class ContainerInfo(t.NamedTuple):
    """Info about a running container"""

    container_id: str
    port: int
    args: tuple


class TestBasics:
    """Test basic pypiserver functionality in a simple unauthed container."""

    # We want to automatically parametrize this class' tests with a variety of
    # pypiserver args, since it should work the same in all of these cases
    @pytest.fixture(
        scope="class",
        params=[
            # default (gunicorn) server with cached backend
            (),
            # default (gunicorn) server with non-cached backend
            ("--backend", "simple-dir"),
            # explicit gunicorn server with a non-cached backend
            ("--server", "gunicorn", "--backend", "simple-dir"),
            # explicit gunicorn server
            ("--server", "gunicorn"),
            # explicit waitress server
            ("--server", "wsgiref"),
            # explicit wsgiref server
            ("--server", "wsgiref"),
        ],
    )
    def container(
        self, request: pytest.FixtureRequest, image: str
    ) -> t.Iterator[ContainerInfo]:
        """Run the pypiserver container.

        Returns the container ID.
        """
        port = get_socket()
        args = (
            "docker",
            "run",
            "--rm",
            "--publish",
            f"{port}:8080",
            "--detach",
            image,
            "run",
            "--passwords",
            ".",
            "--authenticate",
            ".",
            *request.param,  # type: ignore
        )
        res = run(*args, capture=True)
        wait_for_container(port)
        container_id = res.out.strip()
        yield ContainerInfo(container_id, port, args)
        run("docker", "container", "rm", "-f", container_id)

    @pytest.fixture(scope="class")
    def upload_mypkg(
        self,
        container: ContainerInfo,
        mypkg_paths: t.Dict[str, Path],
    ) -> None:
        """Upload mypkg to the container."""
        run(
            sys.executable,
            "-m",
            "twine",
            "upload",
            "--repository-url",
            f"http://localhost:{container.port}",
            "--username",
            "",
            "--password",
            "",
            f"{mypkg_paths['dist_dir']}/*",
        )

    @pytest.mark.usefixtures("upload_mypkg")
    def test_download(self, container: ContainerInfo) -> None:
        """Download mypkg from the container."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run(
                sys.executable,
                "-m",
                "pip",
                "download",
                "--index-url",
                f"http://localhost:{container.port}/simple",
                "--dest",
                tmpdir,
                "pypiserver_mypkg",
            )
            assert any(
                "pypiserver_mypkg" in path.name
                for path in Path(tmpdir).iterdir()
            )

    @pytest.mark.usefixtures("upload_mypkg", "cleanup")
    def test_install(self, container: ContainerInfo) -> None:
        """Install mypkg from the container.

        Note this also ensures that name normalization is working,
        since we are requesting the package name with a dash, rather
        than an underscore.
        """
        run(
            sys.executable,
            "-m",
            "pip",
            "install",
            "--index-url",
            f"http://localhost:{container.port}/simple",
            "pypiserver-mypkg",
        )
        run("python", "-c", "'import pypiserver_mypkg; mypkg.pkg_name()'")

    def test_expected_server(self, container: ContainerInfo) -> None:
        """Ensure we run the server we think we're running."""
        resp = httpx.get(f"http://localhost:{container.port}")
        server = resp.headers["server"].lower()
        arg_pairs = tuple(zip(container.args, container.args[1:]))
        if (
            container.args[-1] == "pypiserver:test"
            or ("--server", "gunicorn") in arg_pairs
        ):
            # We specified no overriding args, so we should run gunicorn, or
            # we specified gunicorn in overriding args.
            assert "gunicorn" in server
        elif ("--server", "wsgiref") in arg_pairs:
            # We explicitly specified the wsgiref server
            assert "wsgiserver" in server
        elif ("--server", "waitress") in arg_pairs:
            # We explicitly specified the wsgiref server
            assert "waitress" in server
        else:
            # We overrode args, so instead of using the gunicorn default,
            # we use the `auto` option. Bottle won't choose gunicorn as an
            # auto server, so we have waitress installed in the docker container
            # as a fallback for these scenarios, since wsgiref is not production
            # ready
            assert "waitress" in server

    def test_welcome(self, container: ContainerInfo) -> None:
        """View the welcome page."""
        resp = httpx.get(f"http://localhost:{container.port}")
        assert resp.status_code == 200
        assert "pypiserver" in resp.text


class TestAuthed:
    """Test basic pypiserver functionality in a simple unauthed container."""

    HOST_PORT = get_socket()

    @pytest.fixture(scope="class")
    def container(self, image: str) -> t.Iterator[str]:
        """Run the pypiserver container.

        Returns the container ID.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            dirpath = Path(tmpdir)
            shutil.copy2(HTPASS_FILE, dirpath / "htpasswd")
            pkg_path = dirpath / "packages"
            pkg_path.mkdir(mode=0o777)

            res = run(
                "docker",
                "run",
                "--rm",
                "--publish",
                f"{self.HOST_PORT}:8080",
                "-v",
                f"{dirpath / 'htpasswd'}:/data/htpasswd",
                "--detach",
                image,
                "run",
                "--passwords",
                "/data/htpasswd",
                "--authenticate",
                "download, update",
                capture=True,
            )
            wait_for_container(self.HOST_PORT)
            container_id = res.out.strip()
            yield container_id
            run("docker", "container", "rm", "-f", container_id)

    @pytest.fixture(scope="class")
    def upload_mypkg(
        self,
        container: str,  # pylint: disable=unused-argument
        mypkg_paths: t.Dict[str, Path],
    ) -> None:
        """Upload mypkg to the container."""
        run(
            sys.executable,
            "-m",
            "twine",
            "upload",
            "--repository-url",
            f"http://localhost:{self.HOST_PORT}",
            "--username",
            "a",
            "--password",
            "a",
            f"{mypkg_paths['dist_dir']}/*",
        )

    def test_upload_failed_auth(
        self,
        container: str,  # pylint: disable=unused-argument
        mypkg_paths: t.Dict[str, Path],
    ) -> None:
        """Upload mypkg to the container."""
        run(
            sys.executable,
            "-m",
            "twine",
            "upload",
            "--repository-url",
            f"http://localhost:{self.HOST_PORT}",
            f"{mypkg_paths['dist_dir']}/*",
            check_code=lambda c: c != 0,
        )

    @pytest.mark.usefixtures("upload_mypkg")
    def test_download(self) -> None:
        """Download mypkg from the container."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run(
                sys.executable,
                "-m",
                "pip",
                "download",
                "--index-url",
                f"http://a:a@localhost:{self.HOST_PORT}/simple",
                "--dest",
                tmpdir,
                "pypiserver_mypkg",
            )
            assert any(
                "pypiserver_mypkg" in path.name
                for path in Path(tmpdir).iterdir()
            )

    @pytest.mark.usefixtures("upload_mypkg")
    def test_download_failed_auth(self) -> None:
        """Download mypkg from the container."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run(
                sys.executable,
                "-m",
                "pip",
                "download",
                "--index-url",
                f"http://foo:bar@localhost:{self.HOST_PORT}/simple",
                "--dest",
                tmpdir,
                "pypiserver_mypkg",
                check_code=lambda c: c != 0,
            )

    @pytest.mark.usefixtures("upload_mypkg", "cleanup")
    def test_install(self) -> None:
        """Install mypkg from the container.

        Note this also ensures that name normalization is working,
        since we are requesting the package name with a dash, rather
        than an underscore.
        """
        run(
            sys.executable,
            "-m",
            "pip",
            "install",
            "--index-url",
            f"http://a:a@localhost:{self.HOST_PORT}/simple",
            "pypiserver-mypkg",
        )
        run("python", "-c", "'import pypiserver_mypkg; mypkg.pkg_name()'")

    @pytest.mark.usefixtures("upload_mypkg", "cleanup")
    def test_install_failed_auth(self) -> None:
        """Install mypkg from the container.

        Note this also ensures that name normalization is working,
        since we are requesting the package name with a dash, rather
        than an underscore.
        """
        run(
            sys.executable,
            "-m",
            "pip",
            "install",
            "--no-cache",
            "--index-url",
            f"http://localhost:{self.HOST_PORT}/simple",
            "pypiserver-mypkg",
            check_code=lambda c: c != 0,
        )

    def test_welcome(self) -> None:
        """View the welcome page."""
        resp = httpx.get(f"http://localhost:{self.HOST_PORT}")
        assert resp.status_code == 200
        assert "pypiserver" in resp.text
