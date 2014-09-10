import sys
import os
import io
import itertools
import zipfile
import mimetypes
import logging
import pkg_resources

try:
    from io import BytesIO
except ImportError:
    from StringIO import StringIO as BytesIO

if sys.version_info >= (3, 0):
    from urllib.parse import urljoin
else:
    from urlparse import urljoin

from bottle import static_file, redirect, request, response, HTTPError, Bottle
from pypiserver import __version__
from pypiserver.core import listdir, find_packages, store, get_prefixes, exists

log = logging.getLogger('pypiserver.http')
packages = None


class Configuration(object):
    def __init__(self):
        self.fallback_url = "http://pypi.python.org/simple"
        self.redirect_to_fallback = True
        self.htpasswdfile = None
        self.welcome_file = None
        self.welcome_msg = None

config = Configuration()


def validate_user(username, password):
    if config.htpasswdfile is not None:
        config.htpasswdfile.load_if_changed()
        return config.htpasswdfile.check_password(username, password)


class auth(object):
    "decorator to apply authentication if specified for the decorated method & action"

    def __init__(self, action):
        self.action = action

    def __call__(self, method):

        def protector(*args, **kwargs):
            if self.action in config.authenticated:
                if not request.auth or request.auth[1] is None:
                    raise HTTPError(401, header={"WWW-Authenticate": 'Basic realm="pypi"'})
                if not validate_user(*request.auth):
                    raise HTTPError(403)
            return method(*args, **kwargs)

        return protector


def configure(root=None,
              redirect_to_fallback=True,
              fallback_url=None,
              authenticated=[],
              password_file=None,
              overwrite=False,
              log_req_frmt=None, 
              log_res_frmt=None,
              log_err_frmt=None,
              welcome_file=None,
              cache_control=None,
             ):
    global packages

    log.info("Starting(%s)", dict(root=root,
              redirect_to_fallback=redirect_to_fallback,
              fallback_url=fallback_url,
              authenticated=authenticated,
              password_file=password_file,
              overwrite=overwrite,
              welcome_file=welcome_file,
              log_req_frmt=log_req_frmt, 
              log_res_frmt=log_res_frmt,
              log_err_frmt=log_err_frmt,
              cache_control=cache_control))

    config.authenticated = authenticated

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
        except OSError:
            err = sys.exc_info()[1]
            sys.exit("Error: while trying to list %r: %s" % (r, err))

    packages = lambda: itertools.chain(*[listdir(r) for r in roots])
    packages.root = roots[0]

    config.redirect_to_fallback = redirect_to_fallback
    config.fallback_url = fallback_url
    config.cache_control = cache_control
    if password_file:
        from passlib.apache import HtpasswdFile
        config.htpasswdfile = HtpasswdFile(password_file)
    config.overwrite = overwrite
    
    ## Read welcome-msg from external file,
    #     or failback to the embedded-msg (ie. in standalone mode).
    #
    try:
        if not welcome_file:
            welcome_file = pkg_resources.resource_filename(__name__, "welcome.html")  # @UndefinedVariable
        config.welcome_file = welcome_file
        with io.open(config.welcome_file, 'r', encoding='utf-8') as fd:
            config.welcome_msg = fd.read()
    except Exception:
        log.warning("Could not load welcome-file(%s)!", welcome_file, exc_info=1)
    if not config.welcome_msg:
        from textwrap import dedent
        config.welcome_msg = dedent("""\
            <html><head><title>Welcome to pypiserver!</title></head><body>
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
            </body></html>\
        """)

    config.log_req_frmt = log_req_frmt
    config.log_res_frmt = log_res_frmt
    config.log_err_frmt = log_err_frmt

app = Bottle()


@app.hook('before_request')
def log_request():
    log.info(config.log_req_frmt, request.environ)


@app.hook('after_request')
def log_response():
    log.info(config.log_res_frmt, #vars(response))  ## DOES NOT WORK!
            dict(
                response=response, 
                status=response.status, headers=response.headers, 
                body=response.body, cookies=response.COOKIES,
    ))


@app.error
def log_error(http_error):
    log.info(config.log_err_frmt, vars(http_error))


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

    return config.welcome_msg % dict(
           URL=request.url, 
           VERSION=__version__, 
           NUMPKGS=numpkgs,
           PACKAGES=urljoin(fp, "packages/"),
           SIMPLE=urljoin(fp, "simple/")
    )


@app.post('/')
@auth("update")
def update():
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
            zf.getinfo('index.html')
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
@auth("list")
def simpleindex_redirect():
    return redirect(request.fullpath + "/")


@app.route("/simple/")
@auth("list")
def simpleindex():
    res = ["<html><head><title>Simple Index</title></head><body>\n"]
    for x in sorted(get_prefixes(packages())):
        res.append('<a href="%s/">%s</a><br>\n' % (x, x))
    res.append("</body></html>")
    return "".join(res)


@app.route("/simple/:prefix")
@app.route("/simple/:prefix/")
@auth("list")
def simple(prefix=""):
    fp = request.fullpath
    if not fp.endswith("/"):
        fp += "/"

    files = [x.relfn for x in sorted(find_packages(packages(), prefix=prefix), key=lambda x: x.parsed_version)]

    if not files:
        if config.redirect_to_fallback:
            return redirect("%s/%s/" % (config.fallback_url.rstrip("/"), prefix))
        return HTTPError(404)
    res = ["<html><head><title>Links for %s</title></head><body>\n" % prefix,
           "<h1>Links for %s</h1>\n" % prefix]
    for x in files:
        abspath = urljoin(fp, "../../packages/%s" % x.replace("\\", "/"))

        res.append('<a href="%s">%s</a><br>\n' % (abspath, os.path.basename(x)))
    res.append("</body></html>\n")
    return "".join(res)


@app.route('/packages')
@app.route('/packages/')
@auth("list")
def list_packages():
    fp = request.fullpath
    if not fp.endswith("/"):
        fp += "/"

    files = [x.relfn for x in sorted(find_packages(packages()),
                                     key=lambda x: (os.path.dirname(x.relfn), x.pkgname, x.parsed_version))]

    res = ["<html><head><title>Index of packages</title></head><body>\n"]
    for x in files:
        x = x.replace("\\", "/")
        res.append('<a href="%s">%s</a><br>\n' % (urljoin(fp, x), x))
    res.append("</body></html>\n")
    return "".join(res)


@app.route('/packages/:filename#.*#')
@auth("download")
def server_static(filename):
    entries = find_packages(packages())
    for x in entries:
        f = x.relfn.replace("\\", "/")
        if f == filename:
            response = static_file(filename, root=x.root, mimetype=mimetypes.guess_type(filename)[0])
            if config.cache_control:
                response.set_header("Cache-Control", "public, max-age=%s" % config.cache_control)
            return response

    return HTTPError(404)


@app.route('/:prefix')
@app.route('/:prefix/')
def bad_url(prefix):
    p = request.fullpath
    if p.endswith("/"):
        p = p[:-1]
    p = p.rsplit('/', 1)[0]
    p += "/simple/%s/" % prefix

    return redirect(p)
