import hashlib
import os
from pathlib import Path
from typing import List, Union

from .pkg_utils import (
    normalize_pkgname,
    parse_version,
    is_allowed_path,
    guess_pkgname_and_version,
)


class Backend:
    def find_packages(self):
        raise NotImplementedError

    def find_package(self, name, version):
        raise NotImplementedError

    def add_package(self, pkg):
        raise NotImplementedError

    def remove_package(self):
        raise NotImplementedError

    def digest_file(self):
        raise NotImplementedError


class SimpleFileBackend(Backend):
    def __init__(self, roots: List[Union[str, Path]] = None):
        self.roots = roots


class PkgFile:

    __slots__ = [
        "fn",
        "root",
        "_fname_and_hash",
        "relfn",
        "relfn_unix",
        "pkgname_norm",
        "pkgname",
        "version",
        "parsed_version",
        "replaces",
    ]

    def __init__(
        self, pkgname, version, fn=None, root=None, relfn=None, replaces=None
    ):
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
        return "{}({})".format(
            self.__class__.__name__,
            ", ".join(
                [
                    f"{k}={getattr(self, k, 'AttributeError')!r}"
                    for k in sorted(self.__slots__)
                ]
            ),
        )

    def fname_and_hash(self, hash_algo):
        if not hasattr(self, "_fname_and_hash"):
            if hash_algo:
                self._fname_and_hash = (
                    f"{self.relfn_unix}#{hash_algo}="
                    f"{digest_file(self.fn, hash_algo)}"
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
                yield PkgFile(
                    pkgname=pkgname,
                    version=version,
                    fn=fn,
                    root=root,
                    relfn=fn[len(root) + 1 :],
                )


def _digest_file(fpath, hash_algo):
    """
    Reads and digests a file according to specified hashing-algorith.

    :param str sha256: any algo contained in :mod:`hashlib`
    :return: <hash_algo>=<hex_digest>

    From http://stackoverflow.com/a/21565932/548792
    """
    blocksize = 2 ** 16
    digester = getattr(hashlib, hash_algo)()
    with open(fpath, "rb") as f:
        for block in iter(lambda: f.read(blocksize), b""):
            digester.update(block)
    return digester.hexdigest()


try:
    from .cache import cache_manager

    def listdir(root):
        # root must be absolute path
        return cache_manager.listdir(root, _listdir)

    def digest_file(fpath, hash_algo):
        # fpath must be absolute path
        return cache_manager.digest_file(fpath, hash_algo, _digest_file)


except ImportError:
    pass


listdir = _listdir
digest_file = _digest_file
