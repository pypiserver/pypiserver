"""Define endpoints for the server application."""


import logging
import mimetypes
import os
import re
import xml.dom.minidom
import zipfile
from collections import namedtuple
from warnings import warn

try:
    from io import BytesIO
except ImportError:
    from StringIO import StringIO as BytesIO

try:  # PY3
    from urllib.parse import urljoin
except ImportError:  # PY2
    from urlparse import urljoin

try:
    import xmlrpc.client as xmlrpclib  # py3
except ImportError:
    import xmlrpclib  # py2


from . import core
from ._version import __version__
from .plugins.authenticators.interface import convert_legacy


from .bottle import (
    redirect,
    request,
    response,
    static_file,
    template,
    Bottle,
    HTTPError
)


log = logging.getLogger(__name__)

_bottle_upload_filename_re = re.compile(r'^[a-z0-9_.!+-]+$', re.I)
Upload = namedtuple('Upload', 'pkg sig')


def app(config=None, auther=None, **kwargs):
    """Return a hydrated app using the provided config and ``auther``.

    :param argparse.Namespace config: a hydrated config namespace
    :param callable auther: a callable authenticator
    :param dict kwargs: DEPRECATED. Config keyword arguments.
    """
    config, packages = core.configure(config)

    if auther is not None:
        warn(DeprecationWarning(
            'Passing an authentication callable to app() is deprecated. '
            'Please create and use an authenticator plugin instead.'
        ))
        config.auther = convert_legacy(auther)
    elif callable(getattr(config, 'auther', None)):
        warn(DeprecationWarning(
            'Passing an authentication callable manually via the config '
            'is deprecated. Please create and use an authenticator plugin '
            'instead.'
        ))
        config.auther = convert_legacy(config.auther)
    else:
        config.auther = config.plugins['authenticators'][config.auth_backend](
            config
        )

    if kwargs:
        warn(DeprecationWarning(
            'Passing arbitrary keyword arguments to app() has been '
            'deprecated. Please use config.Config to generate '
            'a config and pass it to this function.'
        ))
        for key, value in kwargs:
            if key in config:
                setattr(config, key, value)

    return create_app(config, packages)


def is_valid_pkg_filename(fname):
    """See https://github.com/pypiserver/pypiserver/issues/102."""
    return _bottle_upload_filename_re.match(fname) is not None


def doc_upload():
    try:
        content = request.files['content']  # pylint: disable=E1136
    except KeyError:
        raise HTTPError(400, "Missing 'content' file-field!")
    zip_data = content.file.read()
    try:
        zf = zipfile.ZipFile(BytesIO(zip_data))
        zf.getinfo('index.html')
    except Exception:
        raise HTTPError(400, "not a zip file")


def create_app(config, packages):
    """Create a bottle application serving pypiserver."""
    app = Bottle()
    app.config = config
    app.packages = packages

    class auth(object):
        """Apply authentication for the decorated method & action."""

        def __init__(self, action):
            self.action = action

        def __call__(self, method):

            def protector(*args, **kwargs):
                # if self.action in config.authenticated:
                if self.action in config.authenticate:
                    if not request.auth or request.auth[1] is None:
                        raise HTTPError(
                            401,
                            headers={"WWW-Authenticate": 'Basic realm="pypi"'}
                        )
                    if not config.auther.authenticate(request):
                        raise HTTPError(403)
                return method(*args, **kwargs)

            return protector

    def remove_pkg():
        name = request.forms.get("name")  # pylint: disable=E1101
        version = request.forms.get("version")  # pylint: disable=E1101
        if not name or not version:
            msg = "Missing 'name'/'version' fields: name=%s, version=%s"
            raise HTTPError(400, msg % (name, version))
        found = None
        for pkg in core.find_packages(packages()):
            if pkg.pkgname == name and pkg.version == version:
                found = pkg
                break
        if found is None:
            raise HTTPError(404, "%s (%s) not found" % (name, version))
        os.unlink(found.fn)

    def file_upload():
        ufiles = Upload._make(
            request.files.get(f, None) for f in ('content', 'gpg_signature')  # noqa pylint: disable=E1101
        )
        if not ufiles.pkg:
            raise HTTPError(400, "Missing 'content' file-field!")
        if (ufiles.sig and
                '%s.asc' % ufiles.pkg.raw_filename != ufiles.sig.raw_filename):
            raise HTTPError(400, "Unrelated signature %r for package %r!",
                            ufiles.sig, ufiles.pkg)

        for uf in ufiles:
            if not uf:
                continue
            if (not is_valid_pkg_filename(uf.raw_filename) or
                    core.guess_pkgname_and_version(uf.raw_filename) is None):
                raise HTTPError(400, "Bad filename: %s" % uf.raw_filename)

            if (not config.overwrite
                    and core.exists(packages.root, uf.raw_filename)):
                log.warn(
                    "Cannot upload %r since it already exists! \n"
                    "  You may start server with `--overwrite` option. ",
                    uf.raw_filename
                )
                raise HTTPError(
                    409, "Package %r already exists!\n"
                    "  You may start server with `--overwrite` option.",
                    uf.raw_filename
                )

            core.store(packages.root, uf.raw_filename, uf.save)
            if request.auth:
                user = request.auth[0]
            else:
                user = 'anon'
            log.info('User %r stored %r.', user, uf.raw_filename)

    @app.hook('before_request')
    def log_request():
        log.info(config.log_req_frmt, request.environ)

    @app.hook('after_request')
    def log_response():
        log.info(config.log_res_frmt, {  # vars(response))  ## DOES NOT WORK!
            'response': response,
            'status': response.status, 'headers': response.headers,
            'body': response.body, 'cookies': response._cookies,
        })

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
        except Exception:
            numpkgs = 0

        # Ensure template() does not consider `msg` as filename!
        msg = config.welcome_msg + '\n'
        return template(
            msg,
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
            action = request.forms[':action']  # noqa pylint: disable=unsubscriptable-object
        except KeyError:
            raise HTTPError(400, "Missing ':action' field!")

        if action in ("verify", "submit"):
            log.warning("Ignored ':action': %s", action)
        elif action == "doc_upload":
            doc_upload()
        elif action == "remove_pkg":
            remove_pkg()
        elif action == "file_upload":
            file_upload()
        else:
            raise HTTPError(400, "Unsupported ':action' field: %s" % action)

        return ""

    @app.route("/simple")
    @app.route("/simple/:prefix")
    @app.route('/packages')
    @auth("list")
    def pep_503_redirects(prefix=None):
        return redirect(request.fullpath + "/", 301)

    @app.post('/RPC2')
    @auth("list")
    def handle_rpc():
        """Handle pip-style RPC2 search requests"""
        parser = xml.dom.minidom.parse(request.body)
        methodname = parser.getElementsByTagName(
            "methodName")[0].childNodes[0].wholeText.strip()
        log.info("Processing RPC2 request for '%s'", methodname)
        if methodname == 'search':
            value = parser.getElementsByTagName(
                "string")[0].childNodes[0].wholeText.strip()
            response = []
            ordering = 0
            for p in packages():
                if p.pkgname.count(value) > 0:
                    # We do not presently have any description/summary,
                    # returning version instead
                    response.append({
                        '_pypi_ordering': ordering,
                        'version': p.version,
                        'name': p.pkgname,
                        'summary': p.version
                    })
                ordering += 1
            call_string = xmlrpclib.dumps(
                (response,),
                'search',
                methodresponse=True
            )
            return call_string

    @app.route("/simple/")
    @auth("list")
    def simpleindex():
        links = sorted(core.get_prefixes(packages()))
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
        normalized = core.normalize_pkgname(prefix)
        if prefix != normalized:
            return redirect('/simple/{0}/'.format(normalized), 301)

        files = sorted(
            core.find_packages(packages(), prefix=prefix),
            key=lambda x: (x.parsed_version, x.relfn)
        )
        if not files:
            if config.redirect_to_fallback:
                return redirect(
                    "%s/%s/" % (config.fallback_url.rstrip("/"), prefix)
                )
            return HTTPError(
                404,
                'Not Found (%s does not exist)\n\n' % normalized
            )

        fp = request.fullpath
        links = [
            (
                os.path.basename(f.relfn),
                urljoin(
                    fp,
                    "../../packages/%s" % f.fname_and_hash(config.hash_algo)
                )
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

    @app.route('/packages/')
    @auth("list")
    def list_packages():
        fp = request.fullpath
        files = sorted(
            core.find_packages(packages()),
            key=lambda x: (
                os.path.dirname(x.relfn),
                x.pkgname,
                x.parsed_version
            )
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

    @app.route('/packages/:filename#.*#')
    @auth("download")
    def server_static(filename):
        entries = core.find_packages(packages())
        for x in entries:
            f = x.relfn_unix
            if f == filename:
                response = static_file(
                    filename,
                    root=x.root,
                    mimetype=mimetypes.guess_type(filename)[0]
                )
                if config.cache_control:
                    response.set_header(
                        "Cache-Control",
                        "public, max-age=%s" % config.cache_control
                    )
                return response

        return HTTPError(404, 'Not Found (%s does not exist)\n\n' % filename)

    @app.route('/:prefix')
    @app.route('/:prefix/')
    def bad_url(prefix):
        p = request.fullpath
        if p.endswith("/"):
            p = p[:-1]
        p = p.rsplit('/', 1)[0]
        p += "/simple/%s/" % prefix

        return redirect(p)

    return app
