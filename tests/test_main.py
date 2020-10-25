import logging
import os
import pathlib
import sys
import typing as t
from unittest import mock

import pytest

from pypiserver import __main__
from pypiserver.bottle import Bottle


THIS_DIR = pathlib.Path(__file__).parent
HTPASS_FILE = THIS_DIR / "htpasswd.a.a"
IGNORELIST_FILE = THIS_DIR / "test-ignorelist"


class main_wrapper:
    app: t.Optional[Bottle]
    run_kwargs: t.Optional[dict]
    update_args: t.Optional[tuple]
    update_kwargs: t.Optional[dict]

    def __init__(self):
        self.app = None
        self.run_kwargs = None
        self.update_args = None
        self.update_kwargs = None

    def __call__(self, argv):
        sys.stdout.write(f"Running {argv}\n")
        # always sets the package directory to this directory, regardless of
        # other passed args.
        __main__.main([str(THIS_DIR)] + argv)
        return self.run_kwargs


@pytest.fixture()
def main(monkeypatch):

    main = main_wrapper()

    def run(**kwargs):
        sys.stdout.write(f"RUN: {kwargs}\n")
        app = kwargs.pop("app")
        main.app = app
        main.run_kwargs = kwargs

    def update(*args, **kwargs):
        main.update_args = args
        main.update_kwargs = kwargs

    monkeypatch.setattr("pypiserver.bottle.run", run)
    monkeypatch.setattr("pypiserver.manage.update_all_packages", update)

    return main


def test_default_pkgdir(main):
    main([])
    assert main.app._pypiserver_config.roots == [THIS_DIR]


def test_noargs(main):
    # Assert we're calling with the default host, port, and server, and
    # assume that we've popped `app` off of the bottle args in our `main`
    # fixture.
    assert main([]) == {"host": "0.0.0.0", "port": 8080, "server": "auto"}


def test_port(main):
    expected = dict(host="0.0.0.0", port=8081, server="auto")
    assert main(["--port=8081"]) == expected
    assert main(["--port", "8081"]) == expected
    assert main(["-p", "8081"]) == expected


def test_server(main):
    assert main(["--server=paste"])["server"] == "paste"
    assert main(["--server", "cherrypy"])["server"] == "cherrypy"


def test_root_multiple(main):
    # Remember we're already setting THIS_DIR as a root in the `main` fixture
    main([str(THIS_DIR.parent)])
    assert main.app._pypiserver_config.roots == [
        THIS_DIR,
        THIS_DIR.parent,
    ]


def test_fallback_url(main):
    main(["--fallback-url", "https://pypi.mirror/simple"])
    assert (
        main.app._pypiserver_config.fallback_url == "https://pypi.mirror/simple"
    )


def test_fallback_url_default(main):
    main([])
    assert (
        main.app._pypiserver_config.fallback_url == "https://pypi.org/simple/"
    )


def test_hash_algo_default(main):
    main([])
    assert main.app._pypiserver_config.hash_algo == "md5"


def test_hash_algo(main):
    main(["--hash-algo=sha256"])
    assert main.app._pypiserver_config.hash_algo == "sha256"


def test_hash_algo_off(main):
    main(["--hash-algo=off"])
    assert main.app._pypiserver_config.hash_algo is None
    main(["--hash-algo=0"])
    assert main.app._pypiserver_config.hash_algo is None
    main(["--hash-algo=no"])
    assert main.app._pypiserver_config.hash_algo is None
    main(["--hash-algo=false"])
    assert main.app._pypiserver_config.hash_algo is None


def test_hash_algo_BAD(main):
    with pytest.raises(SystemExit) as excinfo:
        main(["--hash-algo BAD"])


def test_logging(main, tmpdir):
    logfile = tmpdir.mkdir("logs").join("test.log")
    main(["-v", "--log-file", logfile.strpath])
    assert logfile.check(), logfile


def test_logging_verbosity(main):
    main([])
    assert logging.getLogger().level == logging.WARN
    main(["-v"])
    assert logging.getLogger().level == logging.INFO
    main(["-v", "-v"])
    assert logging.getLogger().level == logging.DEBUG
    main(["-v", "-v", "-v"])
    assert logging.getLogger().level == logging.NOTSET


@pytest.mark.parametrize(
    "cli_arg, expected_stream",
    [
        ("stderr", sys.stderr),
        ("stdout", sys.stdout),
        ("none", None),
    ],
)
@mock.patch.object(__main__, "init_logging")
def test_log_to_stdout(init_logging, main, cli_arg, expected_stream):
    main(["--log-stream", cli_arg])
    assert init_logging.call_args[1].get("stream") is expected_stream


@pytest.fixture
def dummy_logger():
    logger = logging.getLogger("test")
    yield logger
    logger.handlers = []


def test_init_logging_with_stream(dummy_logger):
    assert not dummy_logger.handlers

    __main__.init_logging(stream=sys.stdout, logger=dummy_logger)
    assert isinstance(dummy_logger.handlers[0], logging.StreamHandler)
    assert dummy_logger.handlers[0].stream is sys.stdout


def test_init_logging_with_none_stream_doesnt_add_stream_handler(dummy_logger):
    assert not dummy_logger.handlers

    __main__.init_logging(stream=None, logger=dummy_logger)
    assert not dummy_logger.handlers


def test_welcome_file(main):
    sample_msg_file = os.path.join(os.path.dirname(__file__), "sample_msg.html")
    main(["--welcome", sample_msg_file])
    assert "Hello pypiserver tester!" in main.app._pypiserver_config.welcome_msg


def test_welcome_file_default(main):
    main([])
    assert "Welcome to pypiserver!" in main.app._pypiserver_config.welcome_msg


def test_password_without_auth_list(main, monkeypatch):
    sysexit = mock.MagicMock(side_effect=ValueError("BINGO"))
    monkeypatch.setattr("sys.exit", sysexit)
    with pytest.raises(ValueError) as ex:
        main(["-P", str(HTPASS_FILE), "-a", ""])
    assert ex.value.args[0] == "BINGO"

    with pytest.raises(ValueError) as ex:
        main(["-a", "."])
    assert ex.value.args[0] == "BINGO"
    with pytest.raises(ValueError) as ex:
        main(["-a", ""])
    assert ex.value.args[0] == "BINGO"

    with pytest.raises(ValueError) as ex:
        main(["-P", "."])
    assert ex.value.args[0] == "BINGO"


def test_password_alone(main, monkeypatch):
    monkeypatch.setitem(sys.modules, "passlib", mock.MagicMock())
    monkeypatch.setitem(sys.modules, "passlib.apache", mock.MagicMock())
    main(["-P", str(HTPASS_FILE)])
    assert main.app._pypiserver_config.authenticate == ["update"]


def test_dot_password_without_auth_list(main, monkeypatch):
    main(["-P", ".", "-a", "."])
    assert main.app._pypiserver_config.authenticate == []


def test_blacklist_file(main):
    """
    Test that calling the app with the --blacklist-file argument does not
    throw a getopt error
    """
    main(["-U", "--blacklist-file", str(IGNORELIST_FILE)])
    assert main.update_kwargs["ignorelist"] == ["mypiserver", "something"]
