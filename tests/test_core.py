#! /usr/bin/env py.test
# -*- coding: utf-8 -*-

import logging
import os

import pytest

from pypiserver import __main__, core, backend
from pypiserver.pkg_helpers import (
    normalize_pkgname_for_url,
)
from tests.doubles import Namespace


## Enable logging to detect any problems with it
##
__main__.init_logging()


def test_listdir_bad_name(tmp_path):
    tmp_path.joinpath("foo.whl").touch()
    res = list(backend.listdir(tmp_path))
    assert res == []


hashes = (
    # empty-sha256
    (
        "sha256",
        "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    ),
    # empty-md5
    ("md5", "d41d8cd98f00b204e9800998ecf8427e"),
)


@pytest.mark.parametrize(("algo", "digest"), hashes)
def test_hashfile(tmp_path, algo, digest):
    f = tmp_path.joinpath("empty")
    f.touch()
    assert backend.digest_file(str(f), algo) == f"{algo}={digest}"


@pytest.mark.parametrize("hash_algo", ("md5", "sha256", "sha512"))
def test_fname_and_hash(tmp_path, hash_algo):
    """Ensure we are returning the expected hashes for files."""

    def digester(pkg):
        digest = backend.digest_file(pkg.fn, hash_algo)
        pkg.digest = digest
        return digest

    f = tmp_path.joinpath("tmpfile")
    f.touch()
    pkgfile = core.PkgFile("tmp", "1.0.0", str(f), f.parent, f.name)
    pkgfile.digester = digester

    assert pkgfile.fname_and_hash == f"{f.name}#{digester(pkgfile)}"


def test_normalize_pkgname_for_url_encodes_newlines():
    """Ensure newlines are url encoded in package names for urls."""
    assert "\n" not in normalize_pkgname_for_url("/\nSet-Cookie:malicious=1;")
