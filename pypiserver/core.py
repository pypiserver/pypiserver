#! /usr/bin/env python
"""minimal PyPI like server for use with pip/easy_install"""

import os, sys, getopt, mimetypes
try:
    # get rid of "UserWarning: Module bottle was already imported from..."
    import pkg_resources
except ImportError:
    pass

from pypiserver import bottle, __version__
sys.modules["bottle"] = bottle

from bottle import route, run, static_file, redirect, request, debug, server_names
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


def usage():
    print """pypiserver [-p PORT] [-r PACKAGES_DIR]
    start PyPI compatible package server on port PORT serving packages from PACKAGES_DIR
    default is to listen on port 8080 serving packages from directory ~/packages/
"""



def main():
    global packages

    root = os.path.expanduser("~/packages/")
    host = "0.0.0.0"
    port = 8080
    server = None

    try:
        opts, args = getopt.getopt(sys.argv[1:], "p:r:h", ["port=", "root=", "server=", "version", "help"])
    except getopt.GetoptError, err:
        sys.exit("usage error: %s" % (err,))

    for k, v in opts:
        if k in ("-p", "--port"):
            port = int(v)
        elif k in ("-r", "--root"):
            root = os.path.abspath(v)
        elif k == "--server":
            if v not in server_names:
                sys.exit("unknown server %r. choose one of %s" % (v, ", ".join(server_names.keys())))
            server = v
        elif k == "--version":
            print "pypiserver %s" % __version__
            sys.exit(0)
        elif k in ("-h", "--help"):
            usage()
            sys.exit(0)

    try:
        os.listdir(root)
    except Exception, err:
        sys.exit("error occured while trying to list %r: %s" % (root, err))

    packages = pkgset(root)
    server = server or choose_server()
    debug(True)
    print "serving %r on %s:%s" % (root, host, port)
    print
    run(host=host, port=port, server=server)


if __name__ == "__main__":
    main()
