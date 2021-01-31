"""Tests for the Pypiserver Docker image."""

import os
import shutil
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
    proc = subprocess.Popen(
        ("docker", "build", "--file", str(DOCKERFILE), "--tag", tag, ROOT_DIR),
        cwd=ROOT_DIR,
    )
    proc.communicate()
    assert proc.returncode == 0
    return tag


@pytest.fixture(scope="session")
def mypkg_build() -> None:
    """Ensure the mypkg test fixture package is build."""
    # Use make for this so that it will skip the build step if it's not needed
    proc = subprocess.Popen(("make", "mypkg"), cwd=ROOT_DIR)
    proc.communicate()
    assert proc.returncode == 0


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

    # If we reach here, we've tried 20 times without success.
    raise RuntimeError("Could not connect to pypiserver container")


def uninstall_pkgs() -> None:
    """Uninstall any packages we've installed."""
    proc = subprocess.Popen(
        ("pip", "freeze"), stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    out, err = proc.communicate()
    assert proc.returncode == 0, err and f"{err.decode()}"
    if any(
        ln.strip().startswith("pypiserver-mypkg")
        for ln in out.decode().splitlines()
    ):
        proc = subprocess.Popen(("pip", "uninstall", "-y", "pypiserver-mypkg"))
        proc.communicate()


@pytest.fixture(scope="session")
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
        proc = subprocess.Popen(
            ("docker", "run", image, "--help"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        out, err = proc.communicate()
        assert proc.returncode == 0, err and f"{err.decode()}"
        assert "pypi-server" in out.decode()

    def test_version(self, image: str) -> None:
        """We can get the version from the docker container."""
        proc = subprocess.Popen(
            ("docker", "run", image, "--version"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        out, err = proc.communicate()
        assert proc.returncode == 0, err and f"{err.decode()}"
        assert out.decode().strip() == pypiserver.__version__


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

            proc = subprocess.Popen(
                (
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
                ),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            _, err = proc.communicate()

            # we should error out in this case
            assert proc.returncode != 0
            assert "must have read/execute access" in err.decode()

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

            proc = subprocess.Popen(
                (
                    "docker",
                    "run",
                    "--rm",
                    *extra_args,
                    "-v",
                    # Mount the temporary directory as the /data directory
                    f"{tmpdir}:/data",
                    image,
                ),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            _, err = proc.communicate()
            # we should error out in this case
            assert proc.returncode != 0
            assert "must have read/write/execute access" in err.decode()

    def test_runs_as_pypiserver_user(self, image: str) -> None:
        """Test that the default run uses the pypiserver user."""
        proc = subprocess.Popen(
            (
                "docker",
                "run",
                "--rm",
                "--detach",
                "--publish",
                "8080:8080",
                image,
            ),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        out, err = proc.communicate()
        # we should error out in this case
        assert proc.returncode == 0, err and f"{err.decode()}"
        container_id = out.decode().strip()
        try:
            wait_for_container(8080)
            proc = subprocess.Popen(
                ("docker", "container", "exec", container_id, "ps", "a"),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            out, err = proc.communicate()
            assert proc.returncode == 0, err and f"{err.decode()}"
            proc_line = next(
                filter(
                    # grab the process line for the pypi-server process
                    lambda ln: "pypi-server" in ln,
                    map(bytes.decode, out.splitlines()),
                )
            )
            user = proc_line.split()[1]
            # the ps command on these alpine containers doesn't always show the
            # full user name, so we only check for the first bit
            assert user.startswith("pypi")
        finally:
            subprocess.Popen(
                ("docker", "container", "rm", "-f", container_id)
            ).communicate()


class TestBasics:
    """Test basic pypiserver functionality in a simple unauthed container."""

    @pytest.fixture(scope="class")
    def container(self, image: str) -> t.Iterator[str]:
        """Run the pypiserver container.

        Returns the container ID.
        """
        proc = subprocess.Popen(
            (
                "docker",
                "run",
                "--rm",
                "--publish",
                "8080:8080",
                "--detach",
                image,
                "run",
                "--passwords",
                ".",
                "--authenticate",
                ".",
            ),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        out, err = proc.communicate()
        assert proc.returncode == 0, err and f"{err.decode()}"
        wait_for_container(8080)
        container_id = out.strip().decode()
        yield container_id
        proc = subprocess.Popen(
            ("docker", "container", "rm", "-f", container_id)
        )
        proc.communicate()

    @pytest.fixture(scope="class")
    def upload_mypkg(
        self,
        container: str,  # pylint: disable=unused-argument
        mypkg_paths: t.Dict[str, Path],
    ) -> None:
        """Upload mypkg to the container."""
        proc = subprocess.Popen(
            (
                sys.executable,
                "-m",
                "twine",
                "upload",
                "--repository-url",
                "http://localhost:8080",
                "--username",
                "",
                "--password",
                "",
                f"{mypkg_paths['dist_dir']}/*",
            )
        )
        proc.communicate()
        assert proc.returncode == 0

    @pytest.mark.usefixtures("upload_mypkg")
    def test_download(self) -> None:
        """Download mypkg from the container."""
        with tempfile.TemporaryDirectory() as tmpdir:
            proc = subprocess.Popen(
                (
                    sys.executable,
                    "-m",
                    "pip",
                    "download",
                    "--index-url",
                    "http://localhost:8080/simple",
                    "--dest",
                    tmpdir,
                    "pypiserver_mypkg",
                )
            )
            proc.communicate()
            assert proc.returncode == 0
            assert any(
                "pypiserver_mypkg" in path.name
                for path in Path(tmpdir).iterdir()
            )

    @pytest.mark.usefixtures("upload_mypkg", "cleanup")
    def test_install(self) -> None:
        """Install mypkg from the container.

        Note this also ensures that name normalization is working,
        since we are requesting the package name with a dash, rather
        than an underscore.
        """
        proc = subprocess.Popen(
            (
                sys.executable,
                "-m",
                "pip",
                "install",
                "--index-url",
                "http://localhost:8080/simple",
                "pypiserver-mypkg",
            )
        )

        proc.communicate()
        assert proc.returncode == 0
        proc = subprocess.Popen(
            ("python", "-c", "'import pypiserver_mypkg; mypkg.pkg_name()'"),
        )
        proc.communicate()
        assert proc.returncode == 0

    def test_welcome(self) -> None:
        """View the welcome page."""
        resp = httpx.get("http://localhost:8080")
        assert resp.status_code == 200
        assert "pypiserver" in resp.text


class TestAuthed:
    """Test basic pypiserver functionality in a simple unauthed container."""

    HOST_PORT = 8081

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

            proc = subprocess.Popen(
                (
                    "docker",
                    "run",
                    "--rm",
                    "--publish",
                    "8081:8080",
                    "-v",
                    f"{dirpath / 'htpasswd'}:/data/htpasswd",
                    "--detach",
                    image,
                    "run",
                    "--passwords",
                    "/data/htpasswd",
                    "--authenticate",
                    "download, update",
                ),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            out, err = proc.communicate()
            assert proc.returncode == 0, err and f"{err.decode()}"
            wait_for_container(self.HOST_PORT)
            container_id = out.strip().decode()
            yield container_id
            proc = subprocess.Popen(
                (
                    "docker",
                    "container",
                    "exec",
                    container_id,
                    "rm",
                    "-rf",
                    "/data/packages",
                )
            )
            proc = subprocess.Popen(
                ("docker", "container", "rm", "-f", container_id)
            )
            proc.communicate()

    @pytest.fixture(scope="class")
    def upload_mypkg(
        self,
        container: str,  # pylint: disable=unused-argument
        mypkg_paths: t.Dict[str, Path],
    ) -> None:
        """Upload mypkg to the container."""
        proc = subprocess.Popen(
            (
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
        )
        proc.communicate()
        assert proc.returncode == 0

    def test_upload_failed_auth(
        self,
        container: str,  # pylint: disable=unused-argument
        mypkg_paths: t.Dict[str, Path],
    ) -> None:
        """Upload mypkg to the container."""
        proc = subprocess.Popen(
            (
                sys.executable,
                "-m",
                "twine",
                "upload",
                "--repository-url",
                f"http://localhost:{self.HOST_PORT}",
                f"{mypkg_paths['dist_dir']}/*",
            )
        )
        proc.communicate()
        assert proc.returncode != 0

    @pytest.mark.usefixtures("upload_mypkg")
    def test_download(self) -> None:
        """Download mypkg from the container."""
        with tempfile.TemporaryDirectory() as tmpdir:
            proc = subprocess.Popen(
                (
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
            )
            proc.communicate()
            assert proc.returncode == 0
            assert any(
                "pypiserver_mypkg" in path.name
                for path in Path(tmpdir).iterdir()
            )

    @pytest.mark.usefixtures("upload_mypkg")
    def test_download_failed_auth(self) -> None:
        """Download mypkg from the container."""
        with tempfile.TemporaryDirectory() as tmpdir:
            proc = subprocess.Popen(
                (
                    sys.executable,
                    "-m",
                    "pip",
                    "download",
                    "--index-url",
                    f"http://localhost:{self.HOST_PORT}/simple",
                    "--dest",
                    tmpdir,
                    "pypiserver_mypkg",
                )
            )
            proc.communicate()
            assert proc.returncode != 0

    @pytest.mark.usefixtures("upload_mypkg", "cleanup")
    def test_install(self) -> None:
        """Install mypkg from the container.

        Note this also ensures that name normalization is working,
        since we are requesting the package name with a dash, rather
        than an underscore.
        """
        proc = subprocess.Popen(
            (
                sys.executable,
                "-m",
                "pip",
                "install",
                "--index-url",
                f"http://a:a@localhost:{self.HOST_PORT}/simple",
                "pypiserver-mypkg",
            )
        )

        proc.communicate()
        assert proc.returncode == 0
        proc = subprocess.Popen(
            ("python", "-c", "'import pypiserver_mypkg; mypkg.pkg_name()'"),
        )
        proc.communicate()
        assert proc.returncode == 0

    @pytest.mark.usefixtures("upload_mypkg", "cleanup")
    def test_install_failed_auth(self) -> None:
        """Install mypkg from the container.

        Note this also ensures that name normalization is working,
        since we are requesting the package name with a dash, rather
        than an underscore.
        """
        proc = subprocess.Popen(
            (
                sys.executable,
                "-m",
                "pip",
                "install",
                "--no-cache",
                "--index-url",
                f"http://localhost:{self.HOST_PORT}/simple",
                "pypiserver-mypkg",
            )
        )

        proc.communicate()
        assert proc.returncode != 0

    def test_welcome(self) -> None:
        """View the welcome page."""
        resp = httpx.get(f"http://localhost:{self.HOST_PORT}")
        assert resp.status_code == 200
        assert "pypiserver" in resp.text
