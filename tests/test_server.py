#! /usr/bin/env py.test

import contextlib
import subprocess
import sys
import time

import pip
from py import path  # @UnresolvedImport
import pytest

localhost = "http://localhost:8080"

pypirc = {
    "repository": localhost,
    "username": 'a',
    "password": 'a'
}


@contextlib.contextmanager
def server(packdir, with_password=False):
    pswd_opt_choices = {True: "-Phtpaswd.a.a", False: "-P. -a."}
    pswd_opts = pswd_opt_choices[with_password]
    cmd = "python -m pypiserver.__main__ -v %s %s" % (pswd_opts, packdir)
    proc = subprocess.Popen(cmd.split())
    try:
        yield proc
    finally:
        try:
            proc.terminate()
            time.sleep(1)
        finally:
            proc.kill()


@pytest.fixture
def srv_packdir(tmpdir):
    return tmpdir.mkdir("dists")


@pytest.fixture
def uploader(monkeypatch):
    from twine.commands import upload
    monkeypatch.setattr(upload.utils, 'get_repository_from_config',
                        lambda *x: pypirc)

    return upload


@pytest.fixture
def package():
    dist_path = path.local('tests/centodeps/wheelhouse')
    pkgs = list(dist_path.visit('centodeps*.whl'))
    assert len(pkgs) == 1
    return pkgs[0]


def run_pip(cmd):
    ncmd = "--disable-pip-version-check %s" % cmd
    return pip.main(ncmd.split())


def test_pip(srv_packdir, package):
    with server(package.dirname):
        time.sleep(1)
        cmd = "install -i %s centodeps" % localhost
        assert pip.main(cmd.split()) == 0

    cmd = "uninstall centodeps --yes"
    assert pip.main(cmd.split()) == 0


@pytest.mark.skipif(sys.version_info[:2] == (3, 2),
                    reason="urllib3 fails on twine (see https://travis-ci.org/ankostis/pypiserver/builds/81044993)")
def test_upload(srv_packdir, package, uploader):
    with server(srv_packdir):
        time.sleep(1)
        uploader.upload([str(package)], repository='test',
                        sign=None, identity=None,
                        username='a', password='a',
                        comment=None, sign_with=None,
                        config_file=None, skip_existing=None)
        time.sleep(1)

    assert srv_packdir.join(package.basename).check(), srv_packdir.listdir()

# 
# def test_register_upload(srv_packdir, package):
#     with server(package.dirname) as srv:
#         time.sleep(1)
#         cmd = "pip register -i %s upload centodeps" % localhost
#         assert pip.main(cmd.split()) == 0
# 
#     cmd = "uninstall centodeps --yes"
#     assert pip.main(cmd.split()) == 0
