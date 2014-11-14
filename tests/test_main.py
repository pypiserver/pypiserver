#! /usr/bin/env py.test

import sys, os, pytest
from pypiserver import core


class main_wrapper(object):

    def __init__(self):
        self.run_kwargs = None
        self.pkgdir = None

    def __call__(self, argv):
        sys.stdout.write("Running %s\n" % (argv,))
        core.main(["pypi-server"] + argv)
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

    monkeypatch.setattr(core, "run", run)
    monkeypatch.setattr(os, "listdir", listdir)

    return main


def test_default_pkgdir(main):
    main([])
    assert main.pkgdir == os.path.expanduser("~/packages")


def test_noargs(main):
    assert main([]) == dict(host="0.0.0.0", port=8080, server="auto")


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
    main(["--fallback-url", "http://pypi.mirror/simple"])
    assert main.app.module.config.fallback_url == "http://pypi.mirror/simple"


def test_fallback_url_default(main):
    main([])
    assert main.app.module.config.fallback_url == \
        "http://pypi.python.org/simple"


def test_welcome_file(main):
    sample_msg_file = os.path.join(os.path.dirname(__file__), 'sample_msg.html')
    main(["--welcome", sample_msg_file])
    with open(sample_msg_file) as fd:
        welcome_msg = fd.read()
    assert 'Hello pypiserver tester!' in main.app.module.config.welcome_msg

def test_welcome_file_default(main):
    main([])
    assert 'Welcome to pypiserver!' in main.app.module.config.welcome_msg
