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
import itertools
import os
import shutil
import socket
import sys
import time
from collections import namedtuple
from pathlib import Path
from shlex import split
from subprocess import Popen
from urllib.error import URLError
from urllib.request import urlopen

import pytest

# ######################################################################
# Fixtures & Helper Functions
# ######################################################################


CURRENT_PATH = Path(__file__).parent
ports = itertools.count(10000)
Srv = namedtuple("Srv", ("port", "root"))


@contextlib.contextmanager
def run_server(root, authed=False, other_cli=""):
    """Run a server, optionally with partial auth enabled."""
    htpasswd = CURRENT_PATH.joinpath("htpasswd.a.a").expanduser().resolve()
    pswd_opt_choices = {
        True: f"-P {htpasswd} -a update,download",
        False: "-P. -a.",
        "partial": f"-P {htpasswd} -a update",
    }
    pswd_opts = pswd_opt_choices[authed]

    port = next(ports)
    cmd = (
        f"{sys.executable} -m pypiserver.__main__ "
        f"run -vvv --overwrite -i 127.0.0.1 "
        f"-p {port} {pswd_opts} {other_cli} {root}"
    )
    proc = Popen(cmd.split(), bufsize=2 ** 16)
    srv = Srv(port, root)
    try:
        wait_until_ready(srv)
        assert proc.poll() is None
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


def build_url(port, user="", pswd=""):
    auth = f"{user}:{pswd}@" if user or pswd else ""
    return f"http://{auth}localhost:{port}"


def run_setup_py(path: Path, arguments: str):
    return os.system(f"{sys.executable} {path / 'setup.py'} {arguments}")


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
    assert run_setup_py(project, f"bdist_wheel -d {distdir}") == 0
    return list(distdir.glob("centodeps*.whl"))[0]


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


def pip_download(cmd, port, install_dir, user=None, pswd=None):
    url = build_url(port, user, pswd)
    return _run_pip(f"-vv download -d {install_dir} -i {url} {cmd}")


def _run_pip(cmd):
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


def run_twine(command, package, conf):
    proc = Popen(
        split(
            f"twine {command} --repository test --config-file {conf} {package}"
        )
    )
    proc.communicate()
    assert not proc.returncode, f"Twine {command} failed. See stdout/err"


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


@pytest.mark.parametrize("pkg_frmt", ["bdist", "bdist_wheel"])
@pytest.mark.parametrize(["server_fixture", "pypirc_fixture"], all_servers)
def test_setuptools_upload(
    server_fixture, pypirc_fixture, project, pkg_frmt, server_root, request
):
    request.getfixturevalue(server_fixture)
    request.getfixturevalue(pypirc_fixture)

    assert len(list(server_root.iterdir())) == 0

    for i in range(5):
        print(f"++Attempt #{i}")
        assert run_setup_py(project, f"-vvv {pkg_frmt} upload -r test") == 0
    assert len(list(server_root.iterdir())) == 1


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

    assert len(list(server_root.iterdir())) == 1
    assert server_root.joinpath(wheel_file.name).is_file(), (
        wheel_file.name,
        list(server_root.iterdir()),
    )


@pytest.mark.parametrize(["server_fixture", "pypirc_fixture"], all_servers)
def test_twine_register(server_fixture, pypirc_fixture, wheel_file, request):
    """Test unauthenticated twine registration"""
    request.getfixturevalue(server_fixture)
    pypirc = request.getfixturevalue(pypirc_fixture)
    run_twine("register", wheel_file, conf=pypirc)
