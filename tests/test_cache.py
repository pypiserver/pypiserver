import threading
import time
from collections.abc import Callable, Iterator
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from typing import cast

import pytest

from pypiserver.cache import CacheManager, _EventHandler

watchdog_events = pytest.importorskip("watchdog.events")


@pytest.fixture
def cache() -> Iterator[CacheManager]:
    manager = cast(Callable[[], CacheManager], CacheManager)()
    try:
        yield manager
    finally:
        manager.observer.stop()
        manager.observer.join()


def slow_impl(fpath: str, hash_algo: str) -> str:
    time.sleep(0.05)
    return f"{hash_algo}={Path(fpath).stem}"


def test_digest_same_file_computed_once(
    cache: CacheManager, tmp_path: Path
) -> None:
    fpath = str(tmp_path / "x.whl")
    ready = threading.Barrier(8, timeout=5)
    calls = []
    calls_lock = threading.Lock()

    def counted_impl(path: str, algo: str) -> str:
        with calls_lock:
            calls.append(path)
        return slow_impl(path, algo)

    def lookup(path: str) -> str:
        ready.wait()
        return cache.digest_file(path, "sha256", counted_impl)

    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(lookup, [fpath] * 8))

    assert calls == [fpath]
    assert results == ["sha256=x"] * 8


def test_digest_different_files_run_concurrently(
    cache: CacheManager, tmp_path: Path
) -> None:
    paths = [str(tmp_path / f"pkg{i}.whl") for i in range(6)]
    ready = threading.Barrier(7, timeout=5)

    def lookup(path: str) -> str:
        ready.wait()
        return cache.digest_file(path, "sha256", slow_impl)

    with ThreadPoolExecutor(max_workers=6) as executor:
        jobs = [executor.submit(lookup, path) for path in paths]
        start = time.perf_counter()
        ready.wait()
        results = [job.result() for job in jobs]
        elapsed = time.perf_counter() - start

    print(f"6 files × 50 ms: {elapsed * 1000:.3f} ms")
    assert results == [f"sha256=pkg{i}" for i in range(6)]
    assert elapsed < 0.15


def test_digest_cache_hit_skips_impl(
    cache: CacheManager, tmp_path: Path
) -> None:
    fpath = str(tmp_path / "x.whl")
    calls = []

    def impl(path: str, algo: str) -> str:
        calls.append((path, algo))
        return "sha256=x"

    assert cache.digest_file(fpath, "sha256", impl) == "sha256=x"
    assert cache.digest_file(fpath, "sha256", impl) == "sha256=x"
    assert calls == [(fpath, "sha256")]


def test_digest_invalidated_by_event(
    cache: CacheManager, tmp_path: Path
) -> None:
    fpath = str(tmp_path / "x.whl")
    calls = []

    def impl(path: str, algo: str) -> str:
        calls.append((path, algo))
        return f"sha256={len(calls)}"

    assert cache.digest_file(fpath, "sha256", impl) == "sha256=1"
    handler = _EventHandler(cache, str(tmp_path))
    moved = watchdog_events.FileMovedEvent(fpath, str(tmp_path / "y.whl"))
    cast(Callable[[object], None], handler.dispatch)(moved)
    assert cache.digest_file(fpath, "sha256", impl) == "sha256=2"
    assert calls == [(fpath, "sha256")] * 2


def test_digest_lock_released_on_exception(
    cache: CacheManager, tmp_path: Path
) -> None:
    fpath = str(tmp_path / "x.whl")

    def fail(path: str, algo: str) -> str:
        raise RuntimeError("hash failed")

    with pytest.raises(RuntimeError, match="hash failed"):
        cache.digest_file(fpath, "sha256", fail)

    result: Future[str] = Future()
    finished = threading.Event()

    def retry() -> None:
        try:
            result.set_result(cache.digest_file(fpath, "sha256", slow_impl))
        except Exception as error:
            result.set_exception(error)
        finally:
            finished.set()

    worker = threading.Thread(target=retry, daemon=True)
    timer = threading.Timer(5, finished.set)
    timer.start()
    try:
        worker.start()
        finished.wait()
        assert result.done(), "digest retry blocked after an exception"
        assert result.result() == "sha256=x"
    finally:
        timer.cancel()
        timer.join()
