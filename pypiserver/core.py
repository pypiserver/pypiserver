#! /usr/bin/env python
"""minimal PyPI like server for use with pip/easy_install"""

import os, sys, getopt, re, mimetypes
try:
    # get rid of "UserWarning: Module bottle was already imported from..."
    import pkg_resources
except ImportError:
    pass

from pypiserver import bottle, __version__
sys.modules["bottle"] = bottle

from bottle import route, run, static_file, redirect, request, debug, server_names, HTTPError
mimetypes.add_type("application/octet-stream", ".egg")

packages = None


class configuration(object):
    def __init__(self):
        self.fallback_url = "http://pypi.python.org/simple"
        self.redirect_to_fallback = True

config = configuration()


def guess_pkgname(path):
    pkgname = re.split(r"-\d+\.", os.path.basename(path))[0]
    return pkgname


def is_allowed_path(path_part):
    p = path_part.replace("\\", "/")
    return not (p.startswith(".") or "/." in p)


class pkgset(object):
    def __init__(self, root):
        self.root = root

    def listdir(self):
        res = []
        for dirpath, dirnames, filenames in os.walk(self.root):
            dirnames[:] = [x for x in dirnames if is_allowed_path(x)]
            for x in filenames:
                if is_allowed_path(x):
                    res.append(os.path.join(self.root, dirpath, x))
        return res

    def find_packages(self, prefix=""):
        prefix = prefix.lower()
        files = []
        for x in self.listdir():
            pkgname = guess_pkgname(x)
            if prefix and pkgname.lower() != prefix:
                continue
            if os.path.isfile(x):
                files.append(x[len(self.root) + 1:])
        return files

    def find_prefixes(self):
        prefixes = set()
        for x in self.listdir():
            if not os.path.isfile(x):
                continue

            pkgname = guess_pkgname(x)
            if pkgname:
                prefixes.add(pkgname)
        return prefixes


@route("/favicon.ico")
def favicon():
    return HTTPError(404)


@route('/')
def root():
    try:
        numpkgs = len(packages.find_packages())
    except:
        numpkgs = 0

    return """<html><head><title>Welcome to pypiserver!</title></head><body>
<h1>Welcome to pypiserver!</h1>
<p>This is a PyPI compatible package index serving %(NUMPKGS)s packages.</p>

<p> To use this server with pip, run the the following command:
<blockquote><pre>
pip install -i %(URL)ssimple PACKAGE [PACKAGE2...]
</pre></blockquote></p>

<p> To use this server with easy_install, run the the following command:
<blockquote><pre>
easy_install -i %(URL)ssimple PACKAGE
</pre></blockquote></p>

<p>The complete list of all packages can be found <a href="/packages/">here</a> or via the <a href="/simple/">/simple</a> index.</p>

<p>This instance is running version %(VERSION)s of the <a href="http://pypi.python.org/pypi/pypiserver">pypiserver</a> software.</p>
</body></html>
""" % dict(URL=request.url, VERSION=__version__, NUMPKGS=numpkgs)


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
def simple_redirect(prefix):
    return redirect("/simple/%s/" % prefix)


@route("/simple/:prefix/")
def simple(prefix=""):
    files = packages.find_packages(prefix)
    if not files:
        if config.redirect_to_fallback:
            return redirect("%s/%s/" % (config.fallback_url.rstrip("/"), prefix))
        return HTTPError(404)
    files.sort()
    res = ["<html><head><title>Links for %s</title></head><body>\n" % prefix]
    res.append("<h1>Links for %s</h1>\n" % prefix)
    for x in files:
        res.append('<a href="/packages/%s">%s</a><br>\n' % (x, os.path.basename(x)))
    res.append("</body></html>\n")
    return "".join(res)


@route('/packages')
@route('/packages/')
def list_packages():
    files = packages.find_packages()
    files.sort()
    res = ["<html><head><title>Index of packages</title></head><body>\n"]
    for x in files:
        res.append('<a href="%s">%s</a><br>\n' % (x, x))
    res.append("</body></html>\n")
    return "".join(res)


@route('/packages/:filename#.*#')
def server_static(filename):
    if not is_allowed_path(filename):
        return HTTPError(404)

    return static_file(filename, root=packages.root)


@route('/:prefix')
@route('/:prefix/')
def bad_url(prefix):
    return redirect("/simple/%s/" % prefix)


def usage():
    print """pypi-server [OPTIONS] [PACKAGES_DIRECTORY]
  start PyPI compatible package server serving packages from
  PACKAGES_DIRECTORY. If PACKAGES_DIRECTORY is not given on the
  command line, it uses the default ~/packages.  pypiserver scans this
  directory recursively for packages. It skips packages and
  directories starting with a dot.

pypi-server understands the following options:

  -p PORT, --port PORT
    listen on port PORT (default: 8080)

  -i INTERFACE, --interface INTERFACE
    listen on interface INTERFACE (default: 0.0.0.0, any interface)

  --disable-fallback
    disable redirect to real PyPI index for packages not found in the
    local index

  --server METHOD
    use METHOD to run the server. Valid values include paste,
    cherrypy, twisted, gunicorn, gevent, wsgiref, auto. The
    default is to use "auto" which chooses one of paste, cherrypy,
    twisted or wsgiref.

  -r PACKAGES_DIRECTORY, --root PACKAGES_DIRECTORY
    [deprecated] serve packages from PACKAGES_DIRECTORY

pypi-server -h
pypi-server --help
  show this help message

pypi-server --version
  show pypi-server's version

Visit http://pypi.python.org/pypi/pypiserver for more information.
"""


def main(argv=None):
    if argv is None:
        argv = sys.argv

    global packages

    host = "0.0.0.0"
    port = 8080
    server = None

    try:
        opts, roots = getopt.getopt(argv[1:], "i:p:r:h", ["interface=", "port=", "root=", "server=", "disable-fallback", "version", "help"])
    except getopt.GetoptError, err:
        sys.exit("usage error: %s" % (err,))

    for k, v in opts:
        if k in ("-p", "--port"):
            port = int(v)
        elif k in ("-i", "--interface"):
            host = v
        elif k in ("-r", "--root"):
            roots.append(v)
        elif k == "--disable-fallback":
            config.redirect_to_fallback = False
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

    if len(roots) == 0:
        roots.append(os.path.expanduser("~/packages"))
    elif len(roots) > 1:
        sys.exit("Error: more than one root directory specified: %r" % (roots,))

    root = os.path.abspath(roots[0])

    try:
        os.listdir(root)
    except Exception, err:
        sys.exit("Error: while trying to list %r: %s" % (root, err))

    packages = pkgset(root)
    server = server or "auto"
    debug(True)
    print "This is pypiserver %s serving %r on %s:%s" % (__version__, root, host, port)
    print
    run(host=host, port=port, server=server)


if __name__ == "__main__":
    main(sys.argv)
