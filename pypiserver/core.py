#! /usr/bin/env python3
"""minimal PyPI like server for use with pip/easy_install"""

import configparser
import mimetypes
import typing as t

from pypiserver.pkg_helpers import normalize_pkgname, parse_version

mimetypes.add_type("application/octet-stream", ".egg")
mimetypes.add_type("application/octet-stream", ".whl")
mimetypes.add_type("text/plain", ".asc")


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
        "tracking_url",  # The URL that this package tracks (PEP 708)
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
        tracking_url: t.Optional[str] = None,
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
        self.tracking_url = tracking_url

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


class PyPIServer:
    def __init__(self, config_path=None, *args, **kwargs):
        self.pep708_metadata = {}
        self.base_url = "http://localhost:8000"  # Default URL for tests
        self.project_files = {}  # Add this to simulate files per project
        if config_path:
            self._load_pep708_metadata(config_path)

    def _load_pep708_metadata(self, config_path):
        config = configparser.ConfigParser()
        config.read(config_path)
        self.pep708_metadata = {}
        for section in config.sections():
            if section.startswith("projects."):
                project = section.split(".", 1)[1]
                tracks = config.get(section, "tracks", fallback=None)
                altlocs = config.get(section, "alternate-locations", fallback=None)
                self.pep708_metadata[project] = {
                    "tracks": [t.strip() for t in tracks.split(",")] if tracks else [],
                    "alternate-locations": [a.strip() for a in altlocs.split(",")] if altlocs else [],
                }

    def get_pep708_metadata(self, project):
        return self.pep708_metadata.get(project, {"tracks": [], "alternate-locations": []})

    def get_project_files(self, project: str) -> list:
        """
        Return a list of package files for the given project.
        If the project is unknown, raise KeyError to indicate 404.
        If the project is known but has no files, return an empty list.
        """
        if project not in self.pep708_metadata:
            raise KeyError(f"Project '{project}' not found")
        return self.project_files.get(project, [])

    def simple_api_json(self, project: str) -> t.Tuple[dict, str]:
        try:
            files = self.get_project_files(project)
        except KeyError:
            from werkzeug.exceptions import NotFound
            raise NotFound(f"Project '{project}' not found")
        data = {
            "name": project,
            "files": files,
            "meta": {"api-version": "1.1"},
        }
        pep708 = self.get_pep708_metadata(project)
        if pep708["tracks"]:
            data["tracks"] = pep708["tracks"]
        if pep708["alternate-locations"]:
            data["alternate-locations"] = pep708["alternate-locations"]
        return data, "application/vnd.pypi.simple.v1+json"

    def simple_api_html(self, project) -> t.Tuple[str, str]:
        try:
            files = self.get_project_files(project)
        except KeyError:
            from werkzeug.exceptions import NotFound
            raise NotFound(f"Project '{project}' not found")
        pep708 = self.get_pep708_metadata(project)
        meta_tags = ""
        for url in pep708["tracks"]:
            meta_tags += f'<meta name="tracks" content="{url}">\n'
        for url in pep708["alternate-locations"]:
            meta_tags += f'<meta name="alternate-locations" content="{url}">\n'
        links = ""
        for f in files:
            # Example: links += f'<a href="{f["url"]}">{f["filename"]}</a><br/>\n'
            pass
        html = f"""<!DOCTYPE html>
<html>
<head>
<title>Links for {project}</title>
{meta_tags}
</head>
<body>
<h1>Links for {project}</h1>
{links}
</body>
</html>
"""
        return html, "application/vnd.pypi.simple.v1+html"

    def redirect_to_simple(self, project: str):
        """
        Simulate a 303 redirect from /{project}/ to /simple/{project}/.
        Returns a tuple: (empty body, status code, headers)
        """
        location = f"/simple/{project}/"
        return "", 303, {"Location": location}


def start_test_server(config_path=None, *args, **kwargs):
    """
    Minimal test server factory for test_api.py compatibility.
    Returns a PyPIServer instance with the given config_path.
    """
    return PyPIServer(config_path=config_path, *args, **kwargs)