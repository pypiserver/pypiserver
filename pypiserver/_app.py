import sys, os, itertools, zipfile, mimetypes

try:
    from io import BytesIO
except ImportError:
    from StringIO import StringIO as BytesIO

if sys.version_info >= (3, 0):
    from urllib.parse import urljoin
else:
    from urlparse import urljoin

from bottle import static_file, redirect, request, HTTPError, Bottle
from pypiserver import __version__
from pypiserver.core import listdir, find_packages, store, get_prefixes, exists

packages = None


class configuration(object):
    def __init__(self):
        self.fallback_url = "http://pypi.python.org/simple"
        self.redirect_to_fallback = True
        self.htpasswdfile = None

config = configuration()


def validate_user(username, password):
    if config.htpasswdfile is not None:
        config.htpasswdfile.load_if_changed()
        return config.htpasswdfile.check_password(username, password)


def configure(root=None,
              redirect_to_fallback=True,
              fallback_url=None,
              password_file=None,
              overwrite=False):
    global packages

    if root is None:
        root = os.path.expanduser("~/packages")

    if fallback_url is None:
        fallback_url = "http://pypi.python.org/simple"

    if not isinstance(root, (list, tuple)):
        roots = [root]
    else:
        roots = root

    roots = [os.path.abspath(r) for r in roots]
    for r in roots:
        try:
            os.listdir(r)
        except Exception:
            err = sys.exc_info()[1]
            sys.exit("Error: while trying to list %r: %s" % (r, err))

    packages = lambda: itertools.chain(*[listdir(r) for r in roots])
    packages.root = roots[0]

    config.redirect_to_fallback = redirect_to_fallback
    config.fallback_url = fallback_url
    if password_file:
        from passlib.apache import HtpasswdFile
        config.htpasswdfile = HtpasswdFile(password_file)
    config.overwrite = overwrite

app = Bottle()


@app.route("/favicon.ico")
def favicon():
    return HTTPError(404)


@app.route('/')
def root():
    fp = request.fullpath

    try:
        numpkgs = len(list(packages()))
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

<p>The complete list of all packages can be found <a href="%(PACKAGES)s">here</a> or via the <a href="%(SIMPLE)s">simple</a> index.</p>

<p>This instance is running version %(VERSION)s of the <a href="http://pypi.python.org/pypi/pypiserver">pypiserver</a> software.</p>
</body></html>
""" % dict(URL=request.url, VERSION=__version__, NUMPKGS=numpkgs,
           PACKAGES=urljoin(fp, "packages/"),
           SIMPLE=urljoin(fp, "simple/"))


@app.post('/')
def update():
    if not request.auth or request.auth[1] is None:
        raise HTTPError(401, header={"WWW-Authenticate": 'Basic realm="pypi"'})

    if not validate_user(*request.auth):
        raise HTTPError(403)

    try:
        action = request.forms[':action']
    except KeyError:
        raise HTTPError(400, output=":action field not found")

    if action in ("verify", "submit"):
        return ""

    if action == "doc_upload":
        try:
            content = request.files['content']
        except KeyError:
            raise HTTPError(400, output="content file field not found")
        zip_data = content.file.read()
        try:
            zf = zipfile.ZipFile(BytesIO(zip_data))
            info = zf.getinfo('index.html')
        except Exception:
            raise HTTPError(400, output="not a zip file")
        return ""

    if action == "remove_pkg":
        name = request.forms.get("name")
        version = request.forms.get("version")
        if not name or not version:
            raise HTTPError(400, "Name or version not specified")
        found = None
        for pkg in find_packages(packages()):
            if pkg.pkgname == name and pkg.version == version:
                found = pkg
                break
        if found is None:
            raise HTTPError(404, "%s (%s) not found" % (name, version))
        os.unlink(found.fn)
        return ""

    if action != "file_upload":
        raise HTTPError(400, output="action not supported: %s" % action)

    try:
        content = request.files['content']
    except KeyError:
        raise HTTPError(400, output="content file field not found")

    if "/" in content.filename:
        raise HTTPError(400, output="bad filename")

    if not config.overwrite and exists(packages.root, content.filename):
        raise HTTPError(409, output="file already exists")

    store(packages.root, content.filename, content.value)
    return ""


@app.route("/simple")
def simpleindex_redirect():
    return redirect(request.fullpath + "/")


@app.route("/simple/")
def simpleindex():
    res = ["<html><head><title>Simple Index</title></head><body>\n"]
    for x in sorted(get_prefixes(packages())):
        res.append('<a href="%s/">%s</a><br>\n' % (x, x))
    res.append("</body></html>")
    return "".join(res)


@app.route("/simple/:prefix")
@app.route("/simple/:prefix/")
def simple(prefix=""):
    fp = request.fullpath
    if not fp.endswith("/"):
        fp += "/"

    files = [x.relfn for x in sorted(find_packages(packages(), prefix=prefix), key=lambda x: x.parsed_version)]

    if not files:
        if config.redirect_to_fallback:
            return redirect("%s/%s/" % (config.fallback_url.rstrip("/"), prefix))
        return HTTPError(404)
    res = ["<html><head><title>Links for %s</title></head><body>\n" % prefix]
    res.append("<h1>Links for %s</h1>\n" % prefix)
    for x in files:
        abspath = urljoin(fp, "../../packages/%s" % x.replace("\\", "/"))

        res.append('<a href="%s">%s</a><br>\n' % (abspath, os.path.basename(x)))
    res.append("</body></html>\n")
    return "".join(res)


@app.route('/packages')
@app.route('/packages/')
def list_packages():
    fp = request.fullpath
    if not fp.endswith("/"):
        fp += "/"

    files = [x.relfn for x in sorted(find_packages(packages()), key=lambda x: (os.path.dirname(x.relfn), x.pkgname, x.parsed_version))]

    res = ["<html><head><title>Index of packages</title></head><body>\n"]
    for x in files:
        x = x.replace("\\", "/")
        res.append('<a href="%s">%s</a><br>\n' % (urljoin(fp, x), x))
    res.append("</body></html>\n")
    return "".join(res)


@app.route('/packages/:filename#.*#')
def server_static(filename):
    entries = find_packages(packages())
    for x in entries:
        f = x.relfn.replace("\\", "/")
        if f == filename:
            return static_file(filename, root=x.root, mimetype=mimetypes.guess_type(filename)[0])

    return HTTPError(404)


@app.route('/:prefix')
@app.route('/:prefix/')
def bad_url(prefix):
    p = request.fullpath
    if not p.endswith("/"):
        p += "/"
    p += "../simple/%s/" % prefix

    return redirect(p)
