from collections import namedtuple
from io import BytesIO
from urllib.parse import urljoin, urlparse
import functools
import logging
import mimetypes
import os
import re
import xml.dom.minidom
import xmlrpc.client as xmlrpclib  # py3
import zipfile

from pypiserver.config import RunConfig
from pypiserver import __version__, core
from pypiserver.bottle import (
    static_file,
    redirect,
    request,
    response,
    HTTPError,
    HTTPResponse,
    Bottle,
    template,
)


log = logging.getLogger(__name__)

Upload = namedtuple("Upload", "pkg sig")

_bottle_upload_filename_re = re.compile(r"^[a-z0-9_.!+-]+$", re.I)


class PypiserverApp:
    """A wrapper around the Pypiserver application."""

    def __init__(self, config: RunConfig, app: Bottle) -> None:
        """Construct a new Pypiserver application."""
        self.app = app
        self.config = config
        self.auth = functools.partial(auth, config)
        self._initialize_app()
        # Add a reference to our config onto the bottle instance,
        # so anyone using the app() constructor can get it if needed
        self.app._pypiserver_config = config

    def _initialize_app(self) -> None:
        """Initialize the app, adding routes, hooks, etc.."""
        # Hooks
        self.app.hook("before_request")(self.log_request)
        self.app.hook("before_request")(self.parse_request_path)
        self.app.hook("after_request")(self.log_response)
        self.app.error(self.log_error)

        # Routes
        self.app.route("/")(self.root)
        self.app.post("/")(self.auth("update")(self.update))

        self.app.route("/favicon.ico")(self.favicon)

        self.app.route("/packages/")(self.auth("list")(self.list_packages))
        self.app.route("/packages/:filename#.*#")(
            self.auth("download")(self.server_static)
        )

        self.app.post("/RPC2")(self.auth("list")(self.handle_rpc))

        self.app.route("/simple/")(self.auth("list")(self.simpleindex))
        self.app.route("/simple/:prefix/")(self.auth("list")(self.simple))

        # - handle pep 503 redirects
        redirect_route = self.auth("list")(self.pep_503_redirects)
        self.app.route("/simple")(redirect_route)
        self.app.route("/simple/:prefix")(redirect_route)
        self.app.route("/packages")(redirect_route)

        # - handle unknown URLs
        self.app.route("/:prefix")(self.bad_url)
        self.app.route("/:prefix/")(self.bad_url)

    # ************************************************************
    # App Hooks
    # ************************************************************

    def log_request(self) -> None:
        log.info(self.config.log_req_frmt, request.environ)

    @staticmethod
    def parse_request_path() -> None:
        # pylint: disable=no-member
        parsed = urlparse(
            request.urlparts.scheme + "://" + request.urlparts.netloc
        )
        # pylint: enable=no-member
        request.custom_host = parsed.netloc
        request.custom_fullpath = (
            parsed.path.rstrip("/") + "/" + request.fullpath.lstrip("/")
        )

    def log_response(self) -> None:
        log.info(
            self.config.log_res_frmt,
            {  # vars(response))  ## DOES NOT WORK!
                "response": response,
                "status": response.status,
                "headers": response.headers,
                "body": response.body,
                "cookies": response._cookies,
            },
        )

    def log_error(self, http_error: HTTPError) -> None:
        log.info(self.config.log_err_frmt, vars(http_error))

    # ************************************************************
    # App Routes
    # ************************************************************

    @staticmethod
    def favicon() -> HTTPError:
        return HTTPError(404)

    def root(self) -> None:
        fp = request.custom_fullpath

        try:
            numpkgs = len(list(self.config.iter_packages()))
        except Exception as exc:  # pylint: disable=broad-except
            log.error(f"Could not list packages: {exc}")
            numpkgs = 0

        # Ensure template() does not consider `msg` as filename!
        msg = self.config.welcome_msg + "\n"
        return template(
            msg,
            URL=request.url.rstrip("/") + "/",
            VERSION=__version__,
            NUMPKGS=numpkgs,
            PACKAGES=fp.rstrip("/") + "/packages/",
            SIMPLE=fp.rstrip("/") + "/simple/",
        )

    def update(self) -> str:
        try:
            action = request.forms[":action"]
        except KeyError:
            raise HTTPError(400, "Missing ':action' field!")

        if action in ("verify", "submit"):
            log.warning(f"Ignored ':action': {action}")
        elif action == "doc_upload":
            self.doc_upload()
        elif action == "remove_pkg":
            self.remove_pkg()
        elif action == "file_upload":
            self.file_upload()
        else:
            raise HTTPError(400, f"Unsupported ':action' field: {action}")

        return ""

    @staticmethod
    def pep_503_redirects(prefix: str = None) -> tuple:
        return redirect(request.custom_fullpath + "/", 301)

    def handle_rpc(self) -> str:
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
            for p in self.config.iter_packages():
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
        return ""

    def simpleindex(self) -> str:
        links = sorted(core.get_prefixes(self.config.iter_packages()))
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

    def simple(self, prefix: str = "") -> str:
        # PEP 503: require normalized prefix
        normalized = core.normalize_pkgname_for_url(prefix)
        if prefix != normalized:
            return redirect("/simple/{0}/".format(normalized), 301)

        files = sorted(
            core.find_packages(self.config.iter_packages(), prefix=prefix),
            key=lambda x: (x.parsed_version, x.relfn),
        )
        if not files:
            if not self.config.disable_fallback:
                return redirect(
                    f"{self.config.fallback_url.rstrip('/')}/{prefix}/"
                )
            return HTTPError(
                404, f"Not Found ({normalized} does not exist)\n\n"
            )

        fp = request.custom_fullpath
        links = [
            (
                os.path.basename(f.relfn),
                urljoin(
                    fp,
                    f"../../packages/{f.fname_and_hash(self.config.hash_algo)}",
                ),
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

    def list_packages(self) -> str:
        fp = request.custom_fullpath
        files = sorted(
            core.find_packages(self.config.iter_packages()),
            key=lambda x: (
                os.path.dirname(x.relfn),
                x.pkgname,
                x.parsed_version,
            ),
        )
        links = [
            (f.relfn_unix, urljoin(fp, f.fname_and_hash(self.config.hash_algo)))
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

    def server_static(self, filename: str) -> HTTPResponse:
        entries = core.find_packages(self.config.iter_packages())
        for x in entries:
            f = x.relfn_unix
            if f == filename:
                response = static_file(
                    filename,
                    root=x.root,
                    mimetype=mimetypes.guess_type(filename)[0],
                )
                if self.config.cache_control:
                    response.set_header(
                        "Cache-Control",
                        f"public, max-age={self.config.cache_control}",
                    )
                return response

        return HTTPError(404, f"Not Found ({filename} does not exist)\n\n")

    @staticmethod
    def bad_url(prefix: str) -> tuple:
        """Redirect unknown root URLs to /simple/."""
        return redirect(core.get_bad_url_redirect_path(request, prefix))

    # ************************************************************
    # Utility Methods
    # ************************************************************

    @staticmethod
    def is_valid_pkg_filename(fname: str) -> bool:
        """See https://github.com/pypiserver/pypiserver/issues/102"""
        return _bottle_upload_filename_re.match(fname) is not None

    @staticmethod
    def doc_upload() -> None:
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

    def remove_pkg(self) -> None:
        name = request.forms.get("name")
        version = request.forms.get("version")
        if not name or not version:
            msg = f"Missing 'name'/'version' fields: name={name}, version={version}"
            raise HTTPError(400, msg)
        pkgs = list(
            filter(
                lambda pkg: pkg.pkgname == name and pkg.version == version,
                core.find_packages(self.config.iter_packages()),
            )
        )
        if len(pkgs) == 0:
            raise HTTPError(404, f"{name} ({version}) not found")
        for pkg in pkgs:
            os.unlink(pkg.fn)

    def file_upload(self) -> None:
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
                not self.is_valid_pkg_filename(uf.raw_filename)
                or core.guess_pkgname_and_version(uf.raw_filename) is None
            ):
                raise HTTPError(400, f"Bad filename: {uf.raw_filename}")

            if not self.config.overwrite and core.exists(
                self.config.package_root, uf.raw_filename
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

            core.store(self.config.package_root, uf.raw_filename, uf.save)
            if request.auth:
                user = request.auth[0]
            else:
                user = "anon"
            log.info(f"User {user!r} stored {uf.raw_filename!r}.")


class auth:  # pylint: disable=invalid-name
    """decorator to apply authentication if specified for the decorated method & action"""

    def __init__(self, config: RunConfig, action: str) -> None:
        self.config = config
        self.action = action

    def __call__(self, method):
        def protector(*args, **kwargs):
            if self.action in self.config.authenticate:
                if not request.auth or request.auth[1] is None:
                    raise HTTPError(
                        401, headers={"WWW-Authenticate": 'Basic realm="pypi"'}
                    )
                if not self.config.auther(*request.auth):
                    raise HTTPError(403)
            return method(*args, **kwargs)

        return protector
