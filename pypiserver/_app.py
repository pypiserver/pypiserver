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

try:  # PY3
    from urllib.parse import urljoin
except ImportError:  # PY2
    from urlparse import urljoin

from .bottle import static_file, redirect, request, response, HTTPError, Bottle, template
from . import __version__
from .core import listdir, find_packages, store, get_prefixes, exists

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
                    raise HTTPError(
                        401, header={"WWW-Authenticate": 'Basic realm="pypi"'})
                if not validate_user(*request.auth):
                    raise HTTPError(403)
            return method(*args, **kwargs)

        return protector


def configure(root=None,
              redirect_to_fallback=True,
              fallback_url=None,
              authenticated=None,
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

    config.authenticated = authenticated or []

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
    if password_file and password_file != '.':
        from passlib.apache import HtpasswdFile
        config.htpasswdfile = HtpasswdFile(password_file)
    config.overwrite = overwrite

    # Read welcome-msg from external file,
    #     or failback to the embedded-msg (ie. in standalone mode).
    #
    try:
        if not welcome_file:
            config.welcome_file = "welcome.html"
            config.welcome_msg = pkg_resources.resource_string(  # @UndefinedVariable
                __name__, "welcome.html").decode("utf-8")  # @UndefinedVariable
        else:
            config.welcome_file = welcome_file
            with io.open(welcome_file, 'r', encoding='utf-8') as fd:
                config.welcome_msg = fd.read()
    except Exception:
        log.warning(
            "Could not load welcome-file(%s)!", welcome_file, exc_info=1)
    config.log_req_frmt = log_req_frmt
    config.log_res_frmt = log_res_frmt
    config.log_err_frmt = log_err_frmt

app = Bottle()


@app.hook('before_request')
def log_request():
    log.info(config.log_req_frmt, request.environ)


@app.hook('after_request')
def log_response():
    log.info(config.log_res_frmt,  # vars(response))  ## DOES NOT WORK!
             dict(
                 response=response,
                 status=response.status, headers=response.headers,
                 body=response.body, cookies=response._cookies,
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

    # Ensure template() does not consider `msg` as filename!
    msg = config.welcome_msg + '\n'
    return template(msg,
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
        log.warn("Cannot upload package(%s) since it already exists! \n" +
                 "  You may use `--overwrite` option when starting server to disable this check. ",
                 content.filename)
        raise HTTPError(409, output="file already exists")

    store(packages.root, content.filename, content.save)
    return ""


@app.route("/simple")
@auth("list")
def simpleindex_redirect():
    return redirect(request.fullpath + "/")


@app.route("/simple/")
@auth("list")
def simpleindex():
    links = sorted(get_prefixes(packages()))
    tmpl = """\
    <html>
        <head>
            <title>Simple Index</title>
        </head>
        <body>
            <h1>Simple Index</h1>
            % for p in links:
                 <a href="{{p}}/">{{p}}</a><br>
        </body>
    </html>
    """
    return template(tmpl, links=links)


@app.route("/simple/:prefix")
@app.route("/simple/:prefix/")
@auth("list")
def simple(prefix=""):
    fp = request.fullpath
    if not fp.endswith("/"):
        fp += "/"

    files = [x.relfn for x in sorted(find_packages(
        packages(), prefix=prefix), key=lambda x: (x.parsed_version, x.relfn))]
    if not files:
        if config.redirect_to_fallback:
            return redirect("%s/%s/" % (config.fallback_url.rstrip("/"), prefix))
        return HTTPError(404)

    links = [(os.path.basename(f), urljoin(fp, "../../packages/%s" %
                                           f.replace("\\", "/"))) for f in files]
    tmpl = """\
    <html>
        <head>
            <title>Links for {{prefix}}</title>
        </head>
        <body>
            <h1>Links for {{prefix}}</h1>
            % for file, href in links:
                 <a href="{{href}}">{{file}}</a><br>
        </body>
    </html>
    """
    return template(tmpl, prefix=prefix, links=links)


@app.route('/packages')
@app.route('/packages/')
@auth("list")
def list_packages():
    fp = request.fullpath
    if not fp.endswith("/"):
        fp += "/"

    files = [x.relfn for x in sorted(find_packages(packages()),
                                     key=lambda x: (os.path.dirname(x.relfn), x.pkgname, x.parsed_version))]
    links = [(f.replace("\\", "/"), urljoin(fp, f)) for f in files]
    tmpl = """\
    <html>
        <head>
            <title>Index of packages</title>
        </head>
        <body>
            <h1>Index of packages</h1>
            % for file, href in links:
                 <a href="{{href}}">{{file}}</a><br>
        </body>
    </html>
    """
    return template(tmpl, links=links)


@app.route('/packages/:filename#.*#')
@auth("download")
def server_static(filename):
    entries = find_packages(packages())
    for x in entries:
        f = x.relfn.replace("\\", "/")
        if f == filename:
            response = static_file(
                filename, root=x.root, mimetype=mimetypes.guess_type(filename)[0])
            if config.cache_control:
                response.set_header(
                    "Cache-Control", "public, max-age=%s" % config.cache_control)
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
