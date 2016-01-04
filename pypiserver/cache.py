
# Dumb cache implementation -- requires watchdog to be installed

# Basically -- cache the results of listdir in memory until something
# gets modified, then invalidate the whole thing


from watchdog.observers import Observer
import threading

class ListdirCache(object):

    def __init__(self):
        self.cache = {}
        self.observer = Observer()
        self.observer.start()

        self.watched = set()
        self.lock = threading.Lock()

    def get(self, root, fn):
        with self.lock:
            try:
                return self.cache[root]
            except KeyError:
                # check to see if we're watching
                if root not in self.watched:
                    self._watch(root)

                v = list(fn(root))
                self.cache[root] = v
                return v

    def _watch(self, root):
        self.watched.add(root)
        self.observer.schedule(_EventHandler(self, root), root, recursive=True)

class _EventHandler(object):

    def __init__(self, lcache, root):
        self.lcache = lcache
        self.root = root

    def dispatch(self, event):
        '''Called by watchdog observer'''
        with self.lcache.lock:
            self.lcache.cache.pop(self.root, None)

listdir_cache = ListdirCache()
