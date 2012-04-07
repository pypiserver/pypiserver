import sys, os

if sys.version_info >= (3, 0):
    from urllib.parse import urljoin
else:
    from urlparse import urljoin

from bottle import route, static_file, redirect, request, HTTPError
from pypiserver import __version__
from pypiserver.core import is_allowed_path
packages = None

class configuration(object):
    def __init__(self):
        self.fallback_url = "http://pypi.python.org/simple"
        self.redirect_to_fallback = True

config = configuration()

def configure(root=None,
              redirect_to_fallback=True,
              fallback_url=None):
    from pypiserver.core import pkgset
    global packages

    if root is None:
        root = os.path.expanduser("~/packages")

    if fallback_url is None:
        fallback_url="http://pypi.python.org/simple"

    packages = pkgset(root)
    config.redirect_to_fallback = redirect_to_fallback
    config.fallback_url = fallback_url


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
pip install -i %(URL)ssimple/ PACKAGE [PACKAGE2...]
</pre></blockquote></p>

<p> To use this server with easy_install, run the the following command:
<blockquote><pre>
easy_install -i %(URL)ssimple/ PACKAGE
</pre></blockquote></p>

<p>The complete list of all packages can be found <a href="packages/">here</a> or via the <a href="simple/">simple</a> index.</p>

<p>This instance is running version %(VERSION)s of the <a href="http://pypi.python.org/pypi/pypiserver">pypiserver</a> software.</p>
</body></html>
""" % dict(URL=request.url, VERSION=__version__, NUMPKGS=numpkgs)


@route("/simple")
def simpleindex_redirect():
    return redirect(request.fullpath + "/")


@route("/simple/")
def simpleindex():
    prefixes = list(packages.find_prefixes())
    prefixes.sort()
    res = ["<html><head><title>Simple Index</title></head><body>\n"]
    for x in prefixes:
        res.append('<a href="%s/">%s</a><br>\n' % (x, x))
    res.append("</body></html>")
    return "".join(res)


@route("/simple/:prefix")
@route("/simple/:prefix/")
def simple(prefix=""):
    fp = request.fullpath
    if not fp.endswith("/"):
        fp += "/"

    files = packages.find_packages(prefix)
    if not files:
        if config.redirect_to_fallback:
            return redirect("%s/%s/" % (config.fallback_url.rstrip("/"), prefix))
        return HTTPError(404)
    files.sort()
    res = ["<html><head><title>Links for %s</title></head><body>\n" % prefix]
    res.append("<h1>Links for %s</h1>\n" % prefix)
    for x in files:
        abspath = urljoin(fp, "../../packages/%s" % x)

        res.append('<a href="%s">%s</a><br>\n' % (abspath, os.path.basename(x)))
    res.append("</body></html>\n")
    return "".join(res)


@route('/packages')
@route('/packages/')
def list_packages():
    fp = request.fullpath
    if not fp.endswith("/"):
        fp += "/"

    files = packages.find_packages()
    files.sort()
    res = ["<html><head><title>Index of packages</title></head><body>\n"]
    for x in files:
        res.append('<a href="%s">%s</a><br>\n' % (urljoin(fp, x), x))
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
    p = request.fullpath
    if not p.endswith("/"):
        p += "/"
    p += "../simple/%s/" % prefix

    return redirect(p)

    # return redirect("../simple/%s/" % prefix)
