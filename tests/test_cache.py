import threading
from types import SimpleNamespace

from pypiserver.cache import _EventHandler


class StubCache:
    def __init__(self, root, package):
        self.listdir_cache = {root: [package]}
        self.digest_cache = {"sha256": {package: "digest"}}
        self.listdir_lock = threading.Lock()
        self.digest_lock = threading.Lock()

    def invalidate_root_cache(self, root):
        with self.listdir_lock:
            self.listdir_cache.pop(root, None)


def test_opened_event_does_not_invalidate_caches(tmp_path):
    root = str(tmp_path)
    package = str(tmp_path / "package.whl")
    cache = StubCache(root, package)

    event = SimpleNamespace(
        event_type="opened", is_directory=False, src_path=package
    )
    _EventHandler(cache, root).dispatch(event)

    assert cache.listdir_cache == {root: [package]}
    assert cache.digest_cache == {"sha256": {package: "digest"}}


def test_modified_event_invalidates_caches(tmp_path):
    root = str(tmp_path)
    package = str(tmp_path / "package.whl")
    cache = StubCache(root, package)

    event = SimpleNamespace(
        event_type="modified", is_directory=False, src_path=package
    )
    _EventHandler(cache, root).dispatch(event)

    assert cache.listdir_cache == {}
    assert cache.digest_cache == {"sha256": {}}
