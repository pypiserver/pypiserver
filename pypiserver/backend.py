import hashlib
import itertools
import os
import typing as t
from pathlib import Path, PurePath

from .pkg_helpers import (
    normalize_pkgname,
    parse_version,
    is_allowed_path,
    guess_pkgname_and_version,
)

PathLike = t.Union[str, bytes, Path, PurePath]


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


class Backend:
    def get_all_packages(self) -> t.Iterable[PkgFile]:
        """Implement this method to return an Iterable of all packages (as
        PkgFile objects) that are available in the Backend.
        """
        raise NotImplementedError

    def add_package(self, filename: str, fh: t.BinaryIO) -> PkgFile:
        """Add a package to the Backend. `filename` is the package's filename
        (without any directory parts). It is just a name, there is no file by
        that name (yet). `fh` is an open file object that can be used to read
        the file's content. To convert the package into an actual file on disk,
        run `as_file(filename, fh)`. This method should return a PkgFile object
        representing the newly added package
        """
        raise NotImplementedError

    def remove_package(self, pkg: PkgFile):
        """Remove a package from the Backend"""
        raise NotImplementedError

    def digest(self, pkg: PkgFile, hash_algo):
        """Calculate a package's digest"""
        raise NotImplementedError

    def exists(self, filename) -> bool:
        """Does a package by the given name exist?"""
        raise NotImplementedError

    def get_projects(self) -> t.Iterable[str]:
        """Return an iterable of all (unique) projects available in the store
        in their PEP503 normalized form. When implementing a Backend class,
        either use this method as is, or override it with a more performant
        version.
        """
        normalized_pkgnames = set()
        for x in self.get_all_packages():
            if x.pkgname:
                normalized_pkgnames.add(x.pkgname_norm)
        return normalized_pkgnames

    def find_project_packages(self, project: str) -> t.Iterable[PkgFile]:
        """Find all packages from a given project. The project may be given
        as either the normalized or canonical name. When implementing a
        Backend class, either use this method as is, or override it with a
        more performant version.
        """
        return (
            x
            for x in self.get_all_packages()
            if normalize_pkgname(project) == x.pkgname_norm
        )

    def find_version(self, name, version) -> t.Iterable[PkgFile]:
        """Return all packages that match PkgFile.pkgname == name and
        PkgFile.version == version` When implementing a Backend class,
        either use this method as is, or override it with a more performant
        version.
        """
        return filter(
            lambda pkg: pkg.pkgname == name and pkg.version == version,
            self.get_all_packages(),
        )


def as_file(fh: t.BinaryIO, destination: PathLike):
    # taken from bottle.FileUpload
    chunk_size = 2 ** 16  # 64 KB
    read, offset = fh.read, fh.tell()
    with open(destination, "wb") as dest:
        while True:
            buf = read(chunk_size)
            if not buf:
                break
            dest.write(buf)
    fh.seek(offset)


class SimpleFileBackend(Backend):
    def __init__(self, roots: t.List[PathLike] = None):
        self.roots = [Path(root).resolve() for root in roots]

    def add_package(self, filename: str, fh: t.BinaryIO):
        as_file(fh, self.roots[0].joinpath(filename))

    def remove_package(self, pkg: PkgFile):
        os.remove(pkg.fn)

    def exists(self, filename):
        return any(root.joinpath(filename).exists() for root in self.roots)

    def get_all_packages(self):
        return itertools.chain(*[listdir(r) for r in self.roots])


def _listdir(root: PathLike) -> t.Iterable[PkgFile]:
    root = os.path.abspath(root)
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [x for x in dirnames if is_allowed_path(x)]
        for x in filenames:
            fn = os.path.join(root, dirpath, x)
            if not is_allowed_path(x) or not os.path.isfile(fn):
                continue
            res = guess_pkgname_and_version(x)
            if not res:
                # Seems the current file isn't a proper package
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

    def listdir(root: PathLike) -> t.Iterable[PkgFile]:
        # root must be absolute path
        return cache_manager.listdir(root, _listdir)

    def digest_file(fpath: PathLike, hash_algo):
        # fpath must be absolute path
        return cache_manager.digest_file(fpath, hash_algo, _digest_file)


except ImportError:
    listdir = _listdir
    digest_file = _digest_file
