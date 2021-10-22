#
# The cache implementation is only used when the watchdog package
# is installed
#

import platform
from os import stat
from os import listdir
from os.path import dirname
from pathlib import Path
from subprocess import check_output
import typing as t
import threading

from .pkg_helpers import guess_pkgname_and_version
from .core import PkgFile
try:
    from watchdog.observers import Observer
    from watchdog.observers.polling import PollingObserver

    ENABLE_CACHING = True

except ImportError:

    Observer = None
    PollingObserver = None

    ENABLE_CACHING = False


class CacheManager:
    """
    A naive cache implementation for listdir and digest_file

    The listdir_cache is just a giant list of PkgFile objects, and
    we modify the list based on FileEvents from the watchdog.Observer
    (or PollingObserver on nfs)

    The digest_cache exists on a per-file basis, because computing
    hashes on large files can get expensive, and it's very easy to
    invalidate specific filenames.
    """

    @staticmethod
    def root_is_nfs(path: str):
        if "Windows" in platform.system():
            # Lazy: Answering this on Windows is more involved.
            return False
        # From https://stackoverflow.com/a/460061/13483441
        return b"nfs" in check_output(["stat", "-f", "-L", "-c", "%T", path])

    @staticmethod
    def get_pkgfile_for_path(path: str, root: t.Union[Path, str]):
        pathlib_path = Path(path)
        res = guess_pkgname_and_version(str(pathlib_path.name))
        if res is None:
            # Assume it's not a python package
            return
        event_dest_pkgname, event_dest_version = res
        return PkgFile(
            pkgname=event_dest_pkgname,
            version=event_dest_version,
            fn=str(pathlib_path),
            root=str(root),
            relfn=str(pathlib_path)[len(str(root)) + 1 :],
        )

    def __init__(self):
        if not ENABLE_CACHING:
            raise RuntimeError(
                "Please install the extra cache requirements by running 'pip "
                "install pypiserver[cache]' to use the CachingFileBackend"
            )

        # Cache for listdir output
        self.listdir_cache = {}

        # Cache for hashes: two-level dictionary
        # -> key: hash_algo, value: dict
        #    -> key: file path, value: hash
        # We assume that the hash_algo value will never be erased
        self.digest_cache = {}

        self.observer = Observer()
        self.observer.start()

        # Directories being watched
        self.watched = set()

        self.watch_lock = threading.Lock()
        self.digest_lock = threading.Lock()
        self.listdir_lock = threading.Lock()

        # Used to track whether any root is an NFS volume
        self.polling = False
        self.polling_interval = 1

    def set_cache_polling_interval(self, cache_polling_interval):
        self.polling_interval = cache_polling_interval

    def listdir(
        self,
        root: t.Union[Path, str],
        impl_fn: t.Callable[[Path], t.Iterable["PkgFile"]],
    ) -> t.Iterable["PkgFile"]:
        root = str(root)
        with self.listdir_lock:
            try:
                return self.listdir_cache[root]
            except KeyError:
                # check to see if we're watching
                with self.watch_lock:
                    if root not in self.watched:
                        self._watch(root)

                v = list(impl_fn(Path(root)))
                self.listdir_cache[root] = v
                return v

    def digest_file(
        self, fpath: str, hash_algo: str, impl_fn: t.Callable[[str, str], str]
    ) -> str:
        with self.digest_lock:
            try:
                cache = self.digest_cache[hash_algo]
            except KeyError:
                cache = self.digest_cache.setdefault(hash_algo, {})

            try:
                return cache[fpath]
            except KeyError:
                root = dirname(fpath)
                with self.watch_lock:
                    if root not in self.watched:
                        self._watch(root)

            # TODO: move this outside of the lock... but there's not a good
            #       way to do this without a race condition if the file
            #       gets modified
            v = impl_fn(fpath, hash_algo)
            cache[fpath] = v
            return v

    def _watch(self, root: str):
        if CacheManager.root_is_nfs(root):
            if not self.polling:
                self.polling = True
                self.observer.stop()
                # See https://github.com/gorakhargosh/watchdog/issues/504#issuecomment-449643137
                # We need to use a PollingObserver if we are on an NFS volume
                self.observer = PollingObserver(timeout=self.polling_interval)
                for already_watched_root in self.watched:
                    self.observer.schedule(
                        _EventHandler(self, already_watched_root),
                        already_watched_root,
                        recursive=True,
                    )
                self.observer.start()
        self.observer.schedule(_EventHandler(self, root), root, recursive=True)
        self.watched.add(root)

    def handle_cache_event(self, root: t.Union[Path, str], event):
        if event.event_type == "modified":
            return
        with self.listdir_lock:
            if hasattr(event, "dest_path"):
                event_dest_pkg = CacheManager.get_pkgfile_for_path(event.dest_path, root)
            event_pkg = CacheManager.get_pkgfile_for_path(event.src_path, root)
            if event.event_type == "created":
                self.listdir_cache[root].append(event_pkg)
            elif event.event_type == "deleted":
                for index, cached_path in enumerate(self.listdir_cache[root]):
                    if cached_path.fn == event_pkg.fn:
                        del self.listdir_cache[root][index]
                        break
            elif event.event_type == "moved":
                for index, cached_path in enumerate(self.listdir_cache[root]):
                    if cached_path.fn == event_pkg.fn:
                        del self.listdir_cache[root][index]
                        self.listdir_cache[root].append(event_dest_pkg)
                        break


class _EventHandler:
    def __init__(self, cache: CacheManager, root: str):
        self.cache = cache
        self.root = root

    def dispatch(self, event):
        """Called by watchdog observer"""
        cache = self.cache

        # Don't care about directory events
        if event.is_directory:
            return

        cache.handle_cache_event(self.root, event)

        # Digests are more expensive: invalidate specific paths
        paths = []

        if event.event_type == "moved":
            paths.append(event.src_path)
            paths.append(event.dest_path)
        else:
            paths.append(event.src_path)

        with cache.digest_lock:
            for _, subcache in cache.digest_cache.items():
                for path in paths:
                    subcache.pop(path, None)
