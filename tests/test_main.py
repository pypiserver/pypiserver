import logging
import os
import pathlib
import sys
import typing as t
from unittest import mock

import pytest

import pypiserver.bottle
from pypiserver import __main__
from pypiserver.bottle import Bottle


THIS_DIR = pathlib.Path(__file__).parent
HTPASS_FILE = THIS_DIR / "../fixtures/htpasswd.a.a"
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
    exp_kwargs = {"host": "0.0.0.0", "port": 8080, "server": "auto"}
    actual_kwargs = main([])
    # Only assert our expected are are present. We may pass extra kwargs
    # for particular servers, depending on what is available in the python
    # path.
    assert all(map(lambda k: exp_kwargs[k] == actual_kwargs[k], exp_kwargs))


def test_port(main):
    assert main(["--port=8081"])["port"] == 8081
    assert main(["--port", "8081"])["port"] == 8081
    assert main(["-p", "8081"])["port"] == 8081


def test_server(main):
    assert main(["--server=paste"])["server"] == "paste"
    assert main(["--server", "cherrypy"])["server"] == "cherrypy"


def test_wsgiserver_extra_args_present(monkeypatch, main):
    """The wsgi server gets extra keyword arguments."""
    monkeypatch.setattr(
        __main__,
        "guess_auto_server",
        lambda: __main__.AutoServer.WsgiRef,
    )
    assert main([])["handler_class"] is __main__.WsgiHandler


def test_wsgiserver_extra_kwargs_absent(monkeypatch, main):
    """Other servers don't get wsgiserver args."""
    monkeypatch.setattr(
        __main__,
        "guess_auto_server",
        lambda: __main__.AutoServer.Waitress,
    )
    assert "handler_class" not in main([])


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
    assert main.app._pypiserver_config.hash_algo == "sha256"


def test_hash_algo(main):
    main(["--hash-algo=md5"])
    assert main.app._pypiserver_config.hash_algo == "md5"


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


def test_auto_servers() -> None:
    """Test auto servers."""
    # A list of bottle ServerAdapters
    bottle_adapters = tuple(
        a.__name__.lower() for a in pypiserver.bottle.AutoServer.adapters
    )
    # We are going to expect that our AutoServer enum names must match those
    # at least closely enough to be recognizable.
    our_mappings = tuple(map(str.lower, __main__.AutoServer.__members__))

    # Assert that all of our mappings are represented in bottle adapters
    assert all(
        any(mapping in a for a in bottle_adapters) for mapping in our_mappings
    )

    # Assert that our import checking order matches the order in which the
    # adapters are defined in the AutoServer
    our_check_order = tuple(i[0] for i in __main__.AUTO_SERVER_IMPORTS)

    # Some of the servers have more than one check, so we need to remove
    # duplicates before we check for identity with the AutoServer definition.
    seen: t.Dict[__main__.AutoServer, __main__.AutoServer] = {}
    our_check_order = tuple(
        seen.setdefault(i, i) for i in our_check_order if i not in seen
    )

    # We should have the same number of deduped checkers as there are bottle
    # adapters
    assert len(our_check_order) == len(bottle_adapters)

    # And the order should be the same
    assert all(
        us.name.lower() in them
        for us, them in zip(our_check_order, bottle_adapters)
    )


def test_health_endpoint_default(main):
    main([])
    assert main.app._pypiserver_config.health_endpoint == "/health"
    assert "/health" in (route.rule for route in main.app.routes)


def test_health_endpoint_customized(main):
    main(["--health-endpoint", "/healthz"])
    assert main.app._pypiserver_config.health_endpoint == "/healthz"
    assert "/healthz" in (route.rule for route in main.app.routes)


def test_health_endpoint_invalid_customized(main):
    with pytest.raises(SystemExit):
        main(["--health-endpoint", "/health!"])
