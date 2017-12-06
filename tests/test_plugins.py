import logging
import os
import sys
import tempfile

import pip
import pkg_resources
import pytest

from py.path import local as Path  # @UnresolvedImport


mydir = Path(__file__).dirpath()
log = logging.getLogger(__name__)

smoktest_package = 'pypiserver-test-plugins'

#: a mapping of ``package-name --> package-dir-Path
packages_map = {
    smoktest_package: mydir / 'plugins',
}


def install_package(package):
    "Return the full dist-Path installed."
    package_dir = packages_map[package]
    package_dir.chdir()
    pip.main('install -e .'.split())
    pkg_resources.working_set.add_entry(str(package_dir))

    return package_dir


def uninstall_package(package):
    try:
        pip.main(['uninstall', '-y', package])
    except Exception as ex:
        log.warning(
            "Uninstalling %r failed due to: %s!\n"
            "  Probably installation had failed??" % (package, ex))


def clean_mark_files(*fpaths):
    for fpath in fpaths:
        try:
            fpath.remove()
        except Exception as ex:
            log.warning(
                "Could not delete mark-file %s due to: %s!\n"
                "Probably this is the 1st run??" % (fpath, ex))


loadable_fpath = Path(tempfile.gettempdir()) / 'loadable.txt'
#: File written by smoketest *installable* plugin.
installable_fpath = Path(tempfile.gettempdir()) / 'installable.txt'


@pytest.fixture
def with_smoketest_plugins():
    ## Clean l-ft overs from previous TCs.
    clean_mark_files(loadable_fpath, installable_fpath)
    install_package(smoktest_package)
    try:
        yield
    finally:
        clean_mark_files(loadable_fpath, installable_fpath)
        uninstall_package(smoktest_package)


def test_no_plugins1():
    "Test no plugins installed BEFORE any `pip install`."
    assert not loadable_fpath.check()
    assert not installable_fpath.check()

def test_plugins_smoketest(with_smoketest_plugins):
    "Test smoketest-plugins write expected files."
    assert not loadable_fpath.check()
    assert not installable_fpath.check()

    ## Init of plugins happens on import-time.
    import pypiserver  # @UnusedImport

    assert loadable_fpath.check()
    assert installable_fpath.check()

def test_no_plugins2():
    "Test no plugins installed AFTER `pip uninstall`."
    assert not loadable_fpath.check()
    assert not installable_fpath.check()