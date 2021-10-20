#
# The cache implementation is only used when the watchdog package
# is installed
#

import platform
from os.path import dirname
from pathlib import Path
from subprocess import call
import typing as t
import threading

try:
    from watchdog.observers import Observer
    from watchdog.observers.polling import PollingObserver

    ENABLE_CACHING = True

except ImportError:

    Observer = None
    PollingObserver = None

    ENABLE_CACHING = False

if t.TYPE_CHECKING:
    from pypiserver.core import PkgFile


class CacheManager:
    """
    A naive cache implementation for listdir and digest_file

    The listdir_cache is just a giant list of PkgFile objects, and
    for simplicity it is invalidated anytime a modification occurs
    within the directory it represents. If we were smarter about
    the way that the listdir data structure were created/stored,
    then we could do more granular invalidation. In practice, this
    is good enough for now.

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
        return "nfs" in call("stat -f -L -c %T {}".format(path)).stdout

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
                self.observer = PollingObserver()
                for already_watched_root in self.watched:
                    self.observer.schedule(
                        _EventHandler(self, already_watched_root),
                        already_watched_root,
                        recursive=True,
                    )
                self.observer.start()
        self.observer.schedule(_EventHandler(self, root), root, recursive=True)
        self.watched.add(root)

    def invalidate_root_cache(self, root: t.Union[Path, str]):
        with self.listdir_lock:
            self.listdir_cache.pop(str(root), None)


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

        # Lazy: just invalidate the whole cache
        cache.invalidate_root_cache(self.root)

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
