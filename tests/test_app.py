#! /usr/bin/env py.test

import twill
from twill.commands import go, code, show, find, reload, showlinks, notfind
import pytest

try:
    from paste.deploy import loadapp
except ImportError:
    loadapp = None

from pypiserver import core  # do no remove. needed for bottle
import bottle

fallback_app = bottle.Bottle()


@fallback_app.route("path#.*#")
def pypi_notfound(path):
    return bottle.HTTPError(404)


def pytest_funcarg__root(request):
    return request.getfuncargvalue("env")["root"]


def pytest_funcarg___app(request):
    return request.getfuncargvalue("env")["_app"]


def pytest_funcarg__env(request):
    tmpdir = request.getfuncargvalue("tmpdir")
    from pypiserver import app
    a = app(root=tmpdir.strpath)

    if loadapp:
        pini = tmpdir.join(".paste.ini")
        pini.write("""
[composite:main]
use = egg:Paste#urlmap
/priv/ = private

[app:private]
paste.app_factory = pypiserver:paste_app_factory
root = %s

[server:main]
use = egg:gunicorn#main
host = 0.0.0.0
port = 8001
workers = 5
accesslog = -
""" % tmpdir)

        twill.add_wsgi_intercept("nonroot", 80, lambda: loadapp("config:%s" % pini))

    twill.add_wsgi_intercept("localhost", 8080, lambda: a)
    twill.add_wsgi_intercept("systemexit.de", 80, lambda: a)
    twill.add_wsgi_intercept("pypi.python.org", 80, lambda: fallback_app)

    def cleanup():
        twill.remove_wsgi_intercept("localhost", 8080)
        twill.remove_wsgi_intercept("systemexit.de", 80)
        twill.remove_wsgi_intercept("pypi.python.org", 80)
        if loadapp:
            twill.remove_wsgi_intercept("nonroot", 80)

    request.addfinalizer(cleanup)

    go("http://localhost:8080/")
    return dict(root=tmpdir, app=a, _app=a.module)


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
    find("easy_install -i http://systemexit.de/simple/ PACKAGE")


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


def test_fallback(root, _app):
    assert _app.config.redirect_to_fallback
    final_url = go("/simple/pypiserver/")
    assert final_url == "http://pypi.python.org/simple/pypiserver/"


def test_no_fallback(root, _app):
    _app.config.redirect_to_fallback = False
    final_url = go("/simple/pypiserver/")
    assert final_url == "http://localhost:8080/simple/pypiserver/"
    code(404)


def test_serve_no_dotfiles(root):
    root.join(".foo-1.0.zip").write("secret")
    go("/packages/.foo-1.0.zip")
    show()
    code(404)


def test_packages_list_no_dotfiles(root):
    root.join(".foo-1.0.zip").write("secret")
    go("/packages/")
    notfind("foo")


def test_simple_list_no_dotfiles(root):
    root.join(".foo-1.0.zip").write("secret")
    go("/simple/")
    notfind("foo")


def test_simple_list_no_dotfiles2(root):
    root.join(".foo-1.0.zip").write("secret")
    go("/simple/.foo/")
    assert list(showlinks()) == []


def test_serve_no_dotdir(root):
    root.mkdir(".subdir").join("foo-1.0.zip").write("secret")
    go("/packages/.subdir/foo-1.0.zip")
    code(404)


def test_packages_list_no_dotdir(root):
    root.mkdir(".subdir").join("foo-1.0.zip").write("secret")
    go("/packages/")
    show()
    notfind("foo")


def test_simple_list_no_dotdir(root):
    root.mkdir(".subdir").join("foo-1.0.zip").write("secret")
    go("/simple/")
    show()
    notfind("foo")


def test_simple_list_no_dotdir2(root):
    root.mkdir(".subdir").join("foo-1.0.zip").write("secret")
    go("/simple/foo/")
    show()
    assert list(showlinks()) == []


def test_simple_index(root):
    root.join("foobar-1.0.zip").write("")
    root.join("foobar-1.1.zip").write("")
    root.join("foobarbaz-1.1.zip").write("")
    root.join("foobar.baz-1.1.zip").write("")

    go("/simple/foobar")
    show()
    links = list(showlinks())
    assert len(links) == 2


def test_simple_index_list(root):
    root.join("foobar-1.0.zip").write("")
    root.join("foobar-1.1.zip").write("")
    root.join("foobarbaz-1.1.zip").write("")
    root.join("foobar.baz-1.1.zip").write("")

    go("/simple/")
    show()
    links = list(showlinks())
    assert len(links) == 3


def test_simple_index_case(root):
    root.join("FooBar-1.0.zip").write("")
    root.join("FooBar-1.1.zip").write("")

    go("/simple/foobar")
    show()
    links = list(showlinks())
    assert len(links) == 2

need_paste = pytest.mark.skipif("loadapp is None")


@need_paste
def test_nonroot_root(root):
    go("http://nonroot/priv/")
    find("easy_install -i http://nonroot/priv/simple/ PACKAGE")


@need_paste
def test_nonroot_simple_index(root):
    root.join("foobar-1.0.zip").write("")

    for url in ["http://nonroot/priv/simple/foobar",
                "http://nonroot/priv/simple/foobar/"]:
        go(url)
        show()
        links = list(showlinks())
        assert len(links) == 1
        assert links[0].url == "/priv/packages/foobar-1.0.zip"


@need_paste
def test_nonroot_simple_packages(root):
    root.join("foobar-1.0.zip").write("123")
    for url in ["http://nonroot/priv/packages",
                "http://nonroot/priv/packages/"]:
        go(url)
        show()
        links = list(showlinks())
        assert len(links) == 1
        assert links[0].url == "/priv/packages/foobar-1.0.zip"
