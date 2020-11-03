#
# The cache implementation is only used when the watchdog package
# is installed
#

from os.path import dirname

from watchdog.observers import Observer
import threading


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

    def __init__(self):

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

    def listdir(self, root, impl_fn):
        with self.listdir_lock:
            try:
                return self.listdir_cache[root]
            except KeyError:
                # check to see if we're watching
                with self.watch_lock:
                    if root not in self.watched:
                        self._watch(root)

                v = list(impl_fn(root))
                self.listdir_cache[root] = v
                return v

    def digest_file(self, fpath, hash_algo, impl_fn):
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

    def _watch(self, root):
        self.watched.add(root)
        self.observer.schedule(_EventHandler(self, root), root, recursive=True)


class _EventHandler:
    def __init__(self, cache, root):
        self.cache = cache
        self.root = root

    def dispatch(self, event):
        """Called by watchdog observer"""
        cache = self.cache

        # Don't care about directory events
        if event.is_directory:
            return

        # Lazy: just invalidate the whole cache
        with cache.listdir_lock:
            cache.listdir_cache.pop(self.root, None)

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


cache_manager = CacheManager()
