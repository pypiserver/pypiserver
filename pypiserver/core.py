#! /usr/bin/env python
"""minimal PyPI like server for use with pip/easy_install"""

import hashlib
import itertools
import logging
import mimetypes
import os
import re

import pkg_resources
from pkg_resources import iter_entry_points

from .const import PLUGIN_GROUPS, PY2, STANDALONE_WELCOME
from .plugins.authenticators.interface import convert_legacy

if PY2:
    from io import open


log = logging.getLogger(__name__)

_archive_suffix_rx = re.compile(
    r"(\.zip|\.tar\.gz|\.tgz|\.tar\.bz2|-py[23]\.\d-.*|"
    "\.win-amd64-py[23]\.\d\..*|\.win32-py[23]\.\d\..*|\.egg)$",
    re.I)
wheel_file_re = re.compile(
    r"""^(?P<namever>(?P<name>.+?)-(?P<ver>\d.*?))
    ((-(?P<build>\d.*?))?-(?P<pyver>.+?)-(?P<abi>.+?)-(?P<plat>.+?)
    \.whl|\.dist-info)$""",
    re.VERBOSE)
_pkgname_re = re.compile(r'-\d+[a-z_.!+]', re.I)
_pkgname_parts_re = re.compile(
    r"[\.\-](?=cp\d|py\d|macosx|linux|sunos|solaris|irix|aix|cygwin|win)",
    re.I)


def _validate_roots(roots):
    """Validate roots.

    :param List[str] roots: a list of package roots.
    """
    for root in roots:
        try:
            os.listdir(root)
        except OSError as exc:
            raise ValueError(
                'Error while trying to list root({}): '
                '{}'.format(root, repr(exc))
            )


def _welcome_msg(welcome_file):
    """Parse the provided welcome file to get the welcome message."""
    try:
        # pkg_resources.resource_filename() is not supported for zipfiles,
        # so we rely on resource_string() instead.
        if welcome_file == STANDALONE_WELCOME:
            welcome_msg = pkg_resources.resource_string(
                __name__, 'welcome.html'
            ).decode('utf-8')
        else:
            with open(welcome_file, 'r', encoding='utf-8') as fd:
                welcome_msg = fd.read()
    except Exception:
        log.warning(
            "Could not load welcome file(%s)!",
            welcome_file,
            exc_info=1
        )
    return welcome_msg


def prep_config(config):
    """Check config arguments and update values when required.

    :param argparse.Namespace config: a config namespace

    :raises ValueError: if a config value is invalid
    """
    _validate_roots(config.roots)
    config.welcome_msg = _welcome_msg(config.welcome_file)


def configure(config):
    """Validate configuration and return with a package list.

    :param argparse.Namespace config: a config namespace

    :return:  2-tuple (Configure, package-list)
    :rtype: tuple
    """
    prep_config(config)
    add_plugins_to_config(config)

    def packages():
        """Return an iterable over package files in package roots."""
        return itertools.chain(*[listdir(r) for r in config.roots])

    packages.root = config.roots[0]

    log.info("+++Pypiserver started with: %s", config)

    return config, packages


def load_plugins(*groups):
    """Load pypiserver plugins.

    :param groups: the plugin group(s) names (str) to load. Group names
        must be one of ``const.PLUGIN_GROUPS``. If no groups are
        provided, all groups will be loaded.

    :return: a dict whose keys are plugin group names and whose values
        are nested dicts whose keys are plugin names and whose values
        are the loaded plugins.
    :rtype: dict
    """
    if groups and not all(g in PLUGIN_GROUPS for g in groups):
        raise ValueError(
            'Invalid group provided. Groups must '
            'be one of: {}'.format(PLUGIN_GROUPS)
        )
    groups = groups if groups else PLUGIN_GROUPS
    plugins = {}
    for group in groups:
        plugins.setdefault(group, {})
        for plugin in iter_entry_points('pypiserver.{}'.format(group)):
            plugins[group][plugin.name] = plugin.load()
    return plugins


def add_plugins_to_config(config, plugins=None):
    """Load plugins if necessary and add to a config object.

    :param argparse.Namespace config: a config namespace
    :param dict plugins: an optional loaded plugin dict. If not
        provided, plugins will be loaded.
    """
    plugins = load_plugins() if plugins is None else plugins
    config.plugins = plugins


def auth_by_htpasswd_file(ht_pwd_file, username, password):
    """The default ``config.auther``."""
    if ht_pwd_file is not None:
        ht_pwd_file.load_if_changed()
        return ht_pwd_file.check_password(username, password)


mimetypes.add_type("application/octet-stream", ".egg")
mimetypes.add_type("application/octet-stream", ".whl")
mimetypes.add_type("text/plain", ".asc")


# ### Next 2 functions adapted from :mod:`distribute.pkg_resources`.
component_re = re.compile(r'(\d+ | [a-z]+ | \.| -)', re.I | re.VERBOSE)
replace = {
    'pre': 'c',
    'preview': 'c',
    '-': 'final-',
    'rc': 'c',
    'dev': '@'
}.get


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
    if path.endswith(".asc"):
        path = path.rstrip(".asc")
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
        pkgname = _pkgname_re.split(path)[0]
        ver_spec = path[len(pkgname) + 1:]
        parts = _pkgname_parts_re.split(ver_spec)
        version = parts[0]
    return pkgname, version


def normalize_pkgname(name):
    """Perform PEP 503 normalization"""
    return re.sub(r"[-_.]+", "-", name).lower()


def is_allowed_path(path_part):
    p = path_part.replace("\\", "/")
    return not (p.startswith(".") or "/." in p)


class PkgFile(object):
    """Provide methods on a package file."""

    __slots__ = ['fn', 'root', '_fname_and_hash',
                 'relfn', 'relfn_unix',
                 'pkgname_norm',
                 'pkgname',
                 'version',
                 'parsed_version',
                 'replaces']

    def __init__(self, pkgname, version, fn=None, root=None,
                 relfn=None, replaces=None):
        self.pkgname = pkgname
        self.pkgname_norm = normalize_pkgname(pkgname)
        self.version = version
        self.parsed_version = parse_version(version)
        self.fn = fn
        self.root = root
        self.relfn = relfn
        self.relfn_unix = None if relfn is None else relfn.replace("\\", "/")
        self.replaces = replaces

    def __repr__(self):
        return "%s(%s)" % (
            self.__class__.__name__,
            ", ".join([
                "%s=%r" % (k, getattr(self, k)) for k in sorted(self.__slots__)
            ])
        )

    def fname_and_hash(self, hash_algo):
        if not hasattr(self, '_fname_and_hash'):
            if hash_algo:
                self._fname_and_hash = (
                    '%s#%s=%.32s' % (
                        self.relfn_unix,
                        hash_algo,
                        digest_file(self.fn, hash_algo)
                    )
                )
            else:
                self._fname_and_hash = self.relfn_unix
        return self._fname_and_hash


def _listdir(root):
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
                yield PkgFile(pkgname=pkgname,
                              version=version,
                              fn=fn, root=root,
                              relfn=fn[len(root) + 1:])


def find_packages(pkgs, prefix=""):
    prefix = normalize_pkgname(prefix)
    for x in pkgs:
        if prefix and x.pkgname_norm != prefix:
            continue
        yield x


def get_prefixes(pkgs):
    normalized_pkgnames = set()
    for x in pkgs:
        if x.pkgname:
            normalized_pkgnames.add(x.pkgname_norm)
    return normalized_pkgnames


def exists(root, filename):
    assert "/" not in filename
    dest_fn = os.path.join(root, filename)
    return os.path.exists(dest_fn)


def store(root, filename, save_method):
    assert "/" not in filename
    dest_fn = os.path.join(root, filename)
    save_method(dest_fn, overwrite=True)  # Overwite check earlier.


def _digest_file(fpath, hash_algo):
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


try:
    from .cache import cache_manager

    def listdir(root):
        # root must be absolute path
        return cache_manager.listdir(root, _listdir)

    def digest_file(fpath, hash_algo):
        # fpath must be absolute path
        return cache_manager.digest_file(fpath, hash_algo, _digest_file)

except ImportError:
    listdir = _listdir
    digest_file = _digest_file
