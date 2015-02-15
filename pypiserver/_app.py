import sys, os, itertools, zipfile, mimetypes, logging

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


class configuration(object):
    def __init__(self):
        self.welcome_template = None
        self.fallback_url = "http://pypi.python.org/simple"
        self.redirect_to_fallback = True
        self.htpasswdfile = None
        self.no_auth = None

config = configuration()


def validate_user(username, password):
    if config.htpasswdfile is not None:
        config.htpasswdfile.load_if_changed()
        return config.htpasswdfile.check_password(username, password)


def configure(root=None,
              redirect_to_fallback=True,
              fallback_url=None,
              password_file=None,
              overwrite=False,
              log_req_frmt=None, 
              log_res_frmt=None,
              log_err_frmt=None,
              cache_control=None,
              no_auth=None,
              welcome_template=None
):
    global packages

    log.info("Starting(%s)", dict(root=root,
              redirect_to_fallback=redirect_to_fallback,
              fallback_url=fallback_url,
              password_file=password_file,
              overwrite=overwrite,
              log_req_frmt=log_req_frmt, 
              log_res_frmt=log_res_frmt,
              log_err_frmt=log_err_frmt,
              cache_control=cache_control,
              no_auth=no_auth,
              welcome_template=welcome_template))

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
    config.cache_control = cache_control
    config.no_auth = no_auth
    config.welcome_template = welcome_template
    if password_file:
        from passlib.apache import HtpasswdFile
        config.htpasswdfile = HtpasswdFile(password_file)
    config.overwrite = overwrite

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

    return config.welcome_template % dict(URL=request.url, VERSION=__version__, NUMPKGS=numpkgs,
           PACKAGES=urljoin(fp, "packages/"),
           SIMPLE=urljoin(fp, "simple/"))


@app.post('/')
def update():
    if not request.auth or request.auth[1] is None:
        raise HTTPError(401, header={"WWW-Authenticate": 'Basic realm="pypi"'})

    if not config.no_auth and not validate_user(*request.auth):
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
