#! /usr/bin/env py.test

from pypiserver import core  # do no remove. needed for bottle
import pytest, bottle, webtest


@pytest.fixture()
def _app(app):
    return app.module


@pytest.fixture
def app(tmpdir):
    from pypiserver import app
    return app(root=tmpdir.strpath)


@pytest.fixture
def testapp(app):
    return webtest.TestApp(app)


@pytest.fixture
def root(tmpdir):
    return tmpdir


@pytest.fixture
def priv(app):
    b = bottle.Bottle()
    b.mount("/priv/", app)
    return b


@pytest.fixture
def testpriv(priv):
    return webtest.TestApp(priv)


def test_root_count(root, testapp):
    resp = testapp.get("/")
    resp.mustcontain("PyPI compatible package index serving 0 packages")
    root.join("Twisted-11.0.0.tar.bz2").write("")
    resp = testapp.get("/")
    resp.mustcontain("PyPI compatible package index serving 1 packages")


def test_root_hostname(testapp):
    resp = testapp.get("/", headers={"Host": "systemexit.de"})
    resp.mustcontain("easy_install -i http://systemexit.de/simple/ PACKAGE")
    # go("http://systemexit.de/")


def test_packages_empty(testapp):
    resp = testapp.get("/packages")
    assert len(resp.html("a")) == 0


def test_favicon(testapp):
    testapp.get("/favicon.ico", status=404)


def test_fallback(root, _app, testapp):
    assert _app.config.redirect_to_fallback
    resp = testapp.get("/simple/pypiserver/", status=302)
    assert resp.headers["Location"] == "http://pypi.python.org/simple/pypiserver/"


def test_no_fallback(root, _app, testapp):
    _app.config.redirect_to_fallback = False
    testapp.get("/simple/pypiserver/", status=404)


def test_serve_no_dotfiles(root, testapp):
    root.join(".foo-1.0.zip").write("secret")
    testapp.get("/packages/.foo-1.0.zip", status=404)


def test_packages_list_no_dotfiles(root, testapp):
    root.join(".foo-1.0.zip").write("secret")
    resp = testapp.get("/packages/")
    assert "foo" not in resp


def test_simple_list_no_dotfiles(root, testapp):
    root.join(".foo-1.0.zip").write("secret")
    resp = testapp.get("/simple/")
    assert "foo" not in resp


def test_simple_list_no_dotfiles2(root, testapp):
    root.join(".foo-1.0.zip").write("secret")
    resp = testapp.get("/simple/")
    assert resp.html("a") == []


def test_serve_no_dotdir(root, testapp):
    root.mkdir(".subdir").join("foo-1.0.zip").write("secret")
    testapp.get("/packages/.subdir/foo-1.0.zip", status=404)


def test_packages_list_no_dotdir(root, testapp):
    root.mkdir(".subdir").join("foo-1.0.zip").write("secret")
    resp = testapp.get("/packages/")
    assert "foo" not in resp


def test_simple_list_no_dotdir(root, testapp):
    root.mkdir(".subdir").join("foo-1.0.zip").write("secret")
    resp = testapp.get("/simple/")
    assert "foo" not in resp


def test_simple_list_no_dotdir2(root, testapp):
    root.mkdir(".subdir").join("foo-1.0.zip").write("secret")
    resp = testapp.get("/simple/foo/")
    assert resp.html("a") == []


def test_simple_index(root, testapp):
    root.join("foobar-1.0.zip").write("")
    root.join("foobar-1.1.zip").write("")
    root.join("foobarbaz-1.1.zip").write("")
    root.join("foobar.baz-1.1.zip").write("")

    resp = testapp.get("/simple/foobar")
    assert len(resp.html("a")) == 2


def test_simple_index_list(root, testapp):
    root.join("foobar-1.0.zip").write("")
    root.join("foobar-1.1.zip").write("")
    root.join("foobarbaz-1.1.zip").write("")
    root.join("foobar.baz-1.1.zip").write("")

    resp = testapp.get("/simple/")
    assert len(resp.html("a")) == 3


def test_simple_index_case(root, testapp):
    root.join("FooBar-1.0.zip").write("")
    root.join("FooBar-1.1.zip").write("")
    resp = testapp.get("/simple/foobar")
    assert len(resp.html("a")) == 2


def test_nonroot_root(testpriv):
    resp = testpriv.get("/priv/", headers={"Host": "nonroot"})
    resp.mustcontain("easy_install -i http://nonroot/priv/simple/ PACKAGE")


def test_nonroot_simple_index(root, testpriv):
    root.join("foobar-1.0.zip").write("")

    for path in ["/priv/simple/foobar",
                "/priv/simple/foobar/"]:
        resp = testpriv.get(path)
        links = resp.html("a")
        assert len(links) == 1
        assert links[0]["href"] == "/priv/packages/foobar-1.0.zip"


def test_nonroot_simple_packages(root, testpriv):
    root.join("foobar-1.0.zip").write("123")
    for path in ["/priv/packages",
                "/priv/packages/"]:
        resp = testpriv.get(path)
        links = resp.html("a")
        assert len(links) == 1
        assert links[0]["href"] == "/priv/packages/foobar-1.0.zip"


def test_root_no_relative_paths(testpriv):
    """https://github.com/schmir/pypiserver/issues/25"""
    resp = testpriv.get("/priv/")
    hrefs = [x["href"] for x in resp.html("a")]
    assert hrefs == ['/priv/packages/', '/priv/simple/', 'http://pypi.python.org/pypi/pypiserver']


def test_simple_index_list_no_duplicates(root, testapp):
    root.join("foo-bar-1.0.tar.gz").write("")
    root.join("foo_bar-1.0-py2.7.egg").write("")

    resp = testapp.get("/simple/")
    assert len(resp.html("a")) == 1


def test_simple_index_list_name_with_underscore(root, testapp):
    root.join("foo_bar-1.0.tar.gz").write("")
    root.join("foo_bar-1.0-py2.7.egg").write("")

    resp = testapp.get("/simple/")
    assert len(resp.html("a")) == 1
    hrefs = [x["href"] for x in resp.html("a")]
    assert hrefs == ["foo_bar/"]


def test_simple_index_egg_and_tarball(root, testapp):
    root.join("foo-bar-1.0.tar.gz").write("")
    root.join("foo_bar-1.0-py2.7.egg").write("")

    resp = testapp.get("/simple/foo-bar")
    assert len(resp.html("a")) == 2


def test_simple_index_list_name_with_underscore_no_egg(root, testapp):
    root.join("foo_bar-1.0.tar.gz").write("")
    root.join("foo-bar-1.1.tar.gz").write("")

    resp = testapp.get("/simple/")
    assert len(resp.html("a")) == 2
    hrefs = set([x["href"] for x in resp.html("a")])
    assert hrefs == set(["foo_bar/", "foo-bar/"])
