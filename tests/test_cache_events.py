import sys
import time
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


def test_closed_event_invalidates_listdir_cache(
    cache: CacheManager, tmp_path: Path
) -> None:
    # "closed" is IN_CLOSE_WRITE: the file was open for writing.
    root = str(tmp_path)
    _prime(cache, root)
    handler = _EventHandler(cache, root)

    handler.dispatch(watchdog_events.FileClosedEvent(root + "/pkg-1.0.zip"))

    assert root not in cache.listdir_cache


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
def test_download_keeps_caches_with_a_real_observer(
    cache: CacheManager, tmp_path: Path
) -> None:
    root = str(tmp_path)
    pkg = tmp_path / "pkg-1.0.zip"
    pkg.write_bytes(b"payload" * 100)

    # Priming also schedules the watch, so the write above raises no event.
    cache.listdir(root, lambda _path: [])
    cache.digest_file(str(pkg), "sha256", lambda _path, _algo: "digest")

    # What a download does: open, read, close.
    pkg.read_bytes()
    time.sleep(0.5)  # give inotify time to deliver opened / closed_no_write

    assert root in cache.listdir_cache
    assert cache.digest_cache["sha256"][str(pkg)] == "digest"
