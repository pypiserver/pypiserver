import sys
from collections.abc import Callable
from pathlib import Path
from queue import Queue

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


def test_closed_no_write_event_keeps_listdir_cache(
    cache: CacheManager, tmp_path: Path
) -> None:
    root = str(tmp_path)
    primed = _prime(cache, root)
    handler = _EventHandler(cache, root)

    handler.dispatch(
        watchdog_events.FileClosedNoWriteEvent(root + "/pkg-1.0.zip")
    )

    assert cache.listdir(root, lambda _path: []) is primed


def test_reading_a_file_keeps_listdir_and_digest_cache(
    cache: CacheManager, tmp_path: Path
) -> None:
    root = str(tmp_path)
    path = root + "/pkg-1.0.zip"
    primed = _prime(cache, root)
    with cache.digest_lock:
        cache.digest_cache.setdefault("sha256", {})[path] = "sha256=digest"

    handler = _EventHandler(cache, root)
    for event in (
        watchdog_events.FileOpenedEvent(path),
        watchdog_events.FileClosedNoWriteEvent(path),
    ):
        handler.dispatch(event)

    assert cache.listdir(root, lambda _path: []) is primed
    assert cache.digest_cache["sha256"][path] == "sha256=digest"


def test_closed_event_invalidates_listdir_and_digest_cache(
    cache: CacheManager, tmp_path: Path
) -> None:
    # "closed" is IN_CLOSE_WRITE: the file was open for writing.
    root = str(tmp_path)
    path = str(tmp_path / "pkg-1.0.zip")
    _prime(cache, root)
    cache.digest_file(path, "sha256", lambda _path, _algo: "digest")
    handler = _EventHandler(cache, root)

    handler.dispatch(watchdog_events.FileClosedEvent(path))

    assert root not in cache.listdir_cache
    assert path not in cache.digest_cache["sha256"]


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


@pytest.mark.skipif(
    not sys.platform.startswith("linux"),
    reason="IN_OPEN / IN_CLOSE_NOWRITE are inotify-only events",
)
def test_real_observer_keeps_caches_on_read_and_invalidates_on_write(
    cache: CacheManager, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from watchdog.events import FileSystemEvent

    root = str(tmp_path)
    pkg = tmp_path / "pkg-1.0.zip"
    pkg.write_bytes(b"payload" * 100)
    path = str(pkg)
    closes: Queue[str] = Queue()
    dispatch: Callable[[_EventHandler, FileSystemEvent], None] = (
        _EventHandler.dispatch
    )

    def record_close(handler: _EventHandler, event: FileSystemEvent) -> None:
        dispatch(handler, event)
        if event.src_path == path and event.event_type in {
            "closed_no_write",
            "closed",
        }:
            closes.put(event.event_type)

    monkeypatch.setattr(_EventHandler, "dispatch", record_close)

    # Priming also schedules the watch, so the write above raises no event.
    primed = _prime(cache, root)
    cache.digest_file(path, "sha256", lambda _path, _algo: "digest")

    pkg.read_bytes()
    assert closes.get(timeout=5) == "closed_no_write"
    assert cache.listdir_cache[root] is primed
    assert cache.digest_cache["sha256"][path] == "digest"

    pkg.write_bytes(b"updated payload")
    assert closes.get(timeout=5) == "closed"
    assert root not in cache.listdir_cache
    assert path not in cache.digest_cache["sha256"]
