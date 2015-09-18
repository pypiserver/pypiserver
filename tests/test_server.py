#! /usr/bin/env py.test
from __future__ import print_function

from collections import namedtuple
import contextlib
import functools
import os
import subprocess
import sys
import time

import pip
from py import path  # @UnresolvedImport
import pytest

_BUFF_SIZE = 4096
_port = 8090


@pytest.fixture
def port():
    global _port
    _port += 1
    return _port

Srv = namedtuple('Srv', ('proc', 'port', 'pdir'))


def _run_server(packdir, port, with_password, other_cli=''):
    pswd_opt_choices = {
        True: "-Ptests/htpasswd.a.a -a update,download",
        False: "-P. -a."
    }
    pswd_opts = pswd_opt_choices[with_password]
    cmd = "python -m pypiserver.__main__ -v --overwrite -p %s %s %s %s" % (
        port, pswd_opts, other_cli, packdir)
    proc = subprocess.Popen(cmd.split(), bufsize=_BUFF_SIZE)
    time.sleep(1)

    return Srv(proc, int(port), packdir)


def _kill_server(srv):
    print('Killing %s' % (srv,))
    try:
        srv.proc.terminate()
        time.sleep(1)
    finally:
        srv.proc.kill()


@contextlib.contextmanager
def new_server(packdir, port, with_password=False, other_cli=''):
    srv = _run_server(packdir, port,
                      with_password=with_password, other_cli=other_cli)
    try:
        yield srv
    finally:
        _kill_server(srv)


@pytest.fixture(scope='module')
def package():
    dist_path = path.local('tests/centodeps/wheelhouse')
    pkgs = list(dist_path.visit('centodeps*.whl'))
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
    srv = _run_server(packdir, open_port, with_password=False)
    fin = functools.partial(_kill_server, srv)
    request.addfinalizer(fin)

    return srv


protected_port = 8082


@pytest.fixture(scope='module')
def protected_server(packdir, request):
    srv = _run_server(packdir, protected_port, with_password=True)
    fin = functools.partial(_kill_server, srv)
    request.addfinalizer(fin)

    return srv


@pytest.fixture
def pypirc(port):
    return {
        "repository": "http://localhost:%s" % port,
        "username": 'a',
        "password": 'a'
    }


@pytest.fixture
def uploader(pypirc, monkeypatch):
    from twine.commands import upload
    monkeypatch.setattr(upload.utils, 'get_repository_from_config',
                        lambda *x: pypirc)
    return upload


@pytest.fixture
def empty_packdir(tmpdir):
    return tmpdir.mkdir("dists")


def _build_url(port, user='', pswd=''):
    auth = '%s:%s@' % (user, pswd) if user or pswd else ''
    return 'http://%slocalhost:%s' % (auth, port)


def _run_pip(cmd):
    ncmd = ("--disable-pip-version-check --retries 0 --timeout 5"
            " --no-input %s"
            ) % cmd
    print('PIP: %s' % ncmd)
    return pip.main(ncmd.split())


def _run_pip_install(cmd, port, install_dir, user=None, pswd=None):
    url = _build_url(port, user, pswd)
    ncmd = 'install --download %s -i %s %s' % (install_dir, url, cmd)
    return _run_pip(ncmd)


@pytest.fixture
def pipdir(tmpdir):
    return tmpdir.mkdir("pip")


def test_pipInstall_packageNotFound(empty_packdir, port, pipdir, package):
    with new_server(empty_packdir, port) as srv:
        cmd = "centodeps"
        assert _run_pip_install(cmd, port, pipdir) != 0
        assert not pipdir.listdir()


def test_pipInstall_openOk(open_server, package, pipdir):
    cmd = "centodeps"
    assert _run_pip_install(cmd, open_server.port, pipdir) == 0
    assert pipdir.join(package.basename).check()


def test_pipInstall_protectedFails(protected_server, pipdir):
    cmd = "centodeps"
    assert _run_pip_install(cmd, protected_server.port, pipdir) != 0
    assert not pipdir.listdir()


def test_pipInstall_protectedOk(protected_server, package, pipdir):
    cmd = "centodeps"
    assert _run_pip_install(cmd, protected_server.port, pipdir,
                            user='a', pswd='a') == 0
    assert pipdir.join(package.basename).check()


@pytest.mark.skipif(sys.version_info[:2] == (3, 2),
                    reason="urllib3 fails on twine (see https://travis-ci.org/ankostis/pypiserver/builds/81044993)")
def test_upload(empty_packdir, port, package, uploader):
    with new_server(empty_packdir, port) as srv:
        uploader.upload([str(package)], repository='test',
                        sign=None, identity=None,
                        username='a', password='a',
                        comment=None, sign_with=None,
                        config_file=None, skip_existing=None)
        time.sleep(1)

    assert empty_packdir.join(
        package.basename).check(), (package.basename, empty_packdir.listdir())

#


# @contextlib.contextmanager
# def chdir(d):
#     old_d = os.getcwd()
#     try:
#         os.chdir('tests/centodeps')
#         yield
#     finally:
#         os.chdir(old_d)


# def test_register_upload(open_server, pypirc, package, pipdir):
#     with chdir('tests/centodeps'):
#         url = _build_url(open_server.port, user='a', pswd='a')
#         cmd = "python setup.py register  sdist upload -r %s" % url
#         assert subprocess.Popen(cmd.split(), bufsize=_BUFF_SIZE) == 0
