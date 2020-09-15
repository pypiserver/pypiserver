#! /usr/bin/env py.test
# -*- coding: utf-8 -*-

import logging
import os

import pytest

from pypiserver import __main__, core
from tests.doubles import Namespace


## Enable logging to detect any problems with it
##
__main__.init_logging()


files = [
    ("pytz-2012b.tar.bz2", "pytz", "2012b"),
    ("pytz-2012b.tgz", "pytz", "2012b"),
    ("pytz-2012b.ZIP", "pytz", "2012b"),
    ("pytz-2012a.zip", "pytz", "2012a"),
    ("gevent-1.0b1.win32-py2.6.exe", "gevent", "1.0b1"),
    ("gevent-1.0b1.win32-py2.7.msi", "gevent", "1.0b1"),
    ("greenlet-0.3.4-py3.1-win-amd64.egg", "greenlet", "0.3.4"),
    ("greenlet-0.3.4.win-amd64-py3.2.exe", "greenlet", "0.3.4"),
    ("greenlet-0.3.4-py3.2-win32.egg", "greenlet", "0.3.4"),
    ("greenlet-0.3.4-py2.7-linux-x86_64.egg", "greenlet", "0.3.4"),
    ("pep8-0.6.0.zip", "pep8", "0.6.0"),
    ("ABC12-34_V1X-1.2.3.zip", "ABC12", "34_V1X-1.2.3"),
    ("A100-200-XYZ-1.2.3.zip", "A100-200-XYZ", "1.2.3"),
    ("flup-1.0.3.dev-20110405.tar.gz", "flup", "1.0.3.dev-20110405"),
    ("package-1.0.0-alpha.1.zip", "package", "1.0.0-alpha.1"),
    ("package-1.3.7+build.11.e0f985a.zip", "package", "1.3.7+build.11.e0f985a"),
    ("package-v1-8.1.301.ga0df26f.zip", "package-v1", "8.1.301.ga0df26f"),
    ("package-v1.1-8.1.301.ga0df26f.zip", "package-v1.1", "8.1.301.ga0df26f"),
    ("package-2013.02.17.dev123.zip", "package", "2013.02.17.dev123"),
    ("package-20000101.zip", "package", "20000101"),
    ("flup-123-1.0.3.dev-20110405.tar.gz", "flup-123", "1.0.3.dev-20110405"),
    ("package-123-1.0.0-alpha.1.zip", "package-123", "1.0.0-alpha.1"),
    ("package-123-1.3.7+build.11.e0f985a.zip", "package-123", "1.3.7+build.11.e0f985a"),
    ("package-123-v1.1_3-8.1.zip", "package-123-v1.1_3", "8.1"),
    ("package-123-2013.02.17.dev123.zip", "package-123", "2013.02.17.dev123"),
    ("package-123-20000101.zip", "package-123", "20000101"),
    ("pyelasticsearch-0.5-brainbot-1-20130712.zip", "pyelasticsearch", "0.5-brainbot-1-20130712"),
    ("pywin32-217-cp27-none-win32.whl", "pywin32", "217"),
    ("pywin32-217-55-cp27-none-win32.whl", "pywin32", "217-55"),
    ("pywin32-217.1-cp27-none-win32.whl", "pywin32", "217.1"),
    ("package.zip", "package", ""),
    ("package-name-0.0.1.dev0.linux-x86_64.tar.gz", "package-name", "0.0.1.dev0"),
    ("package-name-0.0.1.dev0.macosx-10.10-intel.tar.gz", "package-name", "0.0.1.dev0"),
    ("package-name-0.0.1.alpha.1.win-amd64-py3.2.exe", "package-name", "0.0.1.alpha.1"),
    ("pkg-3!1.0-0.1.tgz", 'pkg', '3!1.0-0.1'), # TO BE FIXED
    ("pkg-3!1+.0-0.1.tgz", 'pkg', '3!1+.0-0.1'), # TO BE FIXED
    ("pkg.zip", 'pkg', ''),
    ("foo/pkg.zip", 'pkg', ''),
    ("foo/pkg-1b.zip", 'pkg', '1b'),
    ("package-name-0.0.1.alpha.1.win-amd64-py3.2.exe", "package-name", "0.0.1.alpha.1"),
]

def _capitalize_ext(fpath):
    f, e = os.path.splitext(fpath)
    if e != '.whl':
        e = e.upper()
    return f + e

@pytest.mark.parametrize(("filename", "pkgname", "version"), files)
def test_guess_pkgname_and_version(filename, pkgname, version):
    exp = (pkgname, version)
    assert core.guess_pkgname_and_version(filename) == exp
    assert core.guess_pkgname_and_version(_capitalize_ext(filename)) == exp

@pytest.mark.parametrize(("filename", "pkgname", "version"), files)
def test_guess_pkgname_and_version_asc(filename, pkgname, version):
    exp = (pkgname, version)
    filename = '%s.asc' % filename
    assert core.guess_pkgname_and_version(filename) == exp


def test_listdir_bad_name(tmpdir):
    tmpdir.join("foo.whl").ensure()
    res = list(core.listdir(tmpdir.strpath))
    assert res == []


def test_read_lines(tmpdir):
    filename = 'pkg_blacklist'
    file_contents = (
        '# Names of private packages that we don\'t want to upgrade\n'
        '\n'
        'my_private_pkg \n'
        ' \t# This is a comment with starting space and tab\n'
        ' my_other_private_pkg'
    )

    f = tmpdir.join(filename).ensure()
    f.write(file_contents)

    assert core.read_lines(f.strpath) == ['my_private_pkg', 'my_other_private_pkg']


hashes = (
    # empty-sha256
    ('sha256', 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'),
    # empty-md5
    ('md5', 'd41d8cd98f00b204e9800998ecf8427e'),
)
@pytest.mark.parametrize(("algo", "digest"), hashes)
def test_hashfile(tmpdir, algo, digest):
    f = tmpdir.join("empty")
    f.ensure()
    assert core.digest_file(f.strpath, algo) == digest


@pytest.mark.parametrize("hash_algo", ("md5", "sha256", "sha512"))
def test_fname_and_hash(tmpdir, hash_algo):
    """Ensure we are returning the expected hashes for files."""
    f = tmpdir.join("tmpfile")
    f.ensure()
    pkgfile = core.PkgFile(
        "tmp", "1.0.0", f.strpath, f.dirname, f.basename
    )
    assert pkgfile.fname_and_hash(hash_algo) == "{}#{}={}".format(
        f.basename, hash_algo, str(f.computehash(hashtype=hash_algo))
    )


def test_redirect_prefix_encodes_newlines():
    """Ensure raw newlines are url encoded in the generated redirect."""
    request = Namespace(
        custom_fullpath='/\nSet-Cookie:malicious=1;'
    )
    prefix = '\nSet-Cookie:malicious=1;'
    newpath = core.get_bad_url_redirect_path(request, prefix)
    assert '\n' not in newpath


def test_normalize_pkgname_for_url_encodes_newlines():
    """Ensure newlines are url encoded in package names for urls."""
    assert '\n' not in core.normalize_pkgname_for_url(
        '/\nSet-Cookie:malicious=1;'
    )
