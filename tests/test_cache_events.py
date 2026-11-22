from pathlib import Path

import pytest

from pypiserver.cache import CacheManager, _EventHandler

watchdog_events = pytest.importorskip("watchdog.events")


@pytest.fixture
def cache() -> CacheManager:
    manager = CacheManager()
    try:
        yield manager
    finally:
        manager.observer.stop()
        manager.observer.join()


def _prime(cache: CacheManager, root: str) -> list:
    return cache.listdir(root, lambda _path: [])


def test_opened_event_keeps_listdir_cache(
    cache: CacheManager, tmp_path: Path
) -> None:
    root = str(tmp_path)
    primed = _prime(cache, root)
    handler = _EventHandler(cache, root)

    handler.dispatch(watchdog_events.FileOpenedEvent(root + "/pkg-1.0.zip"))

    assert cache.listdir(root, lambda _path: []) is primed


def test_closed_event_keeps_listdir_cache(
    cache: CacheManager, tmp_path: Path
) -> None:
    root = str(tmp_path)
    primed = _prime(cache, root)
    handler = _EventHandler(cache, root)

    handler.dispatch(watchdog_events.FileClosedEvent(root + "/pkg-1.0.zip"))

    assert cache.listdir(root, lambda _path: []) is primed


def test_modified_event_invalidates_listdir_cache(
    cache: CacheManager, tmp_path: Path
) -> None:
    root = str(tmp_path)
    _prime(cache, root)
    handler = _EventHandler(cache, root)

    handler.dispatch(watchdog_events.FileModifiedEvent(root + "/pkg-1.0.zip"))

    assert root not in cache.listdir_cache


def test_moved_event_invalidates_and_drops_digest(
    cache: CacheManager, tmp_path: Path
) -> None:
    root = str(tmp_path)
    src = root + "/pkg-1.0.zip"
    dest = root + "/pkg-2.0.zip"
    _prime(cache, root)
    with cache.digest_lock:
        cache.digest_cache.setdefault("sha256", {})[src] = "sha256=old"
        cache.digest_cache["sha256"][dest] = "sha256=old"

    handler = _EventHandler(cache, root)
    handler.dispatch(watchdog_events.FileMovedEvent(src, dest))

    assert root not in cache.listdir_cache
    assert cache.digest_cache["sha256"] == {}
