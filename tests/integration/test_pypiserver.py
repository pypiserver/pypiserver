"""Integration tests for the new pypiserver command."""

import sys
from contextlib import contextmanager
from os import chdir, getcwd, environ, path, remove
from shutil import copy2, rmtree
from subprocess import PIPE, Popen
from tempfile import mkdtemp
from time import sleep

import pytest


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


def pypiserver_cmd(venv_dir, root, *args):
    """Yield a command to run pypiserver.

    :param str exc: the path to the python executable to use in
        running pypiserver.
    :param args: extra arguments for ``pypiserver run``
    """
    yield '{}/bin/pypiserver'.format(venv_dir)
    yield 'run'
    yield root
    for arg in args:
        yield arg


def pip_cmd(venv_dir, *args):
    """Yield a command to run pip.

    :param str bindir: the path to the bin directory where the pip
        command can be found.
    :param args: extra arguments for ``pip``
    """
    yield '{}/bin/pip'.format(venv_dir)
    for arg in args:
        yield arg
    if 'install' in args or 'download' in args:
        yield '--index-url'
        yield 'http://localhost:8080'


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
        import ipdb; ipdb.set_trace()
        run(
            (
                'python',
                '{}/setup.py'.format(ROOT_DIR),
                'install',
                # ROOT_DIR,
                # '--prefix',
                # venv_dir,
                # '-e',
                # '{}[passlib]'.format(ROOT_DIR),
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


class TestNoAuth:
    """Tests for running pypiserver with no authentication."""

    @pytest.fixture(scope='class', autouse=True)
    def pkg_root(self, venv):
        """Run pypiserver with no auth."""
        pkg_root = mkdtemp()
        with activate_venv(venv):
            proc = Popen(pypiserver_cmd(
                venv, pkg_root, '--auth-backend', 'no-auth'
            ), env=environ)
        yield pkg_root
        proc.kill()
        rmtree(pkg_root)

    @pytest.fixture()
    def simple_pkg(self, pkg_root):
        """Add the simple package to the repo."""
        copy2(SIMPLE_PKG_PATH, pkg_root)
        yield
        remove(path.join(pkg_root, SIMPLE_PKG))

    @pytest.fixture()
    def simple_dev_pkg(self, pkg_root):
        """Add the simple dev package to the repo."""
        copy2(SIMPLE_DEV_PKG_PATH, pkg_root)
        yield
        remove(path.join(pkg_root, SIMPLE_DEV_PKG))

    @pytest.mark.usefixtures('venv_active')
    def test_install(self, venv, simple_pkg):
        """Test pulling a package with pip from the repo."""
        run(('pip', 'install', 'simple_pkg'))
        assert 'simple-pkg' in run(
            ('pip', 'freeze'), capture=True, env=environ
        )
