#! /usr/bin/env python
"""minimal PyPI like server for use with pip/easy_install"""

import hashlib
import io
import itertools
import functools
import logging
import mimetypes
import os
import re
import sys

import pkg_resources
from . import Configuration

log = logging.getLogger(__file__)

def configure(root=None,
              redirect_to_fallback=True,
              fallback_url=None,
              authenticated=None,
              password_file=None,
              overwrite=False,
              log_file=None,
              log_frmt=None,
              log_req_frmt=None,
              log_res_frmt=None,
              log_err_frmt=None,
              welcome_file=None,
              cache_control=None,
              auther=None,
              host=None, port=None, server=None, verbosity=None, VERSION=None
              ):
    """
    :param root:
            A list of paths, derived from the packages specified on cmd-line.
    :param redirect_to_fallback:
            see :option:`--disable-fallback`
    :param authenticated:
            see :option:`--authenticate`
    :param password_file:
            see :option:`--passwords`
    :param log_file:
            see :option:`--log-file`
            Not used, passed here for logging it.
    :param log_frmt:
            see :option:`--log-frmt`
            Not used, passed here for logging it.
    :param callable auther:
            An API-only options that if it evaluates to a callable,
            it is invoked to allow access to protected operations
            (instead of htpaswd mechanism) like that::

                auther(username, password): bool

            When defined, `password_file` is ignored.
    :param host:
            see :option:`--interface`
            Not used, passed here for logging it.
    :param port:
            see :option:`--port`
            Not used, passed here for logging it.
    :param server:
            see :option:`--server`
            Not used, passed here for logging it.
    :param verbosity:
            see :option:`-v`
            Not used, passed here for logging it.
    :param VERSION:
            Not used, passed here for logging it.

    :return: a 2-tuple (Configure, package-list)

    """
    log.info("+++Pypiserver invoked with: %s", Configuration(
            root=root,
            redirect_to_fallback=redirect_to_fallback,
            fallback_url=fallback_url,
            authenticated=authenticated,
            password_file=password_file,
            overwrite=overwrite,
            welcome_file=welcome_file,
            log_file=log_file,
            log_frmt=log_frmt,
            log_req_frmt=log_req_frmt,
            log_res_frmt=log_res_frmt,
            log_err_frmt=log_err_frmt,
            cache_control=cache_control,
            auther=auther,
            host=host, port=port, server=server,
            verbosity=verbosity, VERSION=VERSION
    ))


    if root is None:
        root = os.path.expanduser("~/packages")
    roots = root if isinstance(root, (list, tuple)) else [root]
    roots = [os.path.abspath(r) for r in roots]
    for r in roots:
        try:
            os.listdir(r)
        except OSError:
            err = sys.exc_info()[1]
            sys.exit("Error: while trying to list root(%s): %s" % (r, err))

    packages = lambda: itertools.chain(*[listdir(r) for r in roots])
    packages.root = roots[0]

    authenticated = authenticated or []
    if not callable(auther):
        if password_file and password_file != '.':
            from passlib.apache import HtpasswdFile
            htPsswdFile = HtpasswdFile(password_file)
        else:
            password_file = htPsswdFile = None
        auther = functools.partial(auth_by_htpasswd_file, htPsswdFile)

    # Read welcome-msg from external file,
    #     or failback to the embedded-msg (ie. in standalone mode).
    #
    try:
        if not welcome_file:
            welcome_file = "welcome.html"
            welcome_msg = pkg_resources.resource_string(  # @UndefinedVariable
                __name__, "welcome.html").decode("utf-8")  # @UndefinedVariable
        else:
            welcome_file = welcome_file
            with io.open(welcome_file, 'r', encoding='utf-8') as fd:
                welcome_msg = fd.read()
    except Exception:
        log.warning(
            "Could not load welcome-file(%s)!", welcome_file, exc_info=1)

    if fallback_url is None:
        fallback_url = "http://pypi.python.org/simple"

    log_req_frmt = log_req_frmt
    log_res_frmt = log_res_frmt
    log_err_frmt = log_err_frmt

    config = Configuration(
            root=root,
            redirect_to_fallback=redirect_to_fallback,
            fallback_url=fallback_url,
            authenticated=authenticated,
            password_file=password_file,
            overwrite=overwrite,
            welcome_file=welcome_file,
            welcome_msg=welcome_msg,
            log_req_frmt=log_req_frmt,
            log_res_frmt=log_res_frmt,
            log_err_frmt=log_err_frmt,
            cache_control=cache_control,
            auther=auther
    )
    log.info("+++Pypiserver started with: %s", config)

    return config, packages


def auth_by_htpasswd_file(htPsswdFile, username, password):
    """The default ``config.auther``."""
    if htPsswdFile is not None:
        htPsswdFile.load_if_changed()
        return htPsswdFile.check_password(username, password)



mimetypes.add_type("application/octet-stream", ".egg")
mimetypes.add_type("application/octet-stream", ".whl")


# --- the following two functions were copied from distribute's pkg_resources module
component_re = re.compile(r'(\d+ | [a-z]+ | \.| -)', re.VERBOSE)
replace = {'pre': 'c', 'preview': 'c', '-': 'final-', 'rc': 'c', 'dev': '@'}.get


def _parse_version_parts(s):
    for part in component_re.split(s):
        part = replace(part, part)
        if part in ['', '.']:
            continue
        if part[:1] in '0123456789':
            yield part.zfill(8)  # pad for numeric comparison
        else:
            yield '*' + part

    yield '*final'  # ensure that alpha/beta/candidate are before final


def parse_version(s):
    parts = []
    for part in _parse_version_parts(s.lower()):
        if part.startswith('*'):
            # remove trailing zeros from each series of numeric parts
            while parts and parts[-1] == '00000000':
                parts.pop()
        parts.append(part)
    return tuple(parts)

# -- end of distribute's code

_archive_suffix_rx = re.compile(
    r"(\.zip|\.tar\.gz|\.tgz|\.tar\.bz2|-py[23]\.\d-.*|\.win-amd64-py[23]\.\d\..*|\.win32-py[23]\.\d\..*|\.egg)$",
    re.IGNORECASE)

wheel_file_re = re.compile(
    r"""^(?P<namever>(?P<name>.+?)-(?P<ver>\d.*?))
    ((-(?P<build>\d.*?))?-(?P<pyver>.+?)-(?P<abi>.+?)-(?P<plat>.+?)
    \.whl|\.dist-info)$""",
    re.VERBOSE)


def _guess_pkgname_and_version_wheel(basename):
    m = wheel_file_re.match(basename)
    if not m:
        return None, None
    name = m.group("name")
    ver = m.group("ver")
    build = m.group("build")
    if build:
        return name, ver + "-" + build
    else:
        return name, ver


def guess_pkgname_and_version(path):
    path = os.path.basename(path)
    if path.endswith(".whl"):
        return _guess_pkgname_and_version_wheel(path)
    if not _archive_suffix_rx.search(path):
        return
    path = _archive_suffix_rx.sub('', path)
    if '-' not in path:
        pkgname, version = path, ''
    elif path.count('-') == 1:
        pkgname, version = path.split('-', 1)
    elif '.' not in path:
        pkgname, version = path.rsplit('-', 1)
    else:
        pkgname = re.split(r'-(?i)v?\d+[\.a-z]', path)[0]
        ver_spec = path[len(pkgname) + 1:]
        parts = re.split(r'[\.\-](?=(?i)cp\d|py\d|macosx|linux|sunos|'
                         'solaris|irix|aix|cygwin|win)', ver_spec)
        version = parts[0]
    return pkgname, version


def normalize_pkgname(name):
    return name.lower().replace("-", "_")


def is_allowed_path(path_part):
    p = path_part.replace("\\", "/")
    return not (p.startswith(".") or "/." in p)


class PkgFile(object):
    def __init__(self, **kw):
        self.__dict__.update(kw)

    def __repr__(self):
        return "%s(%s)" % (
            self.__class__.__name__,
            ", ".join(["%s=%r" % (k, v) for k, v in sorted(self.__dict__.items())]))

    def relfn_unix(self):
        return self.relfn.replace("\\", "/")

    def hash(self, hash_algo='md5'):
        return '%s=%.32s' % (hash_algo, digest_file(self.fn, hash_algo))


def listdir(root):
    root = os.path.abspath(root)
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [x for x in dirnames if is_allowed_path(x)]
        for x in filenames:
            fn = os.path.join(root, dirpath, x)
            if not is_allowed_path(x) or not os.path.isfile(fn):
                continue
            res = guess_pkgname_and_version(x)
            if not res:
                # #Seems the current file isn't a proper package
                continue
            pkgname, version = res
            if pkgname:
                yield PkgFile(fn=fn, root=root, relfn=fn[len(root) + 1:],
                              pkgname=pkgname,
                              version=version,
                              parsed_version=parse_version(version))


def find_packages(pkgs, prefix=""):
    prefix = normalize_pkgname(prefix)
    for x in pkgs:
        if prefix and normalize_pkgname(x.pkgname) != prefix:
            continue
        yield x


def get_prefixes(pkgs):
    pkgnames = set()
    eggs = set()

    for x in pkgs:
        if x.pkgname:
            if x.relfn.endswith(".egg"):
                eggs.add(x.pkgname)
            else:
                pkgnames.add(x.pkgname)

    normalized_pkgnames = set(map(normalize_pkgname, pkgnames))

    for x in eggs:
        if normalize_pkgname(x) not in normalized_pkgnames:
            pkgnames.add(x)

    return pkgnames


def exists(root, filename):
    assert "/" not in filename
    dest_fn = os.path.join(root, filename)
    return os.path.exists(dest_fn)


def store(root, filename, save_method):
    assert "/" not in filename
    dest_fn = os.path.join(root, filename)
    save_method(dest_fn, overwrite=True) # Overwite check elsewhere.

    log.info("Stored package: %s", filename)
    return True

def digest_file(fpath, hash_algo):
    """
    Reads and digests a file according to specified hashing-algorith.

    :param str sha256: any algo contained in :mod:`hashlib`
    :return: <hash_algo>=<hex_digest>

    From http://stackoverflow.com/a/21565932/548792
    """
    blocksize = 2**16
    digester = getattr(hashlib, hash_algo)()
    with open(fpath, 'rb') as f:
        for block in iter(lambda: f.read(blocksize), b''):
            digester.update(block)
    return digester.hexdigest()[:32]
