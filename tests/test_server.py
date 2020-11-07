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
from __future__ import print_function

import pathlib
import shutil
import socket
from collections import namedtuple
import contextlib
import functools
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from shlex import split
from subprocess import Popen
from textwrap import dedent
from urllib.error import URLError

try:
    from urllib.request import urlopen
except ImportError:
    from urllib import urlopen

import pytest


# ######################################################################
# Fixtures & Helper Functions
# ######################################################################


_BUFF_SIZE = 2 ** 16
_port = 8090
CURRENT_PATH = pathlib.Path(__file__).parent


@pytest.fixture
def port():
    global _port
    _port += 1
    return _port


Srv = namedtuple("Srv", ("proc", "port", "package"))


@contextlib.contextmanager
def _run_server(packdir, port, authed, other_cli=""):
    """Run a server, optionally with partial auth enabled."""
    htpasswd = CURRENT_PATH.joinpath('htpasswd.a.a').expanduser().resolve()
    pswd_opt_choices = {
        True: f"-P {htpasswd} -a update,download",
        False: "-P. -a.",
        "partial": f"-P {htpasswd} -a update",
    }
    pswd_opts = pswd_opt_choices[authed]
    cmd = (
        f"{sys.executable} -m pypiserver.__main__ run -vvv --overwrite -i 127.0.0.1 "
        f"-p {port} {pswd_opts} {other_cli} {packdir}"
    )
    proc = subprocess.Popen(cmd.split(), bufsize=_BUFF_SIZE)
    srv = Srv(proc, int(port), packdir)
    try:
        wait_until_ready(srv)
        assert proc.poll() is None
        yield srv
    finally:
        _kill_server(srv)


def wait_until_ready(srv: Srv, n_tries=10):
    for _ in range(n_tries):
        if is_ready(srv):
            return True
        time.sleep(0.5)
    raise TimeoutError


def is_ready(srv: Srv):
    try:
        return urlopen(_build_url(srv.port), timeout=0.5).getcode() in (
            200,
            403,
        )
    except (URLError, socket.timeout):
        return False


def _kill_server(srv):
    print(f"Killing {srv}")
    srv.proc.terminate()
    try:
        srv.proc.wait(timeout=1)
    finally:
        srv.proc.kill()


@contextlib.contextmanager
def new_server(packdir, port, authed=False, other_cli=""):
    with _run_server(packdir, port, authed=authed, other_cli=other_cli) as srv:
        yield srv


@contextlib.contextmanager
def chdir(d):
    old_d = os.getcwd()
    try:
        os.chdir(d)
        yield
    finally:
        os.chdir(old_d)


def _run_python(cmd):
    return os.system(f"{sys.executable} {cmd}")


@pytest.fixture(scope="module")
def project(tmp_path_factory):
    src_setup_py = CURRENT_PATH / "centodeps-setup.py"
    assert src_setup_py.is_file()

    projdir = tmp_path_factory.mktemp("project") / "centodeps"
    projdir.mkdir(parents=True, exist_ok=True)

    dst_setup_py = projdir / "setup.py"
    shutil.copy(src_setup_py, dst_setup_py)
    assert dst_setup_py.is_file()

    return projdir


@pytest.fixture(scope="module")
def package(project):
    with chdir(str(project)):
        cmd = "setup.py bdist_wheel"
        assert _run_python(cmd) == 0
        pkgs = list(project.joinpath("dist").glob("centodeps*.whl"))
        assert len(pkgs) == 1 and pkgs[0].is_file()
        return pkgs[0]


@pytest.fixture(scope="module")
def packdir(package):
    return package.parent


open_port = 8081


@pytest.fixture(scope="module")
def open_server(packdir):
    with _run_server(packdir, open_port, authed=False) as srv:
        yield srv


protected_port = 8082


@pytest.fixture(scope="module")
def protected_server(packdir):
    with _run_server(packdir, protected_port, authed=True) as srv:
        yield srv


@pytest.fixture
def empty_packdir(tmp_path_factory):
    return tmp_path_factory.mktemp("dists")


def _build_url(port, user="", pswd=""):
    auth = f"{user}:{pswd}@" if user or pswd else ""
    return f"http://{auth}localhost:{port}"


def _run_pip(cmd):
    ncmd = (
        "pip --no-cache-dir --disable-pip-version-check "
        f"--retries 0 --timeout 5 --no-input {cmd}"
    )
    print(f"PIP: {ncmd}")
    proc = Popen(split(ncmd))
    proc.communicate()
    return proc.returncode


def _run_pip_install(cmd, port, install_dir, user=None, pswd=None):
    url = _build_url(port, user, pswd)
    return _run_pip(f"-vv download -d {install_dir} -i {url} {cmd}")


@pytest.fixture
def pipdir(tmp_path_factory):
    return tmp_path_factory.mktemp("pip")


@contextlib.contextmanager
def pypirc_tmpfile(port, user, password):
    """Create a temporary pypirc file."""
    fd, filepath = tempfile.mkstemp()
    os.close(fd)
    Path(filepath).write_text(
        "\n".join(
            (
                "[distutils]",
                "index-servers: test",
                "" "[test]",
                f"repository: {_build_url(port)}",
                f"username: {user}",
                f"password: {password}",
            )
        )
    )

    print(Path(filepath).read_text())
    yield filepath
    os.remove(filepath)


@contextlib.contextmanager
def pypirc_file(txt):
    pypirc_path = Path.home() / ".pypirc"
    old_pypirc = pypirc_path.read_text() if pypirc_path.is_file() else None
    pypirc_path.write_text(txt)
    try:
        yield
    finally:
        if old_pypirc:
            pypirc_path.write_text(old_pypirc)
        else:
            pypirc_path.unlink()


def twine_upload(
    packages, repository="test", conf="pypirc", expect_failure=False
):
    """Call 'twine upload' with appropriate arguments"""
    proc = Popen(
        (
            "twine",
            "upload",
            "--repository",
            repository,
            "--config-file",
            conf,
            " ".join(str(p) for p in packages),
        )
    )
    proc.communicate()
    if not expect_failure and proc.returncode:
        assert False, "Twine upload failed. See stdout/err"


def twine_register(
    packages, repository="test", conf="pypirc", expect_failure=False
):
    """Call 'twine register' with appropriate args"""
    proc = Popen(
        (
            "twine",
            "register",
            "--repository",
            repository,
            "--config-file",
            conf,
            " ".join(str(p) for p in packages),
        )
    )
    proc.communicate()
    if not expect_failure and proc.returncode:
        assert False, "Twine register failed. See stdout/err"


# ######################################################################
# Tests
# ######################################################################


def test_pipInstall_packageNotFound(empty_packdir, port, pipdir, package):
    with new_server(empty_packdir, port):
        cmd = "centodeps"
        assert _run_pip_install(cmd, port, pipdir) != 0
        assert not list(pipdir.iterdir())


def test_pipInstall_openOk(open_server, package, pipdir):
    cmd = "centodeps"
    assert _run_pip_install(cmd, open_server.port, pipdir) == 0
    assert pipdir.joinpath(package.name).is_file()


def test_pipInstall_authedFails(protected_server, pipdir):
    cmd = "centodeps"
    assert _run_pip_install(cmd, protected_server.port, pipdir) != 0
    assert not list(pipdir.iterdir())


def test_pipInstall_authedOk(protected_server, package, pipdir):
    cmd = "centodeps"
    assert (
        _run_pip_install(cmd, protected_server.port, pipdir, user="a", pswd="a")
        == 0
    )
    assert pipdir.joinpath(package.name).is_file()


@pytest.mark.parametrize("pkg_frmt", ["bdist", "bdist_wheel"])
def test_setuptoolsUpload_open(empty_packdir, port, project, package, pkg_frmt):
    url = _build_url(port, None, None)
    with pypirc_file(
        dedent(
            f"""\
                [distutils]
                index-servers: test

                [test]
                repository: {url}
                username: ''
                password: ''
            """
        )
    ):
        with new_server(empty_packdir, port):
            with chdir(project):
                cmd = f"setup.py -vvv {pkg_frmt} upload -r {url}"
                for i in range(5):
                    print(f"++Attempt #{i}")
                    assert _run_python(cmd) == 0
    assert len(list(empty_packdir.iterdir())) == 1


@pytest.mark.parametrize("pkg_frmt", ["bdist", "bdist_wheel"])
def test_setuptoolsUpload_authed(
    empty_packdir, port, project, package, pkg_frmt, monkeypatch
):
    url = _build_url(port)
    with pypirc_file(
        dedent(
            f"""\
                [distutils]
                index-servers: test

                [test]
                repository: {url}
                username: a
                password: a
            """
        )
    ):
        with new_server(empty_packdir, port, authed=True):
            with chdir(project):
                cmd = (
                    f"setup.py -vvv {pkg_frmt} register -r test upload -r test"
                )
                for i in range(5):
                    print(f"++Attempt #{i}")
                    assert _run_python(cmd) == 0
    assert len(list(empty_packdir.iterdir())) == 1


@pytest.mark.parametrize("pkg_frmt", ["bdist", "bdist_wheel"])
def test_setuptools_upload_partial_authed(
    empty_packdir, port, project, pkg_frmt
):
    """Test uploading a package with setuptools with partial auth."""
    url = _build_url(port)
    with pypirc_file(
        dedent(
            f"""\
                [distutils]
                index-servers: test

                [test]
                repository: {url}
                username: a
                password: a
            """
        )
    ):
        with new_server(empty_packdir, port, authed="partial"):
            with chdir(project):
                cmd = (
                    f"setup.py -vvv {pkg_frmt} register -r test upload -r test"
                )
                for i in range(5):
                    print(f"++Attempt #{i}")
                    assert _run_python(cmd) == 0
    assert len(list(empty_packdir.iterdir())) == 1


def test_partial_authed_open_download(empty_packdir, port):
    """Validate that partial auth still allows downloads."""
    url = _build_url(port) + "/simple"
    with new_server(empty_packdir, port, authed="partial"):
        resp = urlopen(url)
        assert resp.getcode() == 200


def test_twine_upload_open(empty_packdir, port, package):
    """Test twine upload with no authentication"""
    user, pswd = "foo", "bar"
    with new_server(empty_packdir, port):
        with pypirc_tmpfile(port, user, pswd) as rcfile:
            twine_upload([package], repository="test", conf=rcfile)

    assert len(list(empty_packdir.iterdir())) == 1


@pytest.mark.parametrize("hash_algo", ("md5", "sha256", "sha512"))
def test_hash_algos(empty_packdir, port, package, pipdir, hash_algo):
    """Test twine upload with no authentication"""
    user, pswd = "foo", "bar"
    with new_server(
        empty_packdir, port, other_cli="--hash-algo {}".format(hash_algo)
    ):
        with pypirc_tmpfile(port, user, pswd) as rcfile:
            twine_upload([package], repository="test", conf=rcfile)

        assert _run_pip_install("centodeps", port, pipdir) == 0


def test_twine_upload_authed(empty_packdir, port, package):
    """Test authenticated twine upload"""
    user, pswd = "a", "a"
    with new_server(empty_packdir, port, authed=False):
        with pypirc_tmpfile(port, user, pswd) as rcfile:
            twine_upload([package], repository="test", conf=rcfile)
    assert len(list(empty_packdir.iterdir())) == 1

    assert empty_packdir.joinpath(package.name).is_file(), (
        package.name,
        list(empty_packdir.iterdir()),
    )


def test_twine_upload_partial_authed(empty_packdir, port, package):
    """Test partially authenticated twine upload"""
    user, pswd = "a", "a"
    with new_server(empty_packdir, port, authed="partial"):
        with pypirc_tmpfile(port, user, pswd) as rcfile:
            twine_upload([package], repository="test", conf=rcfile)
    assert len(list(empty_packdir.iterdir())) == 1


def test_twine_register_open(open_server, package):
    """Test unauthenticated twine registration"""
    srv = open_server
    with pypirc_tmpfile(srv.port, "foo", "bar") as rcfile:
        twine_register([package], repository="test", conf=rcfile)


def test_twine_register_authed_ok(protected_server, package):
    """Test authenticated twine registration"""
    srv = protected_server
    user, pswd = "a", "a"
    with pypirc_tmpfile(srv.port, user, pswd) as rcfile:
        twine_register([package], repository="test", conf=rcfile)
