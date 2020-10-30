#! /usr/bin/env python3
"""minimal PyPI like server for use with pip/easy_install"""

import functools
import mimetypes
import typing as t
from typing import Optional
from urllib.parse import quote

from .backend import (
    Backend,
    SimpleFileBackend,
    PkgFile,
    CachingFileBackend,
    IBackend,
)
from .cache import ENABLE_CACHING, CacheManager

backend: Optional[Backend] = None

mimetypes.add_type("application/octet-stream", ".egg")
mimetypes.add_type("application/octet-stream", ".whl")
mimetypes.add_type("text/plain", ".asc")


def get_file_backend(config) -> SimpleFileBackend:
    if ENABLE_CACHING:
        return CachingFileBackend(config, config.roots, CacheManager())
    return SimpleFileBackend(config, config.roots)


def get_bad_url_redirect_path(request, project):
    """Get the path for a bad root url."""
    uri = request.custom_fullpath
    if uri.endswith("/"):
        uri = uri[:-1]
    uri = uri.rsplit("/", 1)[0]
    project = quote(project)
    uri += f"/simple/{project}/"
    return uri


PkgFunc = t.TypeVar("PkgFunc", bound=t.Callable[..., t.Iterable[PkgFile]])


def with_digester(func: PkgFunc) -> PkgFunc:
    @functools.wraps(func)
    def add_digester_method(self, *args, **kwargs):
        packages = func(self, *args, **kwargs)
        for package in packages:
            package.digester = self.backend.digest
            yield package

    return add_digester_method


class BackendProxy(IBackend):
    def __init__(self, wraps: Backend):
        self.backend = wraps

    @with_digester
    def get_all_packages(self) -> t.Iterable[PkgFile]:
        return self.backend.get_all_packages()

    @with_digester
    def find_project_packages(self, project: str) -> t.Iterable[PkgFile]:
        return self.backend.find_project_packages(project)

    def find_version(self, name: str, version: str) -> t.Iterable[PkgFile]:
        return self.backend.find_version(name, version)

    def get_projects(self) -> t.Iterable[str]:
        return self.backend.get_projects()

    def exists(self, filename: str) -> bool:
        assert "/" not in filename
        return self.backend.exists(filename)

    def package_count(self) -> int:
        return self.backend.package_count()

    def add_package(self, filename, fh: t.BinaryIO):
        assert "/" not in filename
        return self.backend.add_package(filename, fh)

    def remove_package(self, pkg: PkgFile):
        return self.backend.remove_package(pkg)

    def digest(self, pkg: PkgFile) -> str:
        return self.backend.digest(pkg)
