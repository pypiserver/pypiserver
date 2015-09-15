#! /usr/bin/env python
"""minimal PyPI like server for use with pip/easy_install"""

import os
import re
import mimetypes
import warnings
import logging

warnings.filterwarnings("ignore", "Python 2.5 support may be dropped in future versions of Bottle")
mimetypes.add_type("application/octet-stream", ".egg")
mimetypes.add_type("application/octet-stream", ".whl")

log = logging.getLogger('pypiserver.core')

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


def store(root, filename, data):
    assert "/" not in filename
    dest_fn = os.path.join(root, filename)
    dest_fh = open(dest_fn, "wb")
    dest_fh.write(data)
    dest_fh.close()

    log.info("Stored package: %s", filename)
    return True
