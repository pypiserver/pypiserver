#! /usr/bin/env py.test

import pytest
from pypiserver import core


files = [
    ("pytz-2012b.tar.bz2", "pytz", "2012b"),
    ("pytz-2012b.tgz", "pytz", "2012b"),
    ("pytz-2012b.ZIP", "pytz", "2012b"),
    ("gevent-1.0b1.win32-py2.6.exe", "gevent", "1.0b1"),
    ("gevent-1.0b1.win32-py2.7.msi", "gevent", "1.0b1"),
    ("greenlet-0.3.4-py3.1-win-amd64.egg", "greenlet", "0.3.4"),
    ("greenlet-0.3.4.win-amd64-py3.2.exe", "greenlet", "0.3.4"),
    ("greenlet-0.3.4-py3.2-win32.egg", "greenlet", "0.3.4"),
    ("greenlet-0.3.4-py2.7-linux-x86_64.egg", "greenlet", "0.3.4"),
    ("pep8-0.6.0.zip", "pep8", "0.6.0"),
    ("pytz-2012b.zip", "pytz", "2012b")]


@pytest.mark.parametrize(("filename", "pkgname", "version"), files)
def test_guess_pkgname(filename, pkgname, version):
    assert core.guess_pkgname(filename) == pkgname


@pytest.mark.parametrize(("filename", "pkgname", "version"), files)
def test_guess_pkgname_and_version(filename, pkgname, version):
    assert core.guess_pkgname_and_version(filename) == (pkgname, version)
