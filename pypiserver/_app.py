from collections import namedtuple
import logging
import mimetypes
import os
import re
import zipfile
import xml.dom.minidom

from pypiserver.config import RunConfig
from . import __version__
from . import core
from .bottle import (
    static_file,
    redirect,
    request,
    response,
    HTTPError,
    Bottle,
    template,
)

try:
    import xmlrpc.client as xmlrpclib  # py3
except ImportError:
    import xmlrpclib  # py2

try:
    from io import BytesIO
except ImportError:
    from StringIO import StringIO as BytesIO

try:  # PY3
    from urllib.parse import urljoin, urlparse
except ImportError:  # PY2
    from urlparse import urljoin, urlparse


log = logging.getLogger(__name__)
config: RunConfig

app = Bottle()


class auth:
    """decorator to apply authentication if specified for the decorated method & action"""

    def __init__(self, action):
        self.action = action

    def __call__(self, method):
        def protector(*args, **kwargs):
            if self.action in config.authenticate:
                if not request.auth or request.auth[1] is None:
                    raise HTTPError(
                        401, headers={"WWW-Authenticate": 'Basic realm="pypi"'}
                    )
                if not config.auther(*request.auth):
                    raise HTTPError(403)
            return method(*args, **kwargs)

        return protector


@app.hook("before_request")
def log_request():
    log.info(config.log_req_frmt, request.environ)


@app.hook("before_request")
def print_request():
    parsed = urlparse(request.urlparts.scheme + "://" + request.urlparts.netloc)
    request.custom_host = parsed.netloc
    request.custom_fullpath = (
        parsed.path.rstrip("/") + "/" + request.fullpath.lstrip("/")
    )


@app.hook("after_request")
def log_response():
    log.info(
        config.log_res_frmt,
        {  # vars(response))  ## DOES NOT WORK!
            "response": response,
            "status": response.status,
            "headers": response.headers,
            "body": response.body,
            "cookies": response._cookies,
        },
    )


@app.error
def log_error(http_error):
    log.info(config.log_err_frmt, vars(http_error))


@app.route("/favicon.ico")
def favicon():
    return HTTPError(404)


@app.route("/")
def root():
    fp = request.custom_fullpath

    try:
        numpkgs = len(list(config.iter_packages()))
    except Exception as exc:
        log.error(f"Could not list packages: {exc}")
        numpkgs = 0

    # Ensure template() does not consider `msg` as filename!
    msg = config.welcome_msg + "\n"
    return template(
        msg,
        URL=request.url.rstrip("/") + "/",
        VERSION=__version__,
        NUMPKGS=numpkgs,
        PACKAGES=fp.rstrip("/") + "/packages/",
        SIMPLE=fp.rstrip("/") + "/simple/",
    )


_bottle_upload_filename_re = re.compile(r"^[a-z0-9_.!+-]+$", re.I)


def is_valid_pkg_filename(fname):
    """See https://github.com/pypiserver/pypiserver/issues/102"""
    return _bottle_upload_filename_re.match(fname) is not None


def doc_upload():
    try:
        content = request.files["content"]
    except KeyError:
        raise HTTPError(400, "Missing 'content' file-field!")
    zip_data = content.file.read()
    try:
        zf = zipfile.ZipFile(BytesIO(zip_data))
        zf.getinfo("index.html")
    except Exception:
        raise HTTPError(400, "not a zip file")


def remove_pkg():
    name = request.forms.get("name")
    version = request.forms.get("version")
    if not name or not version:
        msg = f"Missing 'name'/'version' fields: name={name}, version={version}"
        raise HTTPError(400, msg)
    pkgs = list(
        filter(
            lambda pkg: pkg.pkgname == name and pkg.version == version,
            core.find_packages(config.iter_packages()),
        )
    )
    if len(pkgs) == 0:
        raise HTTPError(404, f"{name} ({version}) not found")
    for pkg in pkgs:
        os.unlink(pkg.fn)


Upload = namedtuple("Upload", "pkg sig")


def file_upload():
    ufiles = Upload._make(
        request.files.get(f, None) for f in ("content", "gpg_signature")
    )
    if not ufiles.pkg:
        raise HTTPError(400, "Missing 'content' file-field!")
    if (
        ufiles.sig
        and f"{ufiles.pkg.raw_filename}.asc" != ufiles.sig.raw_filename
    ):
        raise HTTPError(
            400,
            f"Unrelated signature {ufiles.sig!r} for package {ufiles.pkg!r}!",
        )

    for uf in ufiles:
        if not uf:
            continue
        if (
            not is_valid_pkg_filename(uf.raw_filename)
            or core.guess_pkgname_and_version(uf.raw_filename) is None
        ):
            raise HTTPError(400, f"Bad filename: {uf.raw_filename}")

        if not config.overwrite and core.exists(
            config.package_root, uf.raw_filename
        ):
            log.warning(
                f"Cannot upload {uf.raw_filename!r} since it already exists! \n"
                "  You may start server with `--overwrite` option. "
            )
            raise HTTPError(
                409,
                f"Package {uf.raw_filename!r} already exists!\n"
                "  You may start server with `--overwrite` option.",
            )

        core.store(config.package_root, uf.raw_filename, uf.save)
        if request.auth:
            user = request.auth[0]
        else:
            user = "anon"
        log.info(f"User {user!r} stored {uf.raw_filename!r}.")


@app.post("/")
@auth("update")
def update():
    try:
        action = request.forms[":action"]
    except KeyError:
        raise HTTPError(400, "Missing ':action' field!")

    if action in ("verify", "submit"):
        log.warning(f"Ignored ':action': {action}")
    elif action == "doc_upload":
        doc_upload()
    elif action == "remove_pkg":
        remove_pkg()
    elif action == "file_upload":
        file_upload()
    else:
        raise HTTPError(400, f"Unsupported ':action' field: {action}")

    return ""


@app.route("/simple")
@app.route("/simple/:prefix")
@app.route("/packages")
@auth("list")
def pep_503_redirects(prefix=None):
    return redirect(request.custom_fullpath + "/", 301)


@app.post("/RPC2")
@auth("list")
def handle_rpc():
    """Handle pip-style RPC2 search requests"""
    parser = xml.dom.minidom.parse(request.body)
    methodname = (
        parser.getElementsByTagName("methodName")[0]
        .childNodes[0]
        .wholeText.strip()
    )
    log.info(f"Processing RPC2 request for '{methodname}'")
    if methodname == "search":
        value = (
            parser.getElementsByTagName("string")[0]
            .childNodes[0]
            .wholeText.strip()
        )
        response = []
        ordering = 0
        for p in config.iter_packages():
            if p.pkgname.count(value) > 0:
                # We do not presently have any description/summary, returning
                # version instead
                d = {
                    "_pypi_ordering": ordering,
                    "version": p.version,
                    "name": p.pkgname,
                    "summary": p.version,
                }
                response.append(d)
            ordering += 1
        call_string = xmlrpclib.dumps(
            (response,), "search", methodresponse=True
        )
        return call_string


@app.route("/simple/")
@auth("list")
def simpleindex():
    links = sorted(core.get_prefixes(config.iter_packages()))
    tmpl = """\
    <html>
        <head>
            <title>Simple Index</title>
        </head>
        <body>
            <h1>Simple Index</h1>
            % for p in links:
                 <a href="{{p}}/">{{p}}</a><br>
            % end
        </body>
    </html>
    """
    return template(tmpl, links=links)


@app.route("/simple/:prefix/")
@auth("list")
def simple(prefix=""):
    # PEP 503: require normalized prefix
    normalized = core.normalize_pkgname_for_url(prefix)
    if prefix != normalized:
        return redirect("/simple/{0}/".format(normalized), 301)

    files = sorted(
        core.find_packages(config.iter_packages(), prefix=prefix),
        key=lambda x: (x.parsed_version, x.relfn),
    )
    if not files:
        if not config.disable_fallback:
            return redirect(f"{config.fallback_url.rstrip('/')}/{prefix}/")
        return HTTPError(404, f"Not Found ({normalized} does not exist)\n\n")

    fp = request.custom_fullpath
    links = [
        (
            os.path.basename(f.relfn),
            urljoin(fp, f"../../packages/{f.fname_and_hash(config.hash_algo)}"),
        )
        for f in files
    ]
    tmpl = """\
    <html>
        <head>
            <title>Links for {{prefix}}</title>
        </head>
        <body>
            <h1>Links for {{prefix}}</h1>
            % for file, href in links:
                 <a href="{{href}}">{{file}}</a><br>
            % end
        </body>
    </html>
    """
    return template(tmpl, prefix=prefix, links=links)


@app.route("/packages/")
@auth("list")
def list_packages():
    fp = request.custom_fullpath
    files = sorted(
        core.find_packages(config.iter_packages()),
        key=lambda x: (os.path.dirname(x.relfn), x.pkgname, x.parsed_version),
    )
    links = [
        (f.relfn_unix, urljoin(fp, f.fname_and_hash(config.hash_algo)))
        for f in files
    ]
    tmpl = """\
    <html>
        <head>
            <title>Index of packages</title>
        </head>
        <body>
            <h1>Index of packages</h1>
            % for file, href in links:
                 <a href="{{href}}">{{file}}</a><br>
            % end
        </body>
    </html>
    """
    return template(tmpl, links=links)


@app.route("/packages/:filename#.*#")
@auth("download")
def server_static(filename):
    entries = core.find_packages(config.iter_packages())
    for x in entries:
        f = x.relfn_unix
        if f == filename:
            response = static_file(
                filename,
                root=x.root,
                mimetype=mimetypes.guess_type(filename)[0],
            )
            if config.cache_control:
                response.set_header(
                    "Cache-Control", f"public, max-age={config.cache_control}"
                )
            return response

    return HTTPError(404, f"Not Found ({filename} does not exist)\n\n")


@app.route("/:prefix")
@app.route("/:prefix/")
def bad_url(prefix):
    """Redirect unknown root URLs to /simple/."""
    return redirect(core.get_bad_url_redirect_path(request, prefix))
