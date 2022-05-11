import logging
import mimetypes
import os
import re
import xml.dom.minidom
import xmlrpc.client as xmlrpclib
import zipfile
from collections import namedtuple
from io import BytesIO
from urllib.parse import urljoin, urlparse
from json import dumps

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
from .pkg_helpers import guess_pkgname_and_version, normalize_pkgname_for_url

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


@app.route("/health")
def health():
    return "Ok"


@app.route("/favicon.ico")
def favicon():
    return HTTPError(404)


@app.route("/")
def root():
    fp = request.custom_fullpath

    # Ensure template() does not consider `msg` as filename!
    msg = config.welcome_msg + "\n"
    return template(
        msg,
        URL=request.url.rstrip("/") + "/",
        VERSION=__version__,
        NUMPKGS=config.backend.package_count(),
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

    pkgs = list(config.backend.find_version(name, version))
    if not pkgs:
        raise HTTPError(404, f"{name} ({version}) not found")
    for pkg in pkgs:
        config.backend.remove_package(pkg)


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
            or guess_pkgname_and_version(uf.raw_filename) is None
        ):
            raise HTTPError(400, f"Bad filename: {uf.raw_filename}")

        if not config.overwrite and config.backend.exists(uf.raw_filename):
            log.warning(
                f"Cannot upload {uf.raw_filename!r} since it already exists! \n"
                "  You may start server with `--overwrite` option. "
            )
            raise HTTPError(
                409,
                f"Package {uf.raw_filename!r} already exists!\n"
                "  You may start server with `--overwrite` option.",
            )

        config.backend.add_package(uf.raw_filename, uf.file)
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
@app.route("/simple/:project")
@app.route("/packages")
@auth("list")
def pep_503_redirects(project=None):
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
    log.debug(f"Processing RPC2 request for '{methodname}'")
    if methodname == "search":
        value = (
            parser.getElementsByTagName("string")[0]
            .childNodes[0]
            .wholeText.strip()
        )
        response = []
        ordering = 0
        for p in config.backend.get_all_packages():
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
    links = sorted(config.backend.get_projects())
    tmpl = """\
    <!DOCTYPE html>
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


@app.route("/simple/:project/")
@auth("list")
def simple(project):
    # PEP 503: require normalized project
    normalized = normalize_pkgname_for_url(project)
    if project != normalized:
        return redirect(f"/simple/{normalized}/", 301)

    packages = sorted(
        config.backend.find_project_packages(project),
        key=lambda x: (x.parsed_version, x.relfn),
    )
    if not packages:
        if not config.disable_fallback:
            return redirect(f"{config.fallback_url.rstrip('/')}/{project}/")
        return HTTPError(404, f"Not Found ({normalized} does not exist)\n\n")

    current_uri = request.custom_fullpath

    links = (
        (
            os.path.basename(pkg.relfn),
            urljoin(current_uri, f"../../packages/{pkg.fname_and_hash}"),
        )
        for pkg in packages
    )

    tmpl = """\
    <!DOCTYPE html>
    <html>
        <head>
            <title>Links for {{project}}</title>
        </head>
        <body>
            <h1>Links for {{project}}</h1>
            % for file, href in links:
                 <a href="{{href}}">{{file}}</a><br>
            % end
        </body>
    </html>
    """
    return template(tmpl, project=project, links=links)


@app.route("/packages/")
@auth("list")
def list_packages():
    fp = request.custom_fullpath
    packages = sorted(
        config.backend.get_all_packages(),
        key=lambda x: (os.path.dirname(x.relfn), x.pkgname, x.parsed_version),
    )

    links = (
        (pkg.relfn_unix, urljoin(fp, pkg.fname_and_hash)) for pkg in packages
    )

    tmpl = """\
    <!DOCTYPE html>
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
    entries = config.backend.get_all_packages()
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


@app.route("/:project/json")
@auth("list")
def json_info(project):
    # PEP 503: require normalized project
    normalized = normalize_pkgname_for_url(project)
    if project != normalized:
        return redirect(f"/{normalized}/json", 301)

    packages = sorted(
        config.backend.find_project_packages(project),
        key=lambda x: x.parsed_version,
        reverse=True,
    )

    if not packages:
        raise HTTPError(404, f"package {project} not found")

    latest_version = packages[0].version
    releases = {}
    req_url = request.url
    for x in packages:
        releases[x.version] = [
            {"url": urljoin(req_url, "../../packages/" + x.relfn)}
        ]
    rv = {"info": {"version": latest_version}, "releases": releases}
    response.content_type = "application/json"
    return dumps(rv)


@app.route("/:project")
@app.route("/:project/")
def bad_url(project):
    """Redirect unknown root URLs to /simple/."""
    return redirect(core.get_bad_url_redirect_path(request, project))
