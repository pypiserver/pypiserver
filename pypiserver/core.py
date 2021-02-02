#! /usr/bin/env python3
"""minimal PyPI like server for use with pip/easy_install"""

import mimetypes
import typing as t
from urllib.parse import quote

from pypiserver.pkg_helpers import normalize_pkgname, parse_version

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


class PkgFile:
    __slots__ = [
        "pkgname",  # The projects/package name with possible capitalization
        "version",  # The package version as a string
        "fn",  # The full file path
        "root",  # An optional root directory of the file
        "relfn",  # The file path relative to the root
        "replaces",  # The previous version of the package (used by manage.py)
        "pkgname_norm",  # The PEP503 normalized project name
        "digest",  # The file digest in the form of <algo>=<hash>
        "relfn_unix",  # The relative file path in unix notation
        "parsed_version",  # The package version as a tuple of parts
        "digester",  # a function that calculates the digest for the package
    ]
    digest: t.Optional[str]
    digester: t.Optional[t.Callable[["PkgFile"], t.Optional[str]]]
    parsed_version: tuple
    relfn_unix: t.Optional[str]

    def __init__(
        self,
        pkgname: str,
        version: str,
        fn: t.Optional[str] = None,
        root: t.Optional[str] = None,
        relfn: t.Optional[str] = None,
        replaces: t.Optional["PkgFile"] = None,
    ):
        self.pkgname = pkgname
        self.pkgname_norm = normalize_pkgname(pkgname)
        self.version = version
        self.parsed_version: tuple = parse_version(version)
        self.fn = fn
        self.root = root
        self.relfn = relfn
        self.relfn_unix = None if relfn is None else relfn.replace("\\", "/")
        self.replaces = replaces
        self.digest = None
        self.digester = None

    def __repr__(self) -> str:
        return "{}({})".format(
            self.__class__.__name__,
            ", ".join(
                [
                    f"{k}={getattr(self, k, 'AttributeError')!r}"
                    for k in sorted(self.__slots__)
                ]
            ),
        )

    @property
    def fname_and_hash(self) -> str:
        if self.digest is None and self.digester is not None:
            self.digest = self.digester(self)
        hashpart = f"#{self.digest}" if self.digest else ""
        return self.relfn_unix + hashpart  # type: ignore
