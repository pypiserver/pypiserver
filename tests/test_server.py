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

from collections import namedtuple
import contextlib
import functools
import os
import subprocess
import sys
import tempfile
import time
from shlex import split
from subprocess import Popen
from textwrap import dedent
try:
    from urllib.request import urlopen
except ImportError:
    from urllib import urlopen

from py import path  # @UnresolvedImport
import pytest


# ######################################################################
# Fixtures & Helper Functions
# ######################################################################


_BUFF_SIZE = 2**16
_port = 8090
SLEEP_AFTER_SRV = 3  # sec


@pytest.fixture
def port():
    global _port
    _port += 1
    return _port


Srv = namedtuple('Srv', ('proc', 'port', 'package'))


def _run_server(packdir, port, authed, other_cli=''):
    """Run a server, optionally with partial auth enabled."""
    pswd_opt_choices = {
        True: "-Ptests/htpasswd.a.a -a update,download",
        False: "-P. -a.",
        'partial': "-Ptests/htpasswd.a.a -a update",
    }
    pswd_opts = pswd_opt_choices[authed]
    cmd = (
        "%s -m pypiserver.__main__ -vvv --overwrite -i 127.0.0.1 "
        "-p %s %s %s %s" % (
            sys.executable,
            port,
            pswd_opts,
            other_cli,
            packdir,
        )
    )
    proc = subprocess.Popen(cmd.split(), bufsize=_BUFF_SIZE)
    time.sleep(SLEEP_AFTER_SRV)
    assert proc.poll() is None

    return Srv(proc, int(port), packdir)


def _kill_server(srv):
    print('Killing %s' % (srv,))
    try:
        srv.proc.terminate()
        time.sleep(1)
    finally:
        srv.proc.kill()


@contextlib.contextmanager
def new_server(packdir, port, authed=False, other_cli=''):
    srv = _run_server(packdir, port,
                      authed=authed, other_cli=other_cli)
    try:
        yield srv
    finally:
        _kill_server(srv)


@contextlib.contextmanager
def chdir(d):
    old_d = os.getcwd()
    try:
        os.chdir(d)
        yield
    finally:
        os.chdir(old_d)


def _run_python(cmd):
    ncmd = '%s %s' % (sys.executable, cmd)
    return os.system(ncmd)


@pytest.fixture(scope='module')
def project(request):
    def fin():
        tmpdir.remove(True)
    tmpdir = path.local(tempfile.mkdtemp())
    request.addfinalizer(fin)
    src_setup_py = path.local().join('tests', 'centodeps-setup.py')
    assert src_setup_py.check()
    projdir = tmpdir.join('centodeps')
    projdir.mkdir()
    dst_setup_py = projdir.join('setup.py')
    src_setup_py.copy(dst_setup_py)
    assert dst_setup_py.check()

    return projdir


@pytest.fixture(scope='module')
def package(project, request):
    with chdir(project.strpath):
        cmd = 'setup.py bdist_wheel'
        assert _run_python(cmd) == 0
        pkgs = list(project.join('dist').visit('centodeps*.whl'))
        assert len(pkgs) == 1
        pkg = path.local(pkgs[0])
        assert pkg.check()

        return pkg


@pytest.fixture(scope='module')
def packdir(package):
    return package.dirpath()


open_port = 8081


@pytest.fixture(scope='module')
def open_server(packdir, request):
    srv = _run_server(packdir, open_port, authed=False)
    fin = functools.partial(_kill_server, srv)
    request.addfinalizer(fin)

    return srv


protected_port = 8082


@pytest.fixture(scope='module')
def protected_server(packdir, request):
    srv = _run_server(packdir, protected_port, authed=True)
    fin = functools.partial(_kill_server, srv)
    request.addfinalizer(fin)

    return srv


@pytest.fixture
def empty_packdir(tmpdir):
    return tmpdir.mkdir("dists")


def _build_url(port, user='', pswd=''):
    auth = '%s:%s@' % (user, pswd) if user or pswd else ''
    return 'http://%slocalhost:%s' % (auth, port)


def _run_pip(cmd):
    ncmd = (
        "pip --no-cache-dir --disable-pip-version-check "
        "--retries 0 --timeout 5 --no-input %s"
    ) % cmd
    print('PIP: %s' % ncmd)
    proc = Popen(split(ncmd))
    proc.communicate()
    return proc.returncode


def _run_pip_install(cmd, port, install_dir, user=None, pswd=None):
    url = _build_url(port, user, pswd)
    # ncmd = '-vv install --download %s -i %s %s' % (install_dir, url, cmd)
    ncmd = '-vv download -d %s -i %s %s' % (install_dir, url, cmd)
    return _run_pip(ncmd)


@pytest.fixture
def pipdir(tmpdir):
    return tmpdir.mkdir("pip")


@contextlib.contextmanager
def pypirc_tmpfile(port, user, password):
    """Create a temporary pypirc file."""
    fd, filepath = tempfile.mkstemp()
    os.close(fd)
    with open(filepath, 'w') as rcfile:
        rcfile.writelines(
            '\n'.join((
                '[distutils]',
                'index-servers: test',
                ''
                '[test]',
                'repository: {}'.format(_build_url(port)),
                'username: {}'.format(user),
                'password: {}'.format(password),
            ))
        )
    with open(filepath) as rcfile:
        print(rcfile.read())
    yield filepath
    os.remove(filepath)


@contextlib.contextmanager
def pypirc_file(txt):
    pypirc_path = path.local('~/.pypirc', expanduser=1)
    old_pypirc = pypirc_path.read() if pypirc_path.check() else None
    pypirc_path.write(txt)
    try:
        yield
    finally:
        if old_pypirc:
            pypirc_path.write(old_pypirc)
        else:
            pypirc_path.remove()


def twine_upload(packages, repository='test', conf='pypirc',
                 expect_failure=False):
    """Call 'twine upload' with appropriate arguments"""
    proc = Popen((
        'twine',
        'upload',
        '--repository', repository,
        '--config-file', conf,
        ' '.join(packages),
    ))
    proc.communicate()
    if not expect_failure and proc.returncode:
        assert False, 'Twine upload failed. See stdout/err'


def twine_register(packages, repository='test', conf='pypirc',
                   expect_failure=False):
    """Call 'twine register' with appropriate args"""
    proc = Popen((
        'twine',
        'register',
        '--repository', repository,
        '--config-file', conf,
        ' '.join(packages)
    ))
    proc.communicate()
    if not expect_failure and proc.returncode:
        assert False, 'Twine register failed. See stdout/err'


# ######################################################################
# Tests
# ######################################################################


def test_pipInstall_packageNotFound(empty_packdir, port, pipdir, package):
    with new_server(empty_packdir, port):
        cmd = "centodeps"
        assert _run_pip_install(cmd, port, pipdir) != 0
        assert not pipdir.listdir()


def test_pipInstall_openOk(open_server, package, pipdir):
    cmd = "centodeps"
    assert _run_pip_install(cmd, open_server.port, pipdir) == 0
    assert pipdir.join(package.basename).check()


def test_pipInstall_authedFails(protected_server, pipdir):
    cmd = "centodeps"
    assert _run_pip_install(cmd, protected_server.port, pipdir) != 0
    assert not pipdir.listdir()


def test_pipInstall_authedOk(protected_server, package, pipdir):
    cmd = "centodeps"
    assert _run_pip_install(cmd, protected_server.port, pipdir,
                            user='a', pswd='a') == 0
    assert pipdir.join(package.basename).check()


@pytest.mark.parametrize("pkg_frmt", ['bdist', 'bdist_wheel'])
def test_setuptoolsUpload_open(empty_packdir, port, project, package,
                               pkg_frmt):
    url = _build_url(port, None, None)
    with pypirc_file(dedent("""\
                [distutils]
                index-servers: test

                [test]
                repository: %s
                username: ''
                password: ''
            """ % url)):
        with new_server(empty_packdir, port):
            with chdir(project.strpath):
                cmd = "setup.py -vvv %s upload -r %s" % (pkg_frmt, url)
                for i in range(5):
                    print('++Attempt #%s' % i)
                    assert _run_python(cmd) == 0
                time.sleep(SLEEP_AFTER_SRV)
    assert len(empty_packdir.listdir()) == 1


@pytest.mark.parametrize("pkg_frmt", ['bdist', 'bdist_wheel'])
def test_setuptoolsUpload_authed(empty_packdir, port, project, package,
                                 pkg_frmt, monkeypatch):
    url = _build_url(port)
    with pypirc_file(dedent("""\
                [distutils]
                index-servers: test

                [test]
                repository: %s
                username: a
                password: a
            """ % url)):
        with new_server(empty_packdir, port, authed=True):
            with chdir(project.strpath):
                cmd = (
                    "setup.py -vvv %s register -r "
                    "test upload -r test" % pkg_frmt
                )
                for i in range(5):
                    print('++Attempt #%s' % i)
                    assert _run_python(cmd) == 0
            time.sleep(SLEEP_AFTER_SRV)
    assert len(empty_packdir.listdir()) == 1


@pytest.mark.parametrize("pkg_frmt", ['bdist', 'bdist_wheel'])
def test_setuptools_upload_partial_authed(empty_packdir, port, project,
                                          pkg_frmt):
    """Test uploading a package with setuptools with partial auth."""
    url = _build_url(port)
    with pypirc_file(dedent("""\
                [distutils]
                index-servers: test

                [test]
                repository: %s
                username: a
                password: a
            """ % url)):
        with new_server(empty_packdir, port, authed='partial'):
            with chdir(project.strpath):
                cmd = ("setup.py -vvv %s register -r test upload -r test" %
                       pkg_frmt)
                for i in range(5):
                    print('++Attempt #%s' % i)
                    assert _run_python(cmd) == 0
            time.sleep(SLEEP_AFTER_SRV)
    assert len(empty_packdir.listdir()) == 1


def test_partial_authed_open_download(empty_packdir, port):
    """Validate that partial auth still allows downloads."""
    url = _build_url(port) + '/simple'
    with new_server(empty_packdir, port, authed='partial'):
        resp = urlopen(url)
        assert resp.getcode() == 200


def test_twine_upload_open(empty_packdir, port, package):
    """Test twine upload with no authentication"""
    user, pswd = 'foo', 'bar'
    with new_server(empty_packdir, port):
        with pypirc_tmpfile(port, user, pswd) as rcfile:
            twine_upload([package.strpath], repository='test', conf=rcfile)
        time.sleep(SLEEP_AFTER_SRV)

    assert len(empty_packdir.listdir()) == 1


@pytest.mark.parametrize("hash_algo", ("md5", "sha256", "sha512"))
def test_hash_algos(empty_packdir, port, package, pipdir, hash_algo):
    """Test twine upload with no authentication"""
    user, pswd = 'foo', 'bar'
    with new_server(
        empty_packdir, port, other_cli="--hash-algo {}".format(hash_algo)
    ):
        with pypirc_tmpfile(port, user, pswd) as rcfile:
            twine_upload([package.strpath], repository='test', conf=rcfile)
        time.sleep(SLEEP_AFTER_SRV)

        assert _run_pip_install("centodeps", port, pipdir) == 0


def test_twine_upload_authed(empty_packdir, port, package):
    """Test authenticated twine upload"""
    user, pswd = 'a', 'a'
    with new_server(empty_packdir, port, authed=False):
        with pypirc_tmpfile(port, user, pswd) as rcfile:
            twine_upload([package.strpath], repository='test', conf=rcfile)
        time.sleep(SLEEP_AFTER_SRV)
    assert len(empty_packdir.listdir()) == 1

    assert empty_packdir.join(
        package.basename).check(), (package.basename, empty_packdir.listdir())


def test_twine_upload_partial_authed(empty_packdir, port, package):
    """Test partially authenticated twine upload"""
    user, pswd = 'a', 'a'
    with new_server(empty_packdir, port, authed='partial'):
        with pypirc_tmpfile(port, user, pswd) as rcfile:
            twine_upload([package.strpath], repository='test', conf=rcfile)
        time.sleep(SLEEP_AFTER_SRV)
    assert len(empty_packdir.listdir()) == 1


def test_twine_register_open(open_server, package):
    """Test unauthenticated twine registration"""
    srv = open_server
    with pypirc_tmpfile(srv.port, 'foo', 'bar') as rcfile:
        twine_register([package.strpath], repository='test', conf=rcfile)


def test_twine_register_authed_ok(protected_server, package):
    """Test authenticated twine registration"""
    srv = protected_server
    user, pswd = 'a', 'a'
    with pypirc_tmpfile(srv.port, user, pswd) as rcfile:
        twine_register([package.strpath], repository='test', conf=rcfile)
