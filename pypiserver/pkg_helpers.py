import os
import re
import typing as t
from pathlib import PurePath, Path
from urllib.parse import quote


def normalize_pkgname(name: str) -> str:
    """Perform PEP 503 normalization"""
    return re.sub(r"[-_.]+", "-", name).lower()


def normalize_pkgname_for_url(name: str) -> str:
    """Perform PEP 503 normalization and ensure the value is safe for URLs."""
    return quote(normalize_pkgname(name))


# ### Next 2 functions adapted from :mod:`distribute.pkg_resources`.
#


component_re = re.compile(r"(\d+ | [a-z]+ | \.| -)", re.I | re.VERBOSE)
replace = {"pre": "c", "preview": "c", "-": "final-", "rc": "c", "dev": "@"}.get


def _parse_version_parts(s):
    for part in component_re.split(s):
        part = replace(part, part)
        if part in ["", "."]:
            continue
        if part[:1] in "0123456789":
            yield part.zfill(8)  # pad for numeric comparison
        else:
            yield "*" + part

    yield "*final"  # ensure that alpha/beta/candidate are before final


def parse_version(s: str) -> tuple:
    parts = []
    for part in _parse_version_parts(s.lower()):
        if part.startswith("*"):
            # remove trailing zeros from each series of numeric parts
            while parts and parts[-1] == "00000000":
                parts.pop()
        parts.append(part)
    return tuple(parts)


#
# ### -- End of distribute's code.


def is_listed_path(path_part: t.Union[PurePath, str]) -> bool:
    if isinstance(path_part, str):
        path_part = PurePath(path_part)
    return not any(part.startswith(".") for part in path_part.parts)


_archive_suffix_rx = re.compile(
    r"(\.zip|\.tar\.gz|\.tgz|\.tar\.bz2|-py[23]\.\d-.*|"
    r"\.win-amd64-py[23]\.\d\..*|\.win32-py[23]\.\d\..*|\.egg)$",
    re.I,
)
wheel_file_re = re.compile(
    r"""^(?P<namever>(?P<name>.+?)-(?P<ver>\d.*?))
    ((-(?P<build>\d.*?))?-(?P<pyver>.+?)-(?P<abi>.+?)-(?P<plat>.+?)
    \.whl|\.dist-info)$""",
    re.VERBOSE,
)
_pkgname_re = re.compile(r"-\d+[a-z_.!+]", re.I)
_pkgname_parts_re = re.compile(
    r"[\.\-](?=cp\d|py\d|macosx|linux|sunos|solaris|irix|aix|cygwin|win)", re.I
)


def _guess_pkgname_and_version_wheel(
    basename: str,
) -> t.Optional[t.Tuple[str, str]]:
    m = wheel_file_re.match(basename)
    if not m:
        return None
    name = m.group("name")
    ver = m.group("ver")
    build = m.group("build")
    if build:
        return name, ver + "-" + build
    else:
        return name, ver


def guess_pkgname_and_version(path: str) -> t.Optional[t.Tuple[str, str]]:
    path = os.path.basename(path)
    if path.endswith(".asc"):
        path = path.rstrip(".asc")
    if path.endswith(".whl"):
        return _guess_pkgname_and_version_wheel(path)
    if not _archive_suffix_rx.search(path):
        return None
    path = _archive_suffix_rx.sub("", path)
    if "-" not in path:
        pkgname, version = path, ""
    elif path.count("-") == 1:
        pkgname, version = path.split("-", 1)
    elif "." not in path:
        pkgname, version = path.rsplit("-", 1)
    else:
        pkgname = _pkgname_re.split(path)[0]
        ver_spec = path[len(pkgname) + 1 :]
        parts = _pkgname_parts_re.split(ver_spec)
        version = parts[0]
    return pkgname, version
