#! /usr/bin/env py.test

import sys, os, pytest, logging
from pypiserver import __main__
try:
    from unittest import mock
except ImportError:
    import mock


class main_wrapper(object):

    def __init__(self):
        self.run_kwargs = None
        self.pkgdir = None

    def __call__(self, argv):
        sys.stdout.write("Running %s\n" % (argv,))
        __main__.main(["pypi-server"] + argv)
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


def test_default_pkgdir(main):
    main([])
    assert os.path.normpath(main.pkgdir) == os.path.normpath(os.path.expanduser("~/packages"))


def test_noargs(main):
    assert main([]) == {'host': "0.0.0.0", 'port': 8080, 'server': "auto"}


def test_port(main):
    expected = dict(host="0.0.0.0", port=8081, server="auto")
    assert main(["--port=8081"]) == expected
    assert main(["--port", "8081"]) == expected
    assert main(["-p", "8081"]) == expected


def test_server(main):
    assert main(["--server=paste"])["server"] == "paste"
    assert main(["--server", "cherrypy"])["server"] == "cherrypy"


def test_root(main):
    main(["--root", "."])
    assert main.app.module.packages.root == os.path.abspath(".")
    assert main.pkgdir == os.path.abspath(".")


def test_root_r(main):
    main(["-r", "."])
    assert main.app.module.packages.root == os.path.abspath(".")
    assert main.pkgdir == os.path.abspath(".")


# def test_root_multiple(main):
#     pytest.raises(SystemExit, main, [".", "."])
#     pytest.raises(SystemExit, main, ["-r", ".", "."])


def test_fallback_url(main):
    main(["--fallback-url", "https://pypi.mirror/simple"])
    assert main.app.module.config.fallback_url == "https://pypi.mirror/simple"


def test_fallback_url_default(main):
    main([])
    assert main.app.module.config.fallback_url == "https://pypi.org/simple"


def test_hash_algo_default(main):
    main([])
    assert main.app.module.config.hash_algo == 'md5'

def test_hash_algo(main):
    main(['--hash-algo=sha256'])
    assert main.app.module.config.hash_algo == 'sha256'

def test_hash_algo_off(main):
    main(['--hash-algo=off'])
    assert main.app.module.config.hash_algo is None
    main(['--hash-algo=0'])
    assert main.app.module.config.hash_algo is None
    main(['--hash-algo=no'])
    assert main.app.module.config.hash_algo is None
    main(['--hash-algo=false'])
    assert main.app.module.config.hash_algo is None

def test_hash_algo_BAD(main):
    with pytest.raises(SystemExit) as excinfo:
        main(['--hash-algo BAD'])
    #assert excinfo.value.message == 'some info'     main(['--hash-algo BAD'])
    print(excinfo)


def test_logging(main, tmpdir):
    logfile = tmpdir.mkdir("logs").join('test.log')
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
    "cli_arg, expected_stream",[
        ("stderr", sys.stderr),
        ("stdout", sys.stdout),
        ("none", None),
    ]
)
@mock.patch.object(__main__, "init_logging")
def test_log_to_stdout(init_logging, main, cli_arg, expected_stream):
    main(["--log-stream", cli_arg])
    assert init_logging.call_args[1].get("stream") is expected_stream


@pytest.fixture
def dummy_logger():
    logger = logging.getLogger('test')
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
    assert "Hello pypiserver tester!" in main.app.module.config.welcome_msg

def test_welcome_file_default(main):
    main([])
    assert "Welcome to pypiserver!" in main.app.module.config.welcome_msg

def test_password_without_auth_list(main, monkeypatch):
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

def test_password_alone(main, monkeypatch):
    monkeypatch.setitem(sys.modules, 'passlib', mock.MagicMock())
    monkeypatch.setitem(sys.modules, 'passlib.apache', mock.MagicMock())
    main(["-P", "pswd-file"])
    assert main.app.module.config.authenticated == ['update']

def test_dot_password_without_auth_list(main, monkeypatch):
    main(["-P", ".", "-a", ""])
    assert main.app.module.config.authenticated == []

    main(["-P", ".", "-a", "."])
    assert main.app.module.config.authenticated == []


def test_blacklist_file(main):
    """
    Test that calling the app with the --blacklist-file argument does not
    throw a getopt error
    """
    blacklist_file = "/root/pkg_blacklist"
    main(["--blacklist-file", blacklist_file])
