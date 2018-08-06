"""Integration tests for the new pypiserver command."""

import os
import sys
from contextlib import contextmanager
from os import chdir, getcwd, environ, listdir, path, remove
from shutil import copy2, rmtree
from subprocess import PIPE, Popen
from tempfile import mkdtemp, mkstemp

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


@contextmanager
def activate_venv(venv_dir):
    """Set up the environment to use the provided venv."""
    start_venv = environ['VIRTUAL_ENV']
    start_pythonpath = environ.get('PYTHONPATH')
    start_launcher = environ.get('__PYVENV_LAUNCHER__')
    environ['VIRTUAL_ENV'] = venv_dir
    environ['PYTHONPATH'] = pythonpath(venv_dir)
    environ['__PYVENV_LAUNCHER__'] = '{}/bin/python'.format(venv_dir)
    with add_to_path(path.join(venv_dir, 'bin')):
        # with changedir(venv_dir):
        yield
    if start_pythonpath is None:
        del environ['PYTHONPATH']
    else:
        environ['PYTHONPATH'] = start_pythonpath
    if start_launcher is None:
        del environ['__PYVENV_LAUNCHER__']
    else:
        environ['__PYVENV_LAUNCHER__'] = start_launcher
    environ['VIRTUAL_ENV'] = start_venv


def pypiserver_cmd(root, *args):
    """Yield a command to run pypiserver.

    :param str exc: the path to the python executable to use in
        running pypiserver.
    :param args: extra arguments for ``pypiserver run``
    """
    # yield '{}/bin/pypiserver'.format(venv_dir)
    yield 'pypiserver'
    yield 'run'
    yield root
    for arg in args:
        yield arg


def pip_cmd(*args):
    """Yield a command to run pip.

    :param args: extra arguments for ``pip``
    """
    yield 'pip'
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
    yield 'twine'
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


@pytest.fixture(scope='module', autouse=True)
def venv():
    """Return the path to a virtual python interpreter.

    Pypiserver is installed into the venv, along with passlib.
    """
    venv_root = mkdtemp()
    venv_dir = path.join(venv_root, 'venv')
    run((
        'virtualenv',
        '-p',
        path.basename(sys.executable),
        '--always-copy',
        venv_dir,
    ))
    with activate_venv(venv_dir):
        run(
            (
                'python',
                '{}/setup.py'.format(ROOT_DIR),
                'install',
            ),
            env=environ
        )
    yield venv_dir
    rmtree(venv_dir)


@contextmanager
def add_to_path(target):
    """Adjust the PATH to add the target at the front."""
    start = environ['PATH']
    environ['PATH'] = '{}:{}'.format(target, start)
    yield
    environ['PATH'] = start


def pythonpath(venv_dir):
    """Get the python path for the venv_dir."""
    return '{}/lib/{}/site-packages'.format(
        venv_dir, path.basename(sys.executable)
    )


@pytest.fixture()
def venv_active(venv):
    """Adjust the PATH to add the venv."""
    with activate_venv(venv):
        yield


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
    def runserver(self, venv, pkg_root):
        """Run pypiserver with no auth."""
        with activate_venv(venv):
            proc = Popen(pypiserver_cmd(pkg_root), env=environ)
        yield proc
        proc.kill()

    @pytest.mark.usefixtures('venv_active', 'simple_pkg')
    def test_install(self):
        """Test pulling a package with pip from the repo."""
        run(pip_cmd('install', 'simple_pkg'))
        assert 'simple-pkg' in run(pip_cmd('freeze'), capture=True)

    @pytest.mark.usefixtures('venv_active')
    def test_upload(self, pkg_root):
        """Test putting a package into the rpeo."""
        assert SIMPLE_PKG not in listdir(pkg_root)
        run(twine_cmd('upload', SIMPLE_PKG_PATH))
        assert SIMPLE_PKG in listdir(pkg_root)

    @pytest.mark.usefixtures('venv_active', 'simple_pkg')
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
    def runserver(self, venv, pkg_root, htpasswd_file):
        """Run with default auth when pypiserver-passlib is installed."""
        with activate_venv(venv):
            run(pip_cmd(
                'install',
                '-i', 'https://pypi.org/simple',
                '-U',
                '--pre',
                'pypiserver-passlib',
            ))
            proc = Popen(
                pypiserver_cmd(pkg_root, '-P', htpasswd_file)
            )
        yield proc
        proc.kill()

    @pytest.mark.usefixtures('venv_active', 'clean_pkg_root')
    def test_upload(self, pkg_root):
        """Test putting a package into the repo."""
        assert SIMPLE_PKG not in listdir(pkg_root)
        run(twine_cmd(
            'upload', '-u', self.USER, '-p', self.PASS, SIMPLE_PKG_PATH
        ))
        assert SIMPLE_PKG in listdir(pkg_root)

    @pytest.mark.usefixtures('venv_active')
    def test_upload_fail(self, pkg_root):
        """Test putting a package into the repo with bad creds."""
        assert SIMPLE_PKG not in listdir(pkg_root)
        proc = Popen(
            twine_cmd('upload', SIMPLE_PKG_PATH), stdout=PIPE, stderr=PIPE
        )
        out, err = map(lambda s: s.decode('utf-8'), proc.communicate())
        assert '403 Client Error' in err
        assert SIMPLE_PKG not in listdir(pkg_root)
