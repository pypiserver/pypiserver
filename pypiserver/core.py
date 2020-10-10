#! /usr/bin/env python3
"""minimal PyPI like server for use with pip/easy_install"""

import functools
import hashlib
import io
import itertools
import logging
import mimetypes
import os
import sys
from typing import Optional
from urllib.parse import quote

import pkg_resources

from pypiserver import Configuration
from .backend import listdir
from .pkg_helpers import normalize_pkgname

log = logging.getLogger(__name__)

packages: Optional[callable] = None


def configure(**kwds):
    """
    :return: a 2-tuple (Configure, package-list)
    """
    global packages
    c = Configuration(**kwds)
    log.info(f"+++Pypiserver invoked with: {c}")

    if c.root is None:
        c.root = os.path.expanduser("~/packages")
    roots = c.root if isinstance(c.root, (list, tuple)) else [c.root]
    roots = [os.path.abspath(r) for r in roots]
    for r in roots:
        try:
            os.listdir(r)
        except OSError:
            err = sys.exc_info()[1]
            sys.exit(f"Error: while trying to list root({r}): {err}")

    packages = lambda: itertools.chain(*[listdir(r) for r in roots])
    packages.root = roots[0]

    if not c.authenticated:
        c.authenticated = []
    if not callable(c.auther):
        if c.password_file and c.password_file != ".":
            from passlib.apache import HtpasswdFile

            htPsswdFile = HtpasswdFile(c.password_file)
        else:
            c.password_file = htPsswdFile = None
        c.auther = functools.partial(auth_by_htpasswd_file, htPsswdFile)

    # Read welcome-msg from external file or failback to the embedded-msg
    try:
        if not c.welcome_file:
            c.welcome_file = "welcome.html"
            c.welcome_msg = pkg_resources.resource_string(  # @UndefinedVariable
                __name__, "welcome.html"
            ).decode(
                "utf-8"
            )  # @UndefinedVariable
        else:
            with io.open(c.welcome_file, "r", encoding="utf-8") as fd:
                c.welcome_msg = fd.read()
    except Exception:
        log.warning(
            f"Could not load welcome-file({c.welcome_file})!", exc_info=True
        )

    if c.fallback_url is None:
        c.fallback_url = "https://pypi.org/simple"

    if c.hash_algo:
        try:
            halgos = hashlib.algorithms_available
        except AttributeError:
            halgos = ["md5", "sha1", "sha224", "sha256", "sha384", "sha512"]

        if c.hash_algo not in halgos:
            sys.exit(f"Hash-algorithm {c.hash_algo} not one of: {halgos}")

    log.info(f"+++Pypiserver started with: {c}")

    return c


def auth_by_htpasswd_file(htPsswdFile, username, password):
    """The default ``config.auther``."""
    if htPsswdFile is not None:
        htPsswdFile.load_if_changed()
        return htPsswdFile.check_password(username, password)


mimetypes.add_type("application/octet-stream", ".egg")
mimetypes.add_type("application/octet-stream", ".whl")
mimetypes.add_type("text/plain", ".asc")


def find_packages(pkgs=None, prefix=""):
    if pkgs is None:
        pkgs = packages()
    prefix = normalize_pkgname(prefix)
    for x in pkgs:
        if prefix and x.pkgname_norm != prefix:
            continue
        yield x


def get_prefixes():
    pkgs = packages()
    normalized_pkgnames = set()
    for x in pkgs:
        if x.pkgname:
            normalized_pkgnames.add(x.pkgname_norm)
    return normalized_pkgnames


def exists(filename):
    root = packages.root
    assert "/" not in filename
    dest_fn = os.path.join(root, filename)
    return os.path.exists(dest_fn)


def store(filename, save_method):
    root = packages.root
    assert "/" not in filename
    dest_fn = os.path.join(root, filename)
    save_method(dest_fn, overwrite=True)  # Overwite check earlier.


def get_bad_url_redirect_path(request, prefix):
    """Get the path for a bad root url."""
    p = request.custom_fullpath
    if p.endswith("/"):
        p = p[:-1]
    p = p.rsplit("/", 1)[0]
    prefix = quote(prefix)
    p += "/simple/{}/".format(prefix)
    return p



