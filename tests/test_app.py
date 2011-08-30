#! /usr/bin/env py.test

import os

import twill
from twill.commands import go, code, follow, show, find, reload, showlinks

from pypiserver import core
import bottle
bottle.debug(True)


def pytest_funcarg__root(request):

    tmpdir = request.getfuncargvalue("tmpdir")
    monkeypatch = request.getfuncargvalue("monkeypatch")

    monkeypatch.setattr(core, "packages", core.pkgset(tmpdir.strpath))
    monkeypatch.setattr(core, "config", core.configuration())

    twill.add_wsgi_intercept("localhost", 8080, bottle.default_app)
    twill.add_wsgi_intercept("systemexit.de", 80, bottle.default_app)

    go("http://localhost:8080/")
    return tmpdir


def test_root_count(root):
    go("/")
    show()
    code(200)
    find("PyPI compatible package index serving 0 packages")
    showlinks()

    root.join("Twisted-11.0.0.tar.bz2").write("")
    reload()
    show()
    find("PyPI compatible package index serving 1 packages")


def test_root_hostname(root):
    go("http://systemexit.de/")
    find("easy_install -i http://systemexit.de/simple PACKAGE")


def test_packages_empty(root):
    go("/packages")
    show()
    code(200)
    assert list(showlinks()) == []
