#! /usr/bin/env py.test

import os

import twill
from twill.commands import go, code, follow, show, find, reload, showlinks

from pypiserver import core
import bottle
bottle.debug(True)

fallback_app = bottle.Bottle()


@fallback_app.route("path#.*#")
def pypi_notfound(path):
    return bottle.HTTPError(404)


def pytest_funcarg__root(request):

    tmpdir = request.getfuncargvalue("tmpdir")
    monkeypatch = request.getfuncargvalue("monkeypatch")

    monkeypatch.setattr(core, "packages", core.pkgset(tmpdir.strpath))
    monkeypatch.setattr(core, "config", core.configuration())

    twill.add_wsgi_intercept("localhost", 8080, bottle.default_app)
    twill.add_wsgi_intercept("systemexit.de", 80, bottle.default_app)
    twill.add_wsgi_intercept("pypi.python.org", 80, lambda: fallback_app)

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


def test_favicon(root):
    final_url = go("/favicon.ico")
    show()
    print "FINAL_URL:", final_url
    assert final_url == "http://localhost:8080/favicon.ico"
    code(404)


def test_fallback(root):
    assert core.config.redirect_to_fallback
    final_url = go("/simple/pypiserver/")
    assert final_url == "http://pypi.python.org/simple/pypiserver/"


def test_no_fallback(root):
    core.config.redirect_to_fallback = False
    final_url = go("/simple/pypiserver/")
    assert final_url == "http://localhost:8080/simple/pypiserver/"
