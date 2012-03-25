#! /usr/bin/env py.test

import pytest
from pypiserver import core


files = [
    ("pytz-2012b.tar.bz2", "pytz", "2012b"),
    ("pytz-2012b.tgz", "pytz", "2012b"),
    ("pytz-2012b.zip", "pytz", "2012b")]


@pytest.mark.parametrize(("filename", "pkgname", "version"), files)
def test_guess_pkgname(filename, pkgname, version):
    assert core.guess_pkgname(filename) == pkgname


@pytest.mark.parametrize(("filename", "pkgname", "version"), files)
def test_guess_pkgname_and_version(filename, pkgname, version):
    assert core.guess_pkgname_and_version(filename) == (pkgname, version)
