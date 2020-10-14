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
from .backend import Backend, SimpleFileBackend, PkgFile, CachingFileBackend

log = logging.getLogger(__name__)

backend: Optional[Backend] = None


def configure(**kwds):
    """
    :return: Configure
    """
    global backend

    config = Configuration(**kwds)
    log.info(f"+++Pypiserver invoked with: {config}")

    if not config.authenticated:
        config.authenticated = []
    if not callable(config.auther):
        if config.password_file and config.password_file != ".":
            from passlib.apache import HtpasswdFile

            htPsswdFile = HtpasswdFile(config.password_file)
        else:
            config.password_file = htPsswdFile = None
        config.auther = functools.partial(auth_by_htpasswd_file, htPsswdFile)

    # Read welcome-msg from external file or failback to the embedded-msg
    try:
        if not config.welcome_file:
            config.welcome_file = "welcome.html"
            config.welcome_msg = (
                pkg_resources.resource_string(  # @UndefinedVariable
                    __name__, "welcome.html"
                ).decode("utf-8")
            )  # @UndefinedVariable
        else:
            with io.open(config.welcome_file, "r", encoding="utf-8") as fd:
                config.welcome_msg = fd.read()
    except Exception:
        log.warning(
            f"Could not load welcome-file({config.welcome_file})!",
            exc_info=True,
        )

    if config.fallback_url is None:
        config.fallback_url = "https://pypi.org/simple"

    if config.hash_algo:
        try:
            halgos = hashlib.algorithms_available
        except AttributeError:
            halgos = ["md5", "sha1", "sha224", "sha256", "sha384", "sha512"]

        if config.hash_algo not in halgos:
            sys.exit(f"Hash-algorithm {config.hash_algo} not one of: {halgos}")

    backend = get_file_backend(config)

    log.info(f"+++Pypiserver started with: {config}")

    return config


def auth_by_htpasswd_file(htPsswdFile, username, password):
    """The default ``config.auther``."""
    if htPsswdFile is not None:
        htPsswdFile.load_if_changed()
        return htPsswdFile.check_password(username, password)


def get_file_backend(config) -> SimpleFileBackend:
    roots = parse_roots(config)
    try:
        from .cache import cache_manager

        return CachingFileBackend(roots, cache_manager, config)
    except ImportError:
        return SimpleFileBackend(roots, config)


def parse_roots(config) -> t.List[str]:
    if config.root is None:
        config.root = os.path.expanduser("~/packages")
    roots = (
        config.root if isinstance(config.root, (list, tuple)) else [config.root]
    )
    roots = [os.path.abspath(r) for r in roots]
    for r in roots:
        try:
            os.listdir(r)
        except OSError:
            err = sys.exc_info()[1]
            sys.exit(f"Error: while trying to list root({r}): {err}")
    return roots


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


def with_digester(func: t.Callable[..., t.Iterable[PkgFile]]):
    @functools.wraps(func)
    def add_digester_method(*args, **kwargs):
        packages = func(*args, **kwargs)
        for package in packages:
            package.digester = backend.digest
            yield package

    return add_digester_method


@with_digester
def get_all_packages() -> t.Iterable[PkgFile]:
    return backend.get_all_packages()


@with_digester
def find_project_packages(project) -> t.Iterable[PkgFile]:
    return backend.find_project_packages(project)


def find_version(name: str, version: str) -> t.Iterable[PkgFile]:
    return backend.find_version(name, version)


def get_projects() -> t.Iterable[str]:
    return backend.get_projects()


def exists(filename: str) -> bool:
    assert "/" not in filename
    return backend.exists(filename)


def add_package(filename, fh: t.BinaryIO):
    assert "/" not in filename
    return backend.add_package(filename, fh)


def remove_package(pkg: PkgFile):
    return backend.remove_package(pkg)


def digest(pkg: PkgFile) -> str:
    return backend.digest(pkg)
