#! /usr/bin/env py.test

import os
import pytest
from pypiserver import core


class main_wrapper(object):

    def __init__(self):
        self.run_kwargs = None
        self.pkgdir = None

    def __call__(self, argv):
        print "Running", argv
        core.main(["pypi-server"] + argv)
        return self.run_kwargs


def pytest_funcarg__main(request):

    main = main_wrapper()

    def run(**kwargs):
        print "RUN:", kwargs
        main.run_kwargs = kwargs

    def listdir(pkgdir):
        main.pkgdir = pkgdir
        return []

    monkeypatch = request.getfuncargvalue("monkeypatch")
    monkeypatch.setattr(core, "run", run)
    monkeypatch.setattr(os, "listdir", listdir)
    monkeypatch.setattr(core, "packages", None)
    monkeypatch.setattr(core, "config", core.configuration())

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
    assert core.packages.root == os.path.abspath(".")
    assert main.pkgdir == os.path.abspath(".")


def test_root_r(main):
    main(["-r", "."])
    assert core.packages.root == os.path.abspath(".")
    assert main.pkgdir == os.path.abspath(".")


def test_root_multiple(main):
    pytest.raises(SystemExit, main, [".", "."])
    pytest.raises(SystemExit, main, ["-r", ".", "."])
