"""Test the __main__ module."""

import argparse
import logging
import os
import sys
import warnings
try:
    from unittest import mock
except ImportError:
    import mock

import pytest

from pypiserver import __main__


class main_wrapper(object):

    def __init__(self):
        self.run_kwargs = None
        self.pkgdir = None

    def __call__(self, argv):
        sys.stdout.write("Running %s\n" % (argv,))
        with warnings.catch_warnings():
            __main__.main(argv)
        return self.run_kwargs


@pytest.fixture()
def main(request, monkeypatch):

    main = main_wrapper()

    def run(**kwargs):
        sys.stdout.write("RUN: %s\n" % kwargs)
        app = kwargs.pop("app")
        main.app = app
        main.run_kwargs = kwargs

    def listdir(pkgdir):
        main.pkgdir = pkgdir
        return []

    monkeypatch.setattr("pypiserver.bottle.run", run)
    monkeypatch.setattr("os.listdir", listdir)

    return main


class TestMain(object):
    """Test the main() method."""

    def test_default_pkgdir(self, main):
        main([])
        assert os.path.normpath(main.pkgdir) == (
            os.path.normpath(os.path.expanduser("~/packages"))
        )

    def test_noargs(self, main):
        assert main([]) == {'host': "0.0.0.0", 'port': 8080, 'server': "auto"}

    def test_port(self, main):
        expected = dict(host="0.0.0.0", port=8081, server="auto")
        assert main(["--port=8081"]) == expected
        assert main(["--port", "8081"]) == expected
        assert main(["-p", "8081"]) == expected

    def test_server(self, main):
        assert main(["--server=paste"])["server"] == "paste"
        assert main(["--server", "cherrypy"])["server"] == "cherrypy"

    @pytest.mark.skipif(True, reason='deprecated')
    def test_root(self, main):
        main(["--root", "."])
        assert main.app.module.packages.root == os.path.abspath(".")
        assert main.pkgdir == os.path.abspath(".")

    @pytest.mark.skipif(True, reason='deprecated')
    def test_root_r(self, main):
        main(["-r", "."])
        assert main.app.module.packages.root == os.path.abspath(".")
        assert main.pkgdir == os.path.abspath(".")

    def test_fallback_url(self, main):
        main(["--fallback-url", "https://pypi.mirror/simple"])
        assert main.app.config.fallback_url == "https://pypi.mirror/simple"

    def test_fallback_url_default(self, main):
        main([])
        assert main.app.config.fallback_url == "https://pypi.org/simple"

    def test_hash_algo_default(self, main):
        main([])
        assert main.app.config.hash_algo == 'md5'

    def test_hash_algo(self, main):
        main(['--hash-algo=sha256'])
        assert main.app.config.hash_algo == 'sha256'

    def test_hash_algo_off(self, main):
        main(['--hash-algo=off'])
        assert main.app.config.hash_algo is None
        main(['--hash-algo=0'])
        assert main.app.config.hash_algo is None
        main(['--hash-algo=no'])
        assert main.app.config.hash_algo is None
        main(['--hash-algo=false'])
        assert main.app.config.hash_algo is None

    def test_hash_algo_BAD(self, main):
        with pytest.raises(SystemExit):
            main(['--hash-algo', 'BAD'])

    def test_logging(self, main, tmpdir):
        logfile = tmpdir.mkdir("logs").join('test.log')
        main(["-v", "--log-file", logfile.strpath])
        assert logfile.check(), logfile

    # @pytest.mark.filterwarnings('ignore::DeprecationWarning')
    def test_logging_verbosity(self, main):
        main([])
        assert logging.getLogger().level == logging.WARN
        main(["-v"])
        assert logging.getLogger().level == logging.INFO
        main(["-v", "-v"])
        assert logging.getLogger().level == logging.DEBUG
        main(["-v", "-v", "-v"])
        assert logging.getLogger().level == logging.NOTSET

    def test_welcome_file(self, main):
        sample_msg_file = os.path.join(
            os.path.dirname(__file__),
            "sample_msg.html"
        )
        main(["--welcome", sample_msg_file])
        assert "Hello pypiserver tester!" in main.app.config.welcome_msg

    def test_welcome_file_default(self, main):
        main([])
        assert "Welcome to pypiserver!" in main.app.config.welcome_msg

    def test_password_without_auth_list(self, main, monkeypatch):
        sysexit = mock.MagicMock(side_effect=ValueError('BINGO'))
        monkeypatch.setattr('sys.exit', sysexit)
        with pytest.raises(ValueError) as ex:
            main(["-P", "pswd-file", "-a", ""])
        assert ex.value.args[0] == 'BINGO'

        with pytest.raises(ValueError) as ex:
            main(["-a", "."])
        assert ex.value.args[0] == 'BINGO'
        with pytest.raises(ValueError) as ex:
            main(["-a", ""])
        assert ex.value.args[0] == 'BINGO'

        with pytest.raises(ValueError) as ex:
            main(["-P", "."])
        assert ex.value.args[0] == 'BINGO'

    def test_password_alone(self, main, monkeypatch):
        monkeypatch.setitem(sys.modules, 'passlib', mock.MagicMock())
        monkeypatch.setitem(sys.modules, 'passlib.apache', mock.MagicMock())
        main(["-P", "pswd-file"])
        assert main.app.config.authenticate == ['update']

    def test_dot_password_without_auth_list(self, main, monkeypatch):
        main(["-P", ".", "-a", ""])
        assert main.app.config.authenticate == []

        main(["-P", ".", "-a", "."])
        assert main.app.config.authenticate == []


class TestPypiserverDeprecation(object):
    """Test the deprecation of the old pypi-server command.

    Note that these tests should be removed when the pypi-server
    command is removed.
    """

    @pytest.fixture(autouse=True)
    def patch_run(self, monkeypatch):
        """Monkeypatch argv and the _run_app_from_config method."""
        monkeypatch.setattr(argparse._sys, 'argv', ['pypi-server'])
        monkeypatch.setattr(__main__, '_run_app_from_config', lambda c: None)

    def test_warns(self):
        """Test that a deprecation warning is thrown."""
        warnings.simplefilter('always', category=DeprecationWarning)
        with pytest.warns(DeprecationWarning):
            __main__.main()
