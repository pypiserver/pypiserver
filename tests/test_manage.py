#!/usr/bin/env py.test
"""Tests for manage.py."""

from __future__ import absolute_import, print_function, unicode_literals

try:
    from unittest.mock import Mock
except ImportError:
    from mock import Mock

import py
import pytest

from pypiserver import manage
from pypiserver.core import (
    PkgFile,
    guess_pkgname_and_version,
    parse_version,
)
from pypiserver.manage import (
    PipCmd,
    build_releases,
    filter_stable_releases,
    filter_latest_pkgs,
    is_stable_version,
    update_package,
    update_all_packages,
)


def touch_files(root, files):
    root = py.path.local(root)  # pylint: disable=no-member
    for f in files:
        root.join(f).ensure()


def pkgfile_from_path(fn):
    pkgname, version = guess_pkgname_and_version(fn)
    return PkgFile(pkgname=pkgname, version=version,
                   root=py.path.local(fn).parts()[1].strpath,  # noqa pylint: disable=no-member
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


@pytest.mark.parametrize('pip_ver, cmd_type', (
    ('10.0.0', 'd'),
    ('10.0.0rc10', 'd'),
    ('10.0.0b10', 'd'),
    ('10.0.0a3', 'd'),
    ('10.0.0.dev8', 'd'),
    ('10.0.0.dev8', 'd'),
    ('18.0', 'd'),
    ('9.9.8', 'i'),
    ('9.9.8rc10', 'i'),
    ('9.9.8b10', 'i'),
    ('9.9.8a10', 'i'),
    ('9.9.8.dev10', 'i'),
    ('9.9', 'i'),
))
def test_pip_cmd_root(pip_ver, cmd_type):
    """Verify correct determination of the command root by pip version."""
    exp_cmd = (
        'pip',
        '-q',
        'install' if cmd_type == 'i' else 'download',
    )
    assert tuple(PipCmd.update_root(pip_ver)) == exp_cmd


def test_pip_cmd_update():
    """Verify the correct determination of a pip command."""
    index = 'https://pypi.org/simple'
    destdir = 'foo/bar'
    pkg_name = 'mypkg'
    pkg_version = '12.0'
    cmd_root = ('pip', '-q', 'download')
    exp_cmd = cmd_root + (
        '--no-deps',
        '-i',
        index,
        '-d',
        destdir,
        '{}=={}'.format(pkg_name, pkg_version)
    )
    assert exp_cmd == tuple(
        PipCmd.update(cmd_root, destdir, pkg_name, pkg_version)
    )


def test_pip_cmd_update_index_overridden():
    """Verify the correct determination of a pip command."""
    index = 'https://pypi.org/complex'
    destdir = 'foo/bar'
    pkg_name = 'mypkg'
    pkg_version = '12.0'
    cmd_root = ('pip', '-q', 'download')
    exp_cmd = cmd_root + (
        '--no-deps',
        '-i', index,
        '-d', destdir,
        '{}=={}'.format(pkg_name, pkg_version)
    )
    assert exp_cmd == tuple(
        PipCmd.update(cmd_root, destdir, pkg_name, pkg_version, index=index)
    )


def test_update_package(monkeypatch):
    """Test generating an update command for a package."""
    monkeypatch.setattr(manage, 'call', Mock())
    pkg = PkgFile('mypkg', '1.0', replaces=PkgFile('mypkg', '0.9'))
    update_package(pkg, '.')
    manage.call.assert_called_once_with((  # pylint: disable=no-member
        'pip',
        '-q',
        'download',
        '--no-deps',
        '-i', 'https://pypi.org/simple',
        '-d', '.',
        'mypkg==1.0',
    ))


def test_update_package_dry_run(monkeypatch):
    """Test generating an update command for a package."""
    monkeypatch.setattr(manage, 'call', Mock())
    pkg = PkgFile('mypkg', '1.0', replaces=PkgFile('mypkg', '0.9'))
    update_package(pkg, '.', dry_run=True)
    assert not manage.call.mock_calls  # pylint: disable=no-member


def test_update_all_packages(monkeypatch):
    """Test calling update_all_packages()"""
    public_pkg_1 = PkgFile('Flask', '1.0')
    public_pkg_2 = PkgFile('requests', '1.0')
    private_pkg_1 = PkgFile('my_private_pkg', '1.0')
    private_pkg_2 = PkgFile('my_other_private_pkg', '1.0')

    roots_mock = {
        '/opt/pypi': [
            public_pkg_1,
            private_pkg_1,
        ],
        '/data/pypi': [
            public_pkg_2,
            private_pkg_2
        ],
    }

    def core_listdir_mock(directory):
        return roots_mock.get(directory, [])

    monkeypatch.setattr(manage.core, 'listdir', core_listdir_mock)
    monkeypatch.setattr(manage.core, 'read_lines', Mock(return_value=[]))
    monkeypatch.setattr(manage, 'update', Mock(return_value=None))

    destdir = None
    dry_run = False
    stable_only = True
    blacklist_file = None

    update_all_packages(
        roots=list(roots_mock.keys()),
        destdir=destdir,
        dry_run=dry_run,
        stable_only=stable_only,
        blacklist_file=blacklist_file,
    )

    manage.core.read_lines.assert_not_called()   # pylint: disable=no-member
    manage.update.assert_called_once_with(   # pylint: disable=no-member
        frozenset([public_pkg_1, public_pkg_2, private_pkg_1, private_pkg_2]),
        destdir,
        dry_run,
        stable_only
    )


def test_update_all_packages_with_blacklist(monkeypatch):
    """Test calling update_all_packages()"""
    public_pkg_1 = PkgFile('Flask', '1.0')
    public_pkg_2 = PkgFile('requests', '1.0')
    private_pkg_1 = PkgFile('my_private_pkg', '1.0')
    private_pkg_2 = PkgFile('my_other_private_pkg', '1.0')

    roots_mock = {
        '/opt/pypi': [
            public_pkg_1,
            private_pkg_1,
        ],
        '/data/pypi': [
            public_pkg_2,
            private_pkg_2
        ],
    }

    def core_listdir_mock(directory):
        return roots_mock.get(directory, [])

    monkeypatch.setattr(manage.core, 'listdir', core_listdir_mock)
    monkeypatch.setattr(manage.core, 'read_lines', Mock(return_value=['my_private_pkg', 'my_other_private_pkg']))
    monkeypatch.setattr(manage, 'update', Mock(return_value=None))

    destdir = None
    dry_run = False
    stable_only = True
    blacklist_file = '/root/pkg_blacklist'

    update_all_packages(
        roots=list(roots_mock.keys()),
        destdir=destdir,
        dry_run=dry_run,
        stable_only=stable_only,
        blacklist_file=blacklist_file,
    )

    manage.update.assert_called_once_with(   # pylint: disable=no-member
        frozenset([public_pkg_1, public_pkg_2]),
        destdir,
        dry_run,
        stable_only
    )
    manage.core.read_lines.assert_called_once_with(blacklist_file)   # pylint: disable=no-member
