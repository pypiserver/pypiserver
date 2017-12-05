import logging
import os
import tempfile

import pip
import pytest
import subprocess as sbp

from py.path import local as Path  # @UnresolvedImport


mydir = Path(__file__).dirpath()
log = logging.getLogger(__name__)

smoktest_package = 'pypiserver-test-plugins'

#: a mapping of ``package-name --> package-dir-Path
packages_map = {
    smoktest_package: mydir / 'plugins',
}


def build_wheel(package_dir):
    "build (if not there) and return wheel Path"
    def get_wheels():
        return dist_dir.listdir(lambda f: f.fnmatch('*.whl'))

    setup_script = package_dir / 'setup.py'
    dist_dir = package_dir / 'dist'
    if not dist_dir.check(dir=1) or len(get_wheels()) != 1:
        os.chdir(package_dir)
        if dist_dir.check(dir=1):
            dist_dir.remove(ignore_errors=True)
        sbp.check_output('python setup.py bdist_wheel'.split())

    wheels = get_wheels()
    assert len(wheels) == 1

    return wheels[0]


def install_package(package):
    "Return the full dist-Path installed."
    package_dir = packages_map[package]
    package_path = build_wheel(package_dir)
    pip.main(['install', str(package_path)])
    return package_path


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