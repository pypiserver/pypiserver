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
    ("pytz-2012b.zip", "pytz", "2012b"),
    ("ABC12-34_V1X-1.2.3.zip", "ABC12-34_V1X", "1.2.3"),
    ("A100-200-XYZ-1.2.3.zip", "A100-200-XYZ", "1.2.3"),
    ("flup-1.0.3.dev-20110405.tar.gz", "flup", "1.0.3.dev-20110405"),
    ("package-1.0.0-alpha.1.zip", "package", "1.0.0-alpha.1"),
    ("package-1.3.7+build.11.e0f985a.zip", "package", "1.3.7+build.11.e0f985a"),
    ("package-v1.8.1.301.ga0df26f.zip", "package", "v1.8.1.301.ga0df26f"),
    ("package-2013.02.17.dev123.zip", "package", "2013.02.17.dev123"),
    ("package-20000101.zip", "package", "20000101"),
    ("flup-123-1.0.3.dev-20110405.tar.gz", "flup-123", "1.0.3.dev-20110405"),
    ("package-123-1.0.0-alpha.1.zip", "package-123", "1.0.0-alpha.1"),
    ("package-123-1.3.7+build.11.e0f985a.zip", "package-123", "1.3.7+build.11.e0f985a"),
    ("package-123-v1.8.1.301.ga0df26f.zip", "package-123", "v1.8.1.301.ga0df26f"),
    ("package-123-2013.02.17.dev123.zip", "package-123", "2013.02.17.dev123"),
    ("package-123-20000101.zip", "package-123", "20000101"),
    ("pyelasticsearch-0.5-brainbot-1-20130712.zip", "pyelasticsearch", "0.5-brainbot-1-20130712"),
    ("pywin32-217-cp27-none-win32.whl", "pywin32", "217"),
    ("pywin32-217-55-cp27-none-win32.whl", "pywin32", "217-55"),
    ("pywin32-217.1-cp27-none-win32.whl", "pywin32", "217.1"),
    ("package.zip", "package", ""),
]


@pytest.mark.parametrize(("filename", "pkgname", "version"), files)
def test_guess_pkgname_and_version(filename, pkgname, version):
    assert core.guess_pkgname_and_version(filename) == (pkgname, version)


def test_listdir_bad_name(tmpdir):
    tmpdir.join("foo.whl").ensure()
    res = list(core.listdir(tmpdir.strpath))
    assert res == []
