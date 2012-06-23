import sys, os

if sys.version_info >= (3, 0):
    from urllib.parse import urljoin
else:
    from urlparse import urljoin

from bottle import static_file, redirect, request, template
from bottle import HTTPError, Bottle, TEMPLATE_PATH
from pypiserver import __version__
from pypiserver.core import is_allowed_path

packages = None
TEMPLATE_PATH.append(os.path.join(os.path.dirname(__file__), 'templates'))

class configuration(object):
    def __init__(self):
        self.fallback_url = "http://pypi.python.org/simple"
        self.redirect_to_fallback = True
        self.htpasswdfile = None

config = configuration()

class PackageObject(object):
    name = ''
    url = ''


def validate_user(username, password):
    if config.htpasswdfile is not None:
        config.htpasswdfile.load_if_changed()
        return config.htpasswdfile.check_password(username, password)


def configure(root=None,
              redirect_to_fallback=True,
              fallback_url=None,
              password_file=None):
    from pypiserver.core import pkgset
    global packages

    if root is None:
        root = os.path.expanduser("~/packages")

    if fallback_url is None:
        fallback_url = "http://pypi.python.org/simple"

    packages = pkgset(root)
    config.redirect_to_fallback = redirect_to_fallback
    config.fallback_url = fallback_url
    if password_file:
        from passlib.apache import HtpasswdFile
        config.htpasswdfile = HtpasswdFile(password_file)

app = Bottle()


@app.route("/favicon.ico")
def favicon():
    return HTTPError(404)


@app.route('/')
def root():
    contents = {}

    try:
        numpkgs = len(packages.find_packages())
    except:
        numpkgs = 0

    contents['URL'] = request.url
    contents['VERSION'] = __version__
    contents['NUMPKGS'] = numpkgs

    return template('index', **contents)


@app.post('/')
def update():
    if not request.auth:
        raise HTTPError(401, header={"WWW-Authenticate": 'Basic realm="pypi"'})

    if not validate_user(*request.auth):
        raise HTTPError(403)

    try:
        action = request.forms[':action']
    except KeyError:
        raise HTTPError(400, output=":action field not found")

    if action == "submit":
        return ""

    if action != "file_upload":
        raise HTTPError(400, output="actions other than file_upload/submit, not supported")

    try:
        content = request.files['content']
    except KeyError:
        raise HTTPError(400, output="content file field not found")

    if "/" in content.filename:
        raise HTTPError(400, output="bad filename")

    packages.store(content.filename, content.value)

    return ""



@app.route("/simple")
def simpleindex_redirect():
    return redirect(request.fullpath + "/")


@app.route("/simple/")
def simpleindex():
    content = {}
    content['packages'] = []

    package_prefixes = packages.find_prefixes()
    for package in package_prefixes:
        p = PackageObject()
        p.name = package
        p.link = package
        content['packages'].append(p)
    return template('packages', **content)


@app.route("/simple/:prefix")
@app.route("/simple/:prefix/")
def simple(prefix=""):
    content = {}
    content['packages'] = []

    fp = request.fullpath
    if not fp.endswith("/"):
        fp += "/"

    files = packages.find_packages(prefix)
    if not files:
        if config.redirect_to_fallback:
            return redirect("%s/%s/" % (config.fallback_url.rstrip("/"), prefix))
        return HTTPError(404)
    files.sort()
    for x in files:
        p = PackageObject()
        p.name = os.path.basename(x)
        p.link = urljoin(fp, "../../packages/%s" % x.replace("\\", "/"))
        content['packages'].append(p)
    return template('packages', **content)


@app.route('/packages')
@app.route('/packages/')
def list_packages():
    content = {}
    content['packages'] = []

    fp = request.fullpath
    if not fp.endswith("/"):
        fp += "/"

    files = packages.find_packages()
    files.sort()
    for x in files:
        x = x.replace("\\", "/")

        p = PackageObject()
        p.name = os.path.basename(x)
        p.link = urljoin(fp, x)
        content['packages'].append(p)
    return template('packages', **content)


@app.route('/packages/:filename#.*#')
def server_static(filename):
    if not is_allowed_path(filename):
        return HTTPError(404)

    return static_file(filename, root=packages.root)


@app.route('/:prefix')
@app.route('/:prefix/')
def bad_url(prefix):
    p = request.fullpath
    if not p.endswith("/"):
        p += "/"
    p += "../simple/%s/" % prefix

    return redirect(p)
