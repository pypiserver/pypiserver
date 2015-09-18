#! /usr/bin/env py.test

import contextlib
import io
import subprocess
import sys
import time

from py import path  # @UnresolvedImport
import pytest


@contextlib.contextmanager
def server(packdir):
    cmd = "python -m pypiserver.__main__ -v -P. -a. %s" % packdir
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
def packdir(tmpdir):
    return tmpdir.mkdir("dists")


@pytest.fixture
def pypirc():
    return {
        "repository": "http://localhost:8080",
        "username": 'a',
        "password": 'a'
    }


@pytest.fixture
def uploader(pypirc, monkeypatch):
    from twine.commands import upload
    monkeypatch.setattr(upload.utils, 'get_repository_from_config',
                        lambda *x: pypirc)

    return upload


@pytest.mark.skipif(sys.version_info[:2] == (3, 2),
                    reason="urllib3 fails on twine (see https://travis-ci.org/ankostis/pypiserver/builds/81044993)")
def test_centodeps(packdir, uploader):

    dist_path = path.local('tests/centodeps/wheelhouse/centodeps*.whl')

    with server(packdir) as srv:
        time.sleep(1)
        uploader.upload([str(dist_path)], repository='test',
                        sign=None, identity=None,
                        username='a', password='a',
                        comment=None, sign_with=None,
                        config_file=None, skip_existing=None)
        time.sleep(1)

    assert list(packdir.visit('centodeps*.whl')), list(packdir.visit(
                                                       'centodeps*.whl'))
