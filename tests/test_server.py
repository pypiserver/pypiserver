#! /usr/bin/env py.test
"""
Checks an actual pypi-server against various clients.

The tests below are using 3 ways to startup pypi-servers:

- "open": a per-module server instance without any authed operations,
  serving a single `wheel` package, on a fixed port.
- "open": a per-module server instance with authed 'download/upload'
  operations, serving a single `wheel` package, on a fixed port.
- "new_server": starting a new server with any configurations on each test.

"""

import contextlib
import json
import os
from datetime import UTC, datetime
import shutil
import socket
import re
import sys
import time
import typing as t
from collections import namedtuple
from pathlib import Path
from shlex import split
from subprocess import Popen, run
from urllib.error import URLError
from urllib.request import Request, urlopen

import pytest

# ######################################################################
# Fixtures & Helper Functions
# ######################################################################


CURRENT_PATH = Path(__file__).parent
Srv = namedtuple("Srv", ("port", "root"))


def reserve_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        sock.listen()
        return t.cast(int, sock.getsockname()[1])


@contextlib.contextmanager
def run_server(
    root,
    authed: bool | t.Literal["partial"] = False,
    other_cli="",
):
    """Run a server, optionally with partial auth enabled."""
    htpasswd = (
        CURRENT_PATH.joinpath("../fixtures/htpasswd.a.a").expanduser().resolve()
    )
    pswd_opt_choices = {
        True: f"-P {htpasswd} -a update,download",
        False: "-P. -a.",
        "partial": f"-P {htpasswd} -a update",
    }
    pswd_opts = pswd_opt_choices[authed]

    proc = None
    srv = None
    for _ in range(5):
        port = reserve_port()
        cmd = (
            f"{sys.executable} -m pypiserver.__main__ "
            f"run -vvv --overwrite -i 127.0.0.1 "
            f"-p {port} {pswd_opts} {other_cli} {root}"
        )
        proc = Popen(cmd.split(), bufsize=2**16)
        srv = Srv(port, root)
        try:
            wait_until_ready(srv)
            if proc.poll() is None:
                break
        except TimeoutError:
            pass
        finally:
            if proc.poll() is not None:
                proc.wait()
                proc = None
    else:
        raise TimeoutError("Failed to start test pypiserver")

    assert proc is not None
    assert srv is not None

    try:
        yield srv
    finally:
        print(f"Killing {srv}")
        _kill_proc(proc)


def wait_until_ready(srv: Srv, n_tries=10):
    for _ in range(n_tries):
        if is_ready(srv):
            return True
        time.sleep(0.5)
    raise TimeoutError


def is_ready(srv: Srv):
    try:
        return urlopen(build_url(srv.port), timeout=0.5).getcode() in (
            200,
            401,
        )
    except (URLError, socket.timeout):
        return False


def _kill_proc(proc):
    proc.terminate()
    try:
        proc.wait(timeout=1)
    finally:
        proc.kill()


def build_url(port: t.Union[int, str], user: str = "", pswd: str = "") -> str:
    auth = f"{user}:{pswd}@" if user or pswd else ""
    return f"http://{auth}localhost:{port}"


def run_setup_py(path: Path, arguments: str) -> int:
    return os.system(f"{sys.executable} {path / 'setup.py'} {arguments}")


def run_py_build(srcdir: Path, flags: str) -> int:
    return os.system(f"{sys.executable} -m build {flags} {srcdir}")


# A test-distribution to check if
#    bottle supports uploading 100's of packages,
#    see: https://github.com/pypiserver/pypiserver/issues/82
#
# Has been run once `pip wheel .`, just to generate:
#    ./wheelhouse/centodeps-0.0.0-cp34-none-win_amd64.whl
#
SETUP_PY = """\
from setuptools import setup

setup(
    name="centodeps",
    install_requires=["a==1.0"] * 200,
    options={
        "bdist_wheel": {"universal": True},
    },
    packages=[],
)
"""


@pytest.fixture(scope="module")
def project(tmp_path_factory):
    projdir = tmp_path_factory.mktemp("project") / "centodeps"
    projdir.mkdir(parents=True, exist_ok=True)
    projdir.joinpath("setup.py").write_text(SETUP_PY)
    return projdir


@pytest.fixture(scope="session")
def server_root(tmp_path_factory):
    return tmp_path_factory.mktemp("root")


@pytest.fixture(scope="module")
def wheel_file(project, tmp_path_factory):
    distdir = tmp_path_factory.mktemp("dist")
    if re.match(r"^3\.7", sys.version):
        assert run_setup_py(project, f"bdist_wheel -d {distdir}") == 0
    else:
        assert (
            run_py_build(project, f"--wheel --no-isolation --outdir {distdir}")
            == 0
        )
    wheels = list(distdir.glob("centodeps*.whl"))
    assert len(wheels) > 0
    return wheels[0]


@pytest.fixture()
def hosted_wheel_file(wheel_file, server_root):
    dst = server_root / wheel_file.name
    shutil.copy(wheel_file, dst)
    yield dst
    if dst.is_file():
        dst.unlink()


def clear_directory(root: Path):
    for path in root.iterdir():
        if path.is_file():
            path.unlink()


@pytest.fixture(scope="module")
def _open_server(server_root):
    with run_server(server_root, authed=False) as srv:
        yield srv


@pytest.fixture
def open_server(_open_server: Srv):
    yield _open_server
    clear_directory(_open_server.root)


@pytest.fixture(scope="module")
def _authed_server(server_root):
    with run_server(server_root, authed=True) as srv:
        yield srv


@pytest.fixture
def authed_server(_authed_server):
    yield _authed_server
    clear_directory(_authed_server.root)


@pytest.fixture(scope="module")
def _partial_auth_server(server_root):
    with run_server(server_root, authed="partial") as srv:
        yield srv


@pytest.fixture
def partial_authed_server(_partial_auth_server):
    yield _partial_auth_server
    clear_directory(_partial_auth_server.root)


@pytest.fixture
def empty_packdir(tmp_path_factory):
    return tmp_path_factory.mktemp("dists")


def pip_download(
    cmd: str,
    port: t.Union[int, str],
    install_dir: str,
    user: str = None,
    pswd: str = None,
) -> int:
    url = build_url(port, user, pswd)
    return _run_pip(f"-vv download -d {install_dir} -i {url} {cmd}")


def _run_pip(cmd: str) -> int:
    ncmd = (
        "pip --no-cache-dir --disable-pip-version-check "
        f"--retries 0 --timeout 5 --no-input {cmd}"
    )
    print(f"PIP: {ncmd}")
    proc = Popen(split(ncmd))
    proc.communicate()
    return proc.returncode


@pytest.fixture
def pipdir(tmp_path_factory):
    return tmp_path_factory.mktemp("pip")


@contextlib.contextmanager
def pypirc_file(repo, username="''", password="''"):
    pypirc_path = Path.home() / ".pypirc"
    old_pypirc = pypirc_path.read_text() if pypirc_path.is_file() else None
    pypirc_path.write_text(
        "\n".join(
            (
                "[distutils]",
                "index-servers: test",
                "",
                "[test]",
                f"repository: {repo}",
                f"username: {username}",
                f"password: {password}",
            )
        )
    )
    try:
        yield pypirc_path
    finally:
        if old_pypirc:
            pypirc_path.write_text(old_pypirc)
        else:
            pypirc_path.unlink()


@pytest.fixture
def open_pypirc(open_server):
    with pypirc_file(repo=build_url(open_server.port)) as path:
        yield path


@pytest.fixture
def authed_pypirc(authed_server):
    username, password = "a", "a"
    with pypirc_file(
        repo=build_url(authed_server.port),
        username=username,
        password=password,
    ) as path:
        yield path


def run_twine(
    command: str,
    package: str | Path,
    conf: str | Path,
) -> None:
    run(
        split(f"twine {command} --repository test --config-file {conf} {package}"),
        check=True,
    )


# ######################################################################
# Tests
# ######################################################################

all_servers = [
    ("open_server", "open_pypirc"),
    ("authed_server", "authed_pypirc"),
    ("partial_authed_server", "authed_pypirc"),
]


def test_pip_install_package_not_found(open_server, pipdir):
    assert pip_download("centodeps", open_server.port, pipdir) != 0
    assert not list(pipdir.iterdir())


def test_pip_install_open_succeeds(open_server, hosted_wheel_file, pipdir):
    assert pip_download("centodeps", open_server.port, pipdir) == 0
    assert pipdir.joinpath(hosted_wheel_file.name).is_file()


@pytest.mark.usefixtures("wheel_file")
def test_pip_install_authed_fails(authed_server, pipdir):
    assert pip_download("centodeps", authed_server.port, pipdir) != 0
    assert not list(pipdir.iterdir())


def test_pip_install_authed_succeeds(authed_server, hosted_wheel_file, pipdir):
    assert (
        pip_download(
            "centodeps", authed_server.port, pipdir, user="a", pswd="a"
        )
        == 0
    )
    assert pipdir.joinpath(hosted_wheel_file.name).is_file()


def test_partial_authed_open_download(partial_authed_server):
    """Validate that partial auth still allows downloads."""
    url = build_url(partial_authed_server.port) + "/simple"
    resp = urlopen(url)
    assert resp.getcode() == 200


@pytest.mark.parametrize("hash_algo", ("md5", "sha256", "sha512"))
@pytest.mark.usefixtures("hosted_wheel_file")
def test_hash_algos(server_root, pipdir, hash_algo):
    """Test twine upload with no authentication"""
    with run_server(
        server_root, other_cli="--hash-algo {}".format(hash_algo)
    ) as srv:
        assert pip_download("centodeps", srv.port, pipdir) == 0


@pytest.mark.parametrize(["server_fixture", "pypirc_fixture"], all_servers)
def test_twine_upload(
    server_fixture, pypirc_fixture, server_root, wheel_file, request
):
    """Test twine upload with no authentication"""
    assert len(list(server_root.iterdir())) == 0
    request.getfixturevalue(server_fixture)
    pypirc = request.getfixturevalue(pypirc_fixture)

    run_twine("upload", wheel_file, conf=pypirc)

    package_files = [
        path for path in server_root.iterdir() if not path.name.startswith(".")
    ]
    assert len(package_files) == 1
    assert server_root.joinpath(wheel_file.name).is_file(), (
        wheel_file.name,
        package_files,
    )


@pytest.mark.parametrize(["server_fixture", "pypirc_fixture"], all_servers)
def test_twine_register(server_fixture, pypirc_fixture, wheel_file, request):
    """Test unauthenticated twine registration"""
    request.getfixturevalue(server_fixture)
    pypirc = request.getfixturevalue(pypirc_fixture)
    run_twine("register", wheel_file, conf=pypirc)


def test_twine_upload_json_upload_times_drive_uv_exclude_newer(tmp_path):
    package = "dummy-live-upload"
    older_version = "1.0.0"
    newer_version = "2.0.0"

    def build_wheel(version: str) -> Path:
        project_dir = tmp_path / version
        dist_dir = tmp_path / "dist" / version
        project_dir.mkdir(parents=True, exist_ok=True)
        dist_dir.mkdir(parents=True, exist_ok=True)
        project_dir.joinpath("setup.py").write_text(
            f"from setuptools import setup\n\n"
            f"setup(name={package!r}, version={version!r}, packages=[])\n"
        )
        if re.match(r"^3\.7", sys.version):
            exit_code = run_setup_py(project_dir, f"bdist_wheel -d {dist_dir}")
        else:
            exit_code = run_py_build(
                project_dir,
                f"--wheel --no-isolation --outdir {dist_dir}",
            )
        assert exit_code == 0
        wheels = list(dist_dir.glob("*.whl"))
        assert len(wheels) == 1
        return wheels[0]

    def uv_install_version(
        env_name: str,
        index_url: str,
        allow_host: str,
        exclude_newer: str | None = None,
    ) -> str:
        venv_dir = tmp_path / env_name
        uv_dir = str(venv_dir.parent)
        run(
            [
                "uv",
                "--directory",
                uv_dir,
                "--no-config",
                "venv",
                str(venv_dir),
                "--python",
                sys.executable,
            ],
            check=True,
        )
        args = [
            "uv",
            "--directory",
            uv_dir,
            "--no-config",
            "pip",
            "install",
            "--no-cache",
            "--python",
            str(venv_dir),
            "--index-url",
            index_url,
            "--allow-insecure-host",
            allow_host,
        ]
        if exclude_newer is not None:
            args.extend(["--exclude-newer", exclude_newer])
        args.append(package)
        run(args, check=True)
        python = venv_dir / "bin" / "python"
        cmd = f"import importlib.metadata as md; print(md.version({package!r}))"
        return run(
            [str(python), "-c", cmd],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

    older_wheel = build_wheel(older_version)
    newer_wheel = build_wheel(newer_version)
    server_root = tmp_path / "packages"
    server_root.mkdir()

    with run_server(server_root, other_cli="--disable-fallback") as upload_srv:
        with pypirc_file(repo=build_url(upload_srv.port)) as pypirc:
            run_twine("upload", older_wheel, conf=pypirc)
            run_twine("upload", newer_wheel, conf=pypirc)

    sidecar_path = server_root / ".pypiserver-upload-times.json"
    assert sidecar_path.is_file()
    stored_upload_times = json.loads(sidecar_path.read_text())
    assert stored_upload_times[older_wheel.name] < stored_upload_times[newer_wheel.name]

    older_uploaded = server_root / older_wheel.name
    newer_uploaded = server_root / newer_wheel.name
    os.utime(older_uploaded, (1700000200, 1700000200))
    os.utime(newer_uploaded, (1700000100, 1700000100))

    with run_server(server_root, other_cli="--disable-fallback") as install_srv:
        request = Request(
            f"{build_url(install_srv.port)}/simple/{package}/",
            headers={"Accept": "application/vnd.pypi.simple.v1+json"},
        )
        with urlopen(request) as response:
            assert response.getcode() == 200
            body = json.load(response)
        assert body["meta"] == {"api-version": "1.4"}
        assert body["name"] == package
        assert body["versions"] == [older_version, newer_version]
        files_by_name = {item["filename"]: item for item in body["files"]}
        older_file = files_by_name[older_wheel.name]
        newer_file = files_by_name[newer_wheel.name]
        assert older_file["upload-time"] == stored_upload_times[older_wheel.name]
        assert newer_file["upload-time"] == stored_upload_times[newer_wheel.name]
        older_time = datetime.fromisoformat(
            older_file["upload-time"].replace("Z", "+00:00")
        )
        newer_time = datetime.fromisoformat(
            newer_file["upload-time"].replace("Z", "+00:00")
        )
        assert older_time.tzinfo == UTC
        assert newer_time.tzinfo == UTC
        assert older_time < newer_time
        cutover = older_time + (newer_time - older_time) / 2
        cutoff = cutover.isoformat().replace("+00:00", "Z")
        index_url = f"{build_url(install_srv.port)}/simple/"
        allow_host = f"localhost:{install_srv.port}"

        assert uv_install_version(
            "strict-env",
            index_url,
            allow_host,
            exclude_newer=cutoff,
        ) == older_version

        assert (
            uv_install_version("open-env", index_url, allow_host) == newer_version
        )
