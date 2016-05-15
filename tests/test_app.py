#! /usr/bin/env py.test

import contextlib
import glob
import logging
import os
from pypiserver import __main__, bottle
import subprocess

import pytest
import webtest

import test_core

try:
    from html.parser import HTMLParser
except ImportError:
    from HTMLParser import HTMLParser


# Enable logging to detect any problems with it
##
__main__.init_logging(level=logging.NOTSET)
hp = HTMLParser()


@pytest.fixture()
def _app(app):
    return app.module


@pytest.fixture
def app(tmpdir):
    from pypiserver import app
    return app(root=tmpdir.strpath, authenticated=[])


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


@pytest.fixture(params=["  ",  # Mustcontain test below fails when string is empty.
                        "Hey there!",
                        "<html><body>Hey there!</body></html>",
                        ])
def welcome_file_no_vars(request, root):
    wfile = root.join("testwelcome.html")
    wfile.write(request.param)

    return wfile


@pytest.fixture()
def welcome_file_all_vars(request, root):
    msg = """
    {{URL}}
    {{VERSION}}
    {{NUMPKGS}}
    {{PACKAGES}}
    {{SIMPLE}}
    """
    wfile = root.join("testwelcome.html")
    wfile.write(msg)

    return wfile


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


def test_root_welcome_msg_no_vars(root, welcome_file_no_vars):
    from pypiserver import app
    app = app(root=root.strpath, welcome_file=welcome_file_no_vars.strpath)
    testapp = webtest.TestApp(app)
    resp = testapp.get("/")
    from pypiserver import __version__ as pver
    resp.mustcontain(welcome_file_no_vars.read(), no=pver)


def test_root_welcome_msg_all_vars(root, welcome_file_all_vars):
    from pypiserver import app
    app = app(root=root.strpath, welcome_file=welcome_file_all_vars.strpath)
    testapp = webtest.TestApp(app)
    resp = testapp.get("/")

    from pypiserver import __version__ as pver
    resp.mustcontain(pver)


def test_root_welcome_msg_antiXSS(testapp):
    """https://github.com/pypiserver/pypiserver/issues/77"""
    resp = testapp.get(
        "/?<alert>Red</alert>", headers={"Host": "somehost.org"})
    resp.mustcontain("alert", "somehost.org", no="<alert>")


def test_root_remove_not_found_msg_antiXSS(testapp):
    """https://github.com/pypiserver/pypiserver/issues/77"""
    resp = testapp.post("/",  expect_errors=True,
                        headers={"Host": "somehost.org"},
                        params={':action': 'remove_pkg',
                                'name': '<alert>Red</alert>',
                                'version': '1.1.1'})
    resp.mustcontain("alert", "somehost.org", no="<alert>")


def test_packages_redirect(testapp):
    resp = testapp.get("/packages")
    assert resp.status_code >= 300
    assert resp.status_code < 400
    assert resp.location.endswith('/packages/')


def test_packages_empty(testapp):
    resp = testapp.get("/packages/")
    assert len(resp.html("a")) == 0


def test_favicon(testapp):
    testapp.get("/favicon.ico", status=404)


def test_fallback(root, _app, testapp):
    assert _app.config.redirect_to_fallback
    resp = testapp.get("/simple/pypiserver/", status=302)
    assert resp.headers[
        "Location"] == "http://pypi.python.org/simple/pypiserver/"


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


def test_simple_redirect(testapp):
    resp = testapp.get("/simple")
    assert resp.status_code >= 300
    assert resp.status_code < 400
    assert resp.location.endswith('/simple/')


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


def test_simple_name_redirect(testapp):
    resp = testapp.get("/simple/foobar")
    assert resp.status_code >= 300
    assert resp.status_code < 400
    assert resp.location.endswith('/simple/foobar/')


@pytest.mark.parametrize('package,normalized', [
    ('FooBar', 'foobar'),
    ('Foo.Bar', 'foo-bar'),
    ('foo_bar', 'foo-bar'),
    ('Foo-Bar', 'foo-bar'),
    ('foo--_.bar', 'foo-bar'),
])
def test_simple_normalized_name_redirect(testapp, package, normalized):
    resp = testapp.get("/simple/{0}/".format(package))
    assert resp.status_code >= 300
    assert resp.status_code < 400
    assert resp.location.endswith('/simple/{0}/'.format(normalized))


def test_simple_index(root, testapp):
    root.join("foobar-1.0.zip").write("")
    root.join("foobar-1.1.zip").write("")
    root.join("foobarbaz-1.1.zip").write("")
    root.join("foobar.baz-1.1.zip").write("")

    resp = testapp.get("/simple/foobar/")
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
    resp = testapp.get("/simple/foobar/")
    assert len(resp.html("a")) == 2


def test_nonroot_root(testpriv):
    resp = testpriv.get("/priv/", headers={"Host": "nonroot"})
    resp.mustcontain("easy_install -i http://nonroot/priv/simple/ PACKAGE")


def test_nonroot_simple_index(root, testpriv):
    root.join("foobar-1.0.zip").write("")
    resp = testpriv.get("/priv/simple/foobar/")
    links = resp.html("a")
    assert len(links) == 1
    assert links[0]["href"].startswith("/priv/packages/foobar-1.0.zip#")


def test_nonroot_simple_packages(root, testpriv):
    root.join("foobar-1.0.zip").write("123")
    resp = testpriv.get("/priv/packages/")
    links = resp.html("a")
    assert len(links) == 1
    assert links[0]["href"].startswith("/priv/packages/foobar-1.0.zip#")


def test_root_no_relative_paths(testpriv):
    """https://github.com/pypiserver/pypiserver/issues/25"""
    resp = testpriv.get("/priv/")
    hrefs = [x["href"] for x in resp.html("a")]
    assert hrefs == ['/priv/packages/', '/priv/simple/',
                     'http://pypi.python.org/pypi/pypiserver']


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
    assert hrefs == ["foo-bar/"]


def test_simple_index_egg_and_tarball(root, testapp):
    root.join("foo-bar-1.0.tar.gz").write("")
    root.join("foo_bar-1.0-py2.7.egg").write("")

    resp = testapp.get("/simple/foo-bar/")
    assert len(resp.html("a")) == 2


def test_simple_index_list_name_with_underscore_no_egg(root, testapp):
    root.join("foo_bar-1.0.tar.gz").write("")
    root.join("foo-bar-1.1.tar.gz").write("")

    resp = testapp.get("/simple/")
    assert len(resp.html("a")) == 1
    hrefs = set([x["href"] for x in resp.html("a")])
    assert hrefs == set(["foo-bar/"])


def test_no_cache_control_set(root, _app, testapp):
    assert not _app.config.cache_control
    root.join("foo_bar-1.0.tar.gz").write("")
    resp = testapp.get("/packages/foo_bar-1.0.tar.gz")
    assert "Cache-Control" not in resp.headers


def test_cache_control_set(root):
    from pypiserver import app
    AGE = 86400
    app_with_cache = webtest.TestApp(app(root=root.strpath, cache_control=AGE))
    root.join("foo_bar-1.0.tar.gz").write("")
    resp = app_with_cache.get("/packages/foo_bar-1.0.tar.gz")
    assert "Cache-Control" in resp.headers
    assert resp.headers["Cache-Control"] == 'public, max-age=%s' % AGE

def test_upload_noAction(root, testapp):
    resp = testapp.post("/", expect_errors=1)
    assert resp.status == '400 Bad Request'
    assert "Missing ':action' field!" in hp.unescape(resp.text)

def test_upload_badAction(root, testapp):
    resp = testapp.post("/", params={':action': 'BAD'}, expect_errors=1)
    assert resp.status == '400 Bad Request'
    assert "Unsupported ':action' field: BAD" in hp.unescape(resp.text)

@pytest.mark.parametrize(("package"), [f[0] 
        for f in test_core.files 
        if f[1] and '/' not in f[0]])
def test_upload(package, root, testapp):
    resp = testapp.post("/", params={':action': 'file_upload'},
            upload_files=[('content', package, b'')])
    assert resp.status_int == 200
    uploaded_pkgs = [f.basename for f in root.listdir()]
    assert len(uploaded_pkgs) == 1
    assert uploaded_pkgs[0].lower() == package.lower()

@pytest.mark.parametrize(("package"), [f[0] 
        for f in test_core.files 
        if f[1] and '/' not in f[0]])
def test_upload_with_signature(package, root, testapp):
    resp = testapp.post("/", params={':action': 'file_upload'},
            upload_files=[
                    ('content', package, b''), 
                    ('gpg_signature', '%s.asc' % package, b'')])
    assert resp.status_int == 200
    uploaded_pkgs = [f.basename.lower() for f in root.listdir()]
    assert len(uploaded_pkgs) == 2
    assert package.lower() in uploaded_pkgs
    assert '%s.asc' % package.lower() in uploaded_pkgs

@pytest.mark.parametrize(("package"), [
        f[0] for f in test_core.files
        if f[1] is None])
def test_upload_badFilename(package, root, testapp):
    resp = testapp.post("/", params={':action': 'file_upload'},
            upload_files=[('content', package, b'')],
            expect_errors=1)
    assert resp.status == '400 Bad Request'
    assert "Bad filename: %s" % package in resp.text


@pytest.mark.parametrize(("name", "version"), [
        (None, None),
        (None, ''),
        ('', None),
        (None, '1'),
        ('pkg', None),
        ('', '1'),
        ('pkg', ''),
])
def test_remove_pkg_missingNaveVersion(name, version, root, testapp):
    msg = "Missing 'name'/'version' fields: name=%s, version=%s"
    params = {':action': 'remove_pkg', 'name': name, 'version': version}
    params = dict((k, v) for k,v in params.items() if v is not None)
    resp = testapp.post("/", expect_errors=1, params=params)
    
    assert resp.status == '400 Bad Request'
    assert msg %(name, version) in hp.unescape(resp.text)

def test_remove_pkg_notFound(root, testapp):
    resp = testapp.post("/", expect_errors=1,
            params={
                    ':action': 'remove_pkg',
                    'name': 'foo',
                    'version': '123',
    })
    assert resp.status == '404 Not Found'
    assert "foo (123) not found" in hp.unescape(resp.text)

@pytest.mark.xfail()
def test_remove_pkg(root, testapp):
    assert 0
