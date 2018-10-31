"""Integration tests for the new pypiserver command."""

from __future__ import (
    absolute_import, division, print_function, unicode_literals
)

import os
import sys
from contextlib import contextmanager
from os import chdir, getcwd, environ, listdir, path, remove
from shutil import copy2, rmtree
from subprocess import PIPE, Popen
from tempfile import mkdtemp, mkstemp

if sys.version_info < (3,):
    from itertools import ifilter as filter  # noqa pylint: disable=no-name-in-module

import pytest
from passlib.apache import HtpasswdFile


THIS_DIR = path.abspath(path.dirname(__file__))
ROOT_DIR = path.abspath(path.join(THIS_DIR, '../..'))

SIMPLE_PKG = 'simple_pkg-0.0.0-py2.py3-none-any.whl'
SIMPLE_PKG_PATH = path.join(THIS_DIR, 'files', SIMPLE_PKG)
SIMPLE_DEV_PKG = 'simple_pkg-0.0.0.dev0-py2.py3-none-any.whl'
SIMPLE_DEV_PKG_PATH = path.join(THIS_DIR, 'files', SIMPLE_DEV_PKG)


@contextmanager
def changedir(target):
    """Change to target and then change back."""
    start = getcwd()
    chdir(target)
    yield
    chdir(start)


def bin_target(target):
    """Get a binary target relative to the current python executable."""
    return path.abspath(path.join(sys.executable, '..', target))


def pypiserver_cmd(root, *args):
    """Yield a command to run pypiserver.

    :param str exc: the path to the python executable to use in
        running pypiserver.
    :param args: extra arguments for ``pypiserver run``
    """
    yield bin_target('pypiserver')
    yield 'run'
    yield root
    for arg in args:
        yield arg


def pip_cmd(*args):
    """Yield a command to run pip.

    :param args: extra arguments for ``pip``
    """
    yield bin_target('pip')
    for arg in args:
        yield arg
    if (any(i in args for i in ('install', 'download', 'search'))
            and '-i' not in args):
        yield '-i'
        yield 'http://localhost:8080'


def twine_cmd(*args):
    """Yield a command to run twine.

    :param args: arguments for `twine`
    """
    yield bin_target('twine')
    for arg in args:
        yield arg
    for part in ('--repository-url', 'http://localhost:8080'):
        yield part
    if '-u' not in args:
        for part in ('-u', 'username'):
            yield part
    if '-p' not in args:
        for part in ('-p', 'password'):
            yield part


def run(args, raise_on_err=True, capture=False, **kwargs):
    """Straightforward implementation to run subprocesses.

    :param args: command args to pass to Popen
    :param kwargs: extra kwargs to pass to Popen
    """
    pipe = PIPE if capture else None
    proc = Popen(args, stdout=pipe, stderr=pipe, **kwargs)
    out, err = proc.communicate()
    if raise_on_err and proc.returncode:
        raise RuntimeError((proc.returncode, out, err))
    if capture:
        return out.decode('utf-8')
    return proc.returncode


@contextmanager
def add_to_path(target):
    """Adjust the PATH to add the target at the front."""
    start = environ['PATH']
    environ['PATH'] = '{}:{}'.format(target, start)
    yield
    environ['PATH'] = start


@contextmanager
def add_to_pythonpath(target):
    """Adjust the PYTHONPATH to add the target at the front."""
    start = environ.get('PYTHONPATH', '')
    environ['PYTHONPATH'] = '{}:{}'.format(target, start)
    yield
    environ['PYTHONPATH'] = start


@pytest.fixture()
def site_packages():
    """Return a temporary directory to use as an additional packages dir."""
    spdir = mkdtemp()
    yield spdir
    rmtree(spdir)


@pytest.fixture(scope='class')
def extra_pythonpath():
    """Return a temporary directory added to the front of the pythonpath."""
    ppath = mkdtemp()
    with add_to_pythonpath(ppath):
        yield ppath
    rmtree(ppath)


@pytest.fixture(scope='session')
def download_passlib():
    """Download passlib into a temporary directory."""
    passlib_dir = mkdtemp()
    with changedir(passlib_dir):
        run((
            bin_target('pip'),
            'download',
            '--no-deps',
            'git+git://github.com/pypiserver/pypiserver-passlib',
        ))
    passlib_file = next(filter(
        lambda x: x.endswith('.zip'),
        os.listdir(passlib_dir)
    ))
    yield passlib_file
    rmtree(passlib_dir)


@pytest.fixture(scope='class')
def install_passlib(download_passlib, extra_pythonpath):
    """Install passlib into the extra pythonpath."""
    run((
        bin_target('pip'),
        'install',
        '--no-deps',
        download_passlib,
    ))


@pytest.fixture(scope='class', autouse=True)
def pkg_root():
    """Run pypiserver with no auth."""
    pkg_root = mkdtemp()
    yield pkg_root
    rmtree(pkg_root)


@pytest.fixture()
def clean_pkg_root(pkg_root):
    """Ensure the pkg root is cleaned after each test."""
    starts = set(listdir(pkg_root))
    yield
    for filename in set(listdir(pkg_root)).difference(starts):
        remove(path.join(pkg_root, filename))


@pytest.fixture()
def simple_pkg(pkg_root):
    """Add the simple package to the repo."""
    copy2(SIMPLE_PKG_PATH, pkg_root)
    yield
    remove(path.join(pkg_root, SIMPLE_PKG))


@pytest.fixture()
def simple_dev_pkg(pkg_root):
    """Add the simple dev package to the repo."""
    copy2(SIMPLE_DEV_PKG_PATH, pkg_root)
    yield
    remove(path.join(pkg_root, SIMPLE_DEV_PKG))


class TestNoAuth(object):
    """Tests for running pypiserver with no authentication."""

    @pytest.fixture(scope='class', autouse=True)
    def runserver(self, pkg_root):
        """Run pypiserver with no auth."""
        proc = Popen(pypiserver_cmd(pkg_root), env=environ)
        yield proc
        proc.kill()

    @pytest.mark.usefixtures('simple_pkg')
    def test_install(self):
        """Test pulling a package with pip from the repo."""
        run(pip_cmd('install', 'simple_pkg'))
        assert 'simple-pkg' in run(pip_cmd('freeze'), capture=True)

    def test_upload(self, pkg_root):
        """Test putting a package into the repo."""
        assert SIMPLE_PKG not in listdir(pkg_root)
        run(twine_cmd('upload', SIMPLE_PKG_PATH))
        assert SIMPLE_PKG in listdir(pkg_root)

    @pytest.mark.usefixtures('simple_pkg')
    def test_search(self):
        """Test results of pip search."""
        out = run(pip_cmd('search', 'simple_pkg'), capture=True)
        assert 'simple_pkg' in out


class TestPasslibAuth(object):
    """Test the passlib auth plugin.

    Normally we would leave plugin integration testing to be performed
    as part of the plugin's test suite. However, because of the
    historical bundling of passlib functionality with pypiserver
    via the ``[passlib]`` extras requirement, we need to check to be
    sure we provide the same functionality here.

    The point here isn't so much to test every possible variation of
    the ``--authenticate`` option, but to ensure that, when the
    ``pypiserver-passlib`` plugin is installed, the defaults work the
    same way as they did previously (authenticating uploads).
    """

    USER = 'pypiserver'
    PASS = 'password'

    @pytest.fixture(scope='class')
    def htpasswd_file(self):
        """Create an HtpasswdFile with a user/pass saved."""
        fp, passfile = mkstemp()
        os.close(fp)
        htpass = HtpasswdFile(passfile)
        htpass.set_password(self.USER, self.PASS)
        htpass.save()
        yield passfile
        remove(passfile)

    @pytest.fixture(scope='class', autouse=True)
    def runserver(self, pkg_root, install_passlib, htpasswd_file):
        """Run with default auth when pypiserver-passlib is installed."""
        proc = Popen(
            pypiserver_cmd(pkg_root, '-P', htpasswd_file)
        )
        yield proc
        proc.kill()

    @pytest.mark.usefixtures('clean_pkg_root')
    def test_upload(self, pkg_root):
        """Test putting a package into the repo."""
        assert SIMPLE_PKG not in listdir(pkg_root)
        run(twine_cmd(
            'upload', '-u', self.USER, '-p', self.PASS, SIMPLE_PKG_PATH
        ))
        assert SIMPLE_PKG in listdir(pkg_root)

    def test_upload_fail(self, pkg_root):
        """Test putting a package into the repo with bad creds."""
        assert SIMPLE_PKG not in listdir(pkg_root)
        proc = Popen(
            twine_cmd('upload', SIMPLE_PKG_PATH), stdout=PIPE, stderr=PIPE
        )
        out, err = map(lambda s: s.decode('utf-8'), proc.communicate())
        assert '403 Client Error' in err
        assert SIMPLE_PKG not in listdir(pkg_root)
