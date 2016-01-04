#! /usr/bin/env py.test

import pytest, py
from pypiserver.core import parse_version, PkgFile, guess_pkgname_and_version
from pypiserver.manage import is_stable_version, build_releases, filter_stable_releases, filter_latest_pkgs


def touch_files(root, files):
    root = py.path.local(root)
    for f in files:
        root.join(f).ensure()


def pkgfile_from_path(fn):
    pkgname, version = guess_pkgname_and_version(fn)
    return PkgFile(pkgname=pkgname, version=version,
                   root=py.path.local(fn).parts()[1].strpath,
                   fn=fn)


@pytest.mark.parametrize(
    ("version", "is_stable"),
    [("1.0", True),
     ("0.0.0", True),
     ("1.1beta1", False),
     ("1.2.10-123", True),
     ("5.5.0-DEV", False),
     ("1.2-rc1", False),
     ("1.0b1", False)])
def test_is_stable_version(version, is_stable):
    parsed_version = parse_version(version)
    assert is_stable_version(parsed_version) == is_stable


def test_build_releases():
    p = pkgfile_from_path('/home/ralf/pypiserver/d/greenlet-0.2.zip')

    expected = dict(parsed_version=('00000000', '00000003', '*final'),
                    pkgname='greenlet',
                    replaces=p,
                    version='0.3.0')

    res, = list(build_releases(p, ["0.3.0"]))
    for k, v in expected.items():
        assert getattr(res, k) == v


def test_filter_stable_releases():
    p = pkgfile_from_path('/home/ralf/pypiserver/d/greenlet-0.2.zip')
    assert list(filter_stable_releases([p])) == [p]

    p2 = pkgfile_from_path('/home/ralf/pypiserver/d/greenlet-0.5rc1.zip')
    assert list(filter_stable_releases([p2])) == []


def test_filter_latest_pkgs():
    paths = ["/home/ralf/greenlet-0.2.zip",
             "/home/ralf/foo/baz-1.0.zip"
             "/home/ralf/bar/greenlet-0.3.zip"]
    pkgs = [pkgfile_from_path(x) for x in paths]

    assert frozenset(filter_latest_pkgs(pkgs)) == frozenset(pkgs[1:])


def test_filter_latest_pkgs_case_insensitive():
    paths = ["/home/ralf/greenlet-0.2.zip",
             "/home/ralf/foo/baz-1.0.zip"
             "/home/ralf/bar/Greenlet-0.3.zip"]
    pkgs = [pkgfile_from_path(x) for x in paths]

    assert frozenset(filter_latest_pkgs(pkgs)) == frozenset(pkgs[1:])
