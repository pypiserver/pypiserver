#! /usr/bin/env python3
"""minimal PyPI like server for use with pip/easy_install"""

import functools
import hashlib
import io
import logging
import mimetypes
import os
import sys
import typing as t
from typing import Optional
from urllib.parse import quote

import pkg_resources

from pypiserver import Configuration
from .backend import Backend, SimpleFileBackend, PkgFile

log = logging.getLogger(__name__)

backend: Optional[Backend] = None


def configure(**kwds):
    """
    :return: Configure
    """
    global backend

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

    backend = SimpleFileBackend(roots)

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


def get_bad_url_redirect_path(request, project):
    """Get the path for a bad root url."""
    uri = request.custom_fullpath
    if uri.endswith("/"):
        uri = uri[:-1]
    uri = uri.rsplit("/", 1)[0]
    project = quote(project)
    uri += f"/simple/{project}/"
    return uri


def get_all_packages():
    return backend.get_all_packages()


def find_project_packages(project):
    return backend.find_project_packages(project)


def find_version(name: str, version: str):
    return backend.find_version(name, version)


def get_projects():
    return backend.get_projects()


def exists(filename: str):
    assert "/" not in filename
    return backend.exists(filename)


def add_package(filename, fh: t.BinaryIO):
    assert "/" not in filename
    return backend.add_package(filename, fh)


def remove_package(pkg: PkgFile):
    return backend.remove_package(pkg)
