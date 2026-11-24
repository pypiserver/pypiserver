import abc
import functools
import hashlib
import itertools
import logging
import os
import threading
import typing as t
from pathlib import Path

from .cache import ENABLE_CACHING, CacheManager
from .core import PkgFile
from .pkg_helpers import (
    guess_pkgname_and_version,
    is_listed_path,
    normalize_pkgname,
)

if t.TYPE_CHECKING:
    from .config import _ConfigCommon as Configuration


log = logging.getLogger(__name__)


PathLike = t.Union[str, os.PathLike]


class IBackend(abc.ABC):
    def get_by_relfn(self, relfn_unix: str) -> t.Optional[PkgFile]:
        """Return the package whose relfn_unix matches, if known."""
        return None

    @abc.abstractmethod
    def get_all_packages(self) -> t.Iterable[PkgFile]:
        pass

    @abc.abstractmethod
    def find_project_packages(self, project: str) -> t.Iterable[PkgFile]:
        pass

    @abc.abstractmethod
    def find_version(self, name: str, version: str) -> t.Iterable[PkgFile]:
        pass

    @abc.abstractmethod
    def get_projects(self) -> t.Iterable[str]:
        pass

    @abc.abstractmethod
    def exists(self, filename: str) -> bool:
        pass

    @abc.abstractmethod
    def digest(self, pkg: PkgFile) -> t.Optional[str]:
        pass

    @abc.abstractmethod
    def package_count(self) -> int:
        pass

    @abc.abstractmethod
    def add_package(self, filename: str, stream: t.BinaryIO) -> None:
        pass

    @abc.abstractmethod
    def remove_package(self, pkg: PkgFile) -> None:
        pass


class Backend(IBackend, abc.ABC):
    def __init__(self, config: "Configuration"):
        self.hash_algo = config.hash_algo

    def get_by_relfn(self, relfn_unix: str) -> t.Optional[PkgFile]:
        for pkg in self.get_all_packages():
            if pkg.relfn_unix == relfn_unix:
                return pkg
        return None

    @abc.abstractmethod
    def get_all_packages(self) -> t.Iterable[PkgFile]:
        """Implement this method to return an Iterable of all packages (as
        PkgFile objects) that are available in the Backend.
        """
        pass

    @abc.abstractmethod
    def add_package(self, filename: str, stream: t.BinaryIO) -> None:
        """Add a package to the Backend. `filename` is the package's filename
        (without any directory parts). It is just a name, there is no file by
        that name (yet). `stream` is an open file-like object that can be used
        to read the file's content. To convert the package into an actual file
        on disk, run `write_file(filename, stream)`.
        """
        pass

    @abc.abstractmethod
    def remove_package(self, pkg: PkgFile) -> None:
        """Remove a package from the Backend"""
        pass

    @abc.abstractmethod
    def exists(self, filename: str) -> bool:
        """Does a package by the given name exist?"""
        pass

    def digest(self, pkg: PkgFile) -> t.Optional[str]:
        if self.hash_algo is None or pkg.fn is None:
            return None
        return digest_file(pkg.fn, self.hash_algo)

    def package_count(self) -> int:
        """Return a count of all available packages. When implementing a Backend
        class, either use this method as is, or override it with a more
        performant version.
        """
        return sum(1 for _ in self.get_all_packages())

    def get_projects(self) -> t.Iterable[str]:
        """Return an iterable of all (unique) projects available in the store
        in their PEP503 normalized form. When implementing a Backend class,
        either use this method as is, or override it with a more performant
        version.
        """
        return set(package.pkgname_norm for package in self.get_all_packages())

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

    def find_version(self, name: str, version: str) -> t.Iterable[PkgFile]:
        """Return packages matching name and version (PEP 503-normalized)."""
        normalized = normalize_pkgname(name)
        return filter(
            lambda pkg: (
                pkg.pkgname_norm == normalized and pkg.version == version
            ),
            self.get_all_packages(),
        )


class _PackageIndex:
    """Package lookup tables built together in scan order."""

    __slots__ = (
        "all_packages",
        "by_relfn",
        "by_basename",
        "by_project",
        "by_project_version",
        "projects",
        "count",
    )

    def __init__(self, packages: t.Iterable[PkgFile]) -> None:
        self.all_packages: list[PkgFile] = []
        self.by_relfn: dict[str, PkgFile] = {}
        self.by_basename: dict[str, list[PkgFile]] = {}
        self.by_project: dict[str, list[PkgFile]] = {}
        self.by_project_version: dict[tuple[str, str], list[PkgFile]] = {}
        for pkg in packages:
            self.all_packages.append(pkg)
            if pkg.relfn_unix is not None:
                self.by_relfn.setdefault(pkg.relfn_unix, pkg)
            basename = os.path.basename(pkg.relfn_unix or pkg.fn or "")
            if basename:
                self.by_basename.setdefault(basename, []).append(pkg)
            self.by_project.setdefault(pkg.pkgname_norm, []).append(pkg)
            key = (pkg.pkgname_norm, pkg.version)
            self.by_project_version.setdefault(key, []).append(pkg)
        self.projects = frozenset(self.by_project)
        self.count = len(self.all_packages)


class _IndexedBackend:
    """Mixin: reuse a package index until the backend's change token advances.

    Only the caching backend opts into this. ``SimpleFileBackend`` keeps
    rescanning on every call on purpose: a root ``st_mtime_ns`` token cannot see
    a package dropped into a subdirectory, and reusing the memoised ``PkgFile``
    objects would keep serving a stale digest after an in-place replace. Under
    ``CachingFileBackend`` the watchdog owns invalidation, so both of those
    signals already exist.
    """

    # Declared here so the mixin is type-checkable; the caching backend
    # initialises them next to its cache manager.
    _index: t.Optional[_PackageIndex] = None
    _index_token: t.Any = None
    _index_lock: "threading.RLock"

    def _scan_packages(self) -> t.Iterable[PkgFile]:
        raise NotImplementedError

    def _current_index_token(self) -> t.Any:
        raise NotImplementedError

    def _ensure_index(self) -> _PackageIndex:
        token = self._current_index_token()
        index = self._index
        if index is not None and token == self._index_token:
            return index
        with self._index_lock:
            token = self._current_index_token()
            index = self._index
            if index is not None and token == self._index_token:
                return index
            index = _PackageIndex(self._scan_packages())
            self._index = index
            self._index_token = token
            return index

    def invalidate_index(self) -> None:
        with self._index_lock:
            self._index = None
            self._index_token = None

    def get_by_relfn(self, relfn_unix: str) -> t.Optional[PkgFile]:
        return self._ensure_index().by_relfn.get(relfn_unix)

    def get_all_packages(self) -> t.Iterable[PkgFile]:
        return self._ensure_index().all_packages

    def find_project_packages(self, project: str) -> t.Iterable[PkgFile]:
        return self._ensure_index().by_project.get(
            normalize_pkgname(project), []
        )

    def find_version(self, name: str, version: str) -> t.Iterable[PkgFile]:
        key = (normalize_pkgname(name), version)
        return self._ensure_index().by_project_version.get(key, [])

    def get_projects(self) -> t.Iterable[str]:
        return set(self._ensure_index().projects)

    def package_count(self) -> int:
        return self._ensure_index().count

    def exists(self, filename: str) -> bool:
        return bool(self._ensure_index().by_basename.get(filename))


class SimpleFileBackend(Backend):
    def __init__(self, config: "Configuration"):
        super().__init__(config)
        self.roots = [Path(root).resolve() for root in config.roots]

    def get_all_packages(self) -> t.Iterable[PkgFile]:
        return itertools.chain.from_iterable(listdir(r) for r in self.roots)

    def add_package(self, filename: str, stream: t.BinaryIO) -> None:
        write_file(stream, self.roots[0].joinpath(filename))

    def remove_package(self, pkg: PkgFile) -> None:
        if pkg.fn is not None:
            try:
                os.remove(pkg.fn)
            except FileNotFoundError:
                log.warning(
                    "Tried to remove %s, but it is already gone", pkg.fn
                )
            except OSError:
                log.exception("Unexpected error removing package: %s", pkg.fn)
                raise

    def exists(self, filename: str) -> bool:
        return any(
            filename == existing_file.name
            for root in self.roots
            for existing_file in all_listed_files(root)
        )


class CachingFileBackend(_IndexedBackend, SimpleFileBackend):
    def __init__(
        self,
        config: "Configuration",
        cache_manager: t.Optional[CacheManager] = None,
    ):
        super().__init__(config)

        self.cache_manager = cache_manager or CacheManager()  # type: ignore
        self._index = None
        self._index_token = None
        self._index_lock = threading.RLock()

    def add_package(self, filename: str, stream: t.BinaryIO) -> None:
        super().add_package(filename, stream)
        self.cache_manager.invalidate_root_cache(self.roots[0])

    def remove_package(self, pkg: PkgFile) -> None:
        super().remove_package(pkg)
        self.cache_manager.invalidate_root_cache(pkg.root)

    def _scan_packages(self) -> t.Iterable[PkgFile]:
        return itertools.chain.from_iterable(
            self.cache_manager.listdir(r, listdir) for r in self.roots
        )

    def _current_index_token(self) -> t.Any:
        return self.cache_manager.generation

    def digest(self, pkg: PkgFile) -> t.Optional[str]:
        if self.hash_algo is None or pkg.fn is None:
            return None
        return self.cache_manager.digest_file(
            pkg.fn, self.hash_algo, digest_file
        )


def write_file(fh: t.BinaryIO, destination: PathLike) -> None:
    """write a byte stream into a destination file. Writes are chunked to reduce
    the memory footprint
    """
    chunk_size = 2**20  # 1 MB
    offset = fh.tell()
    try:
        with open(destination, "wb") as dest:
            for chunk in iter(lambda: fh.read(chunk_size), b""):
                dest.write(chunk)
    finally:
        fh.seek(offset)


def listdir(root: Path) -> t.Iterator[PkgFile]:
    root = root.resolve()
    files = all_listed_files(root)
    yield from valid_packages(root, files)


def all_listed_files(root: Path) -> t.Iterator[Path]:
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = (
            dirname for dirname in dirnames if is_listed_path(Path(dirname))
        )
        for filename in filenames:
            if not is_listed_path(Path(filename)):
                continue
            filepath = root / dirpath / filename
            if Path(filepath).is_file():
                yield filepath


def valid_packages(root: Path, files: t.Iterable[Path]) -> t.Iterator[PkgFile]:
    for file in files:
        res = guess_pkgname_and_version(str(file.name))
        if res is not None:
            pkgname, version = res
            fn = str(file)
            root_name = str(root)
            yield PkgFile(
                pkgname=pkgname,
                version=version,
                fn=fn,
                root=root_name,
                relfn=fn[len(root_name) + 1 :],
            )


def digest_file(file_path: PathLike, hash_algo: str) -> str:
    """
    Reads and digests a file according to specified hashing-algorith.

    :param file_path: path to a file on disk
    :param hash_algo: any algo contained in :mod:`hashlib`
    :return: <hash_algo>=<hex_digest>

    From http://stackoverflow.com/a/21565932/548792
    """
    blocksize = 2**16
    digester = hashlib.new(hash_algo)
    with open(file_path, "rb") as f:
        for block in iter(lambda: f.read(blocksize), b""):
            digester.update(block)
    return f"{hash_algo}={digester.hexdigest()}"


def get_file_backend(config: "Configuration") -> Backend:
    if ENABLE_CACHING:
        return CachingFileBackend(config)
    return SimpleFileBackend(config)


PkgFunc = t.TypeVar("PkgFunc", bound=t.Callable[..., t.Iterable[PkgFile]])


def with_digester(func: PkgFunc) -> PkgFunc:
    @functools.wraps(func)
    def add_digester_method(
        self: "BackendProxy", *args: t.Any, **kwargs: t.Any
    ) -> t.Iterable[PkgFile]:
        packages = func(self, *args, **kwargs)
        for package in packages:
            package.digester = self.backend.digest
            yield package

    return t.cast(PkgFunc, add_digester_method)


class BackendProxy(IBackend):
    def __init__(self, wraps: Backend):
        self.backend = wraps

    def get_by_relfn(self, relfn_unix: str) -> t.Optional[PkgFile]:
        return self.backend.get_by_relfn(relfn_unix)

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

    def add_package(self, filename: str, fh: t.BinaryIO) -> None:
        assert "/" not in filename
        return self.backend.add_package(filename, fh)

    def remove_package(self, pkg: PkgFile) -> None:
        return self.backend.remove_package(pkg)

    def digest(self, pkg: PkgFile) -> t.Optional[str]:
        return self.backend.digest(pkg)
