#! /usr/bin/env python
"""minimal PyPI like server for use with pip/easy_install"""

import os, sys
from pypiserver import bottle
sys.modules["bottle"] = bottle

from bottle import route, run, static_file, redirect, request, debug
import mimetypes
mimetypes.add_type("application/octet-stream", ".egg")

packages = None


class pkgset(object):
    def __init__(self, root):
        self.root = root

    def find_packages(self, prefix=""):
        files = []
        for x in os.listdir(self.root):
            if not x.startswith(prefix):
                continue
            fn = os.path.join(self.root, x)
            if os.path.isfile(fn):
                files.append(x)
        return files

    def find_prefixes(self):
        files = self.find_packages()
        prefixes = set()
        for x in files:
            parts = x.split("-")[:-1]
            for i in range(len(parts)):
                prefixes.add("-".join(parts[:i + 1]))
        return prefixes


@route('/')
def root():
    return request.url
    redirect("/simple/")


@route("/simple")
@route("/simple/")
def simpleindex():
    prefixes = list(packages.find_prefixes())
    prefixes.sort()
    res = ["<html><head><title>Simple Index</title></head><body>\n"]
    for x in prefixes:
        res.append('<a href="/simple/%s/">%s</a><br>\n' % (x, x))
    res.append("</body></html>")
    return "".join(res)


@route("/simple/:prefix")
@route("/simple/:prefix/")
def simple(prefix=""):
    files = packages.find_packages(prefix)
    files.sort()
    res = ["<html><head><title>Links for %s</title></head><body>\n" % prefix]
    res.append("<h1>Links for %s</h1>\n" % prefix)
    for x in files:
        res.append('<a href="/packages/%s">%s</a><br>\n' % (x, x))
    res.append("</body></html>\n")
    return "".join(res)


@route('/packages/')
def list_packages():
    files = packages.find_packages()
    files.sort()
    res = ["<html><head><title>Index of packages</title></head><body>\n"]
    for x in files:
        res.append('<a href="%s">%s</a><br>\n' % (x, x))
    res.append("</body></html>\n")
    return "".join(res)


@route('/packages/:filename')
def server_static(filename):
    return static_file(filename, root=packages.root)


def choose_server():
    server = "auto"
    for x in ["paste", "cherrypy", "twisted"]:
        try:
            __import__(x)
            return x
        except:
            pass


def main():
    global packages
    root = os.path.expanduser("~/packages/")
    packages = pkgset(root)
    server = choose_server()
    debug(True)
    run(host='0.0.0.0', port=8080, server=server)


if __name__ == "__main__":
    main()
