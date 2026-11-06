import os
import sys
from pathlib import Path

import pytest

from pypiserver.backend import CachingFileBackend, SimpleFileBackend, listdir
from pypiserver.config import Config


def create_path(root: Path, path: Path):
    if path.is_absolute():
        raise ValueError(
            "Only test using relative paths"
            " to prevent leaking outside test environment"
        )
    fullpath = root / path
    if not fullpath.parent.exists():
        fullpath.parent.mkdir(parents=True)
    fullpath.touch()


valid_paths = ["direct-in-root.zip", "some/nested/pkg.zip"]


@pytest.mark.parametrize("path_name", valid_paths)
def test_listdir_generates_pkgfile_for_valid_package(tmp_path, path_name):
    path = Path(path_name)
    create_path(tmp_path, path)
    assert len(list(listdir(tmp_path))) == 1


invalid_paths = [
    ".hidden-pkg.zip",
    ".hidden/dir/pkg.zip",
    "in/between/.hidden/pkg.zip",
    "invalid-wheel.whl",
]


@pytest.mark.parametrize("path_name", invalid_paths)
def test_listdir_doesnt_generate_pkgfile_for_invalid_file(tmp_path, path_name):
    path = Path(path_name)
    create_path(tmp_path, path)
    assert not list(listdir(tmp_path))


@pytest.mark.skipif(sys.platform == "win32", reason="symlink privileges")
def test_listdir_follows_symlinked_directories_when_enabled(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    target = tmp_path / "target"
    target.mkdir()
    (target / "direct-in-root.zip").touch()
    (root / "linked").symlink_to(target, target_is_directory=True)

    assert not list(listdir(root))
    followed = list(listdir(root, follow_links=True))
    assert len(followed) == 1


@pytest.mark.skipif(sys.platform == "win32", reason="symlink privileges")
def test_listdir_follow_links_does_not_loop_on_cycles(tmp_path):
    (tmp_path / "direct-in-root.zip").touch()
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "loop").symlink_to(tmp_path, target_is_directory=True)

    assert len(list(listdir(tmp_path, follow_links=True))) == 1


@pytest.mark.skipif(sys.platform == "win32", reason="symlink privileges")
def test_simple_backend_follow_links_option(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    target = tmp_path / "target"
    target.mkdir()
    (target / "direct-in-root.zip").touch()
    (root / "linked").symlink_to(target, target_is_directory=True)

    default = SimpleFileBackend(Config.default_with_overrides(roots=[root]))
    assert not list(default.get_all_packages())
    assert default.exists("direct-in-root.zip") is False

    followed = SimpleFileBackend(
        Config.default_with_overrides(roots=[root], follow_links=True)
    )
    assert len(list(followed.get_all_packages())) == 1
    assert followed.exists("direct-in-root.zip") is True


@pytest.mark.skipif(sys.platform == "win32", reason="symlink privileges")
def test_caching_backend_follow_links_option(tmp_path):
    pytest.importorskip("watchdog")
    root = tmp_path / "root"
    root.mkdir()
    target = tmp_path / "target"
    target.mkdir()
    (target / "direct-in-root.zip").touch()
    (root / "linked").symlink_to(target, target_is_directory=True)

    backend = CachingFileBackend(
        Config.default_with_overrides(roots=[root], follow_links=True)
    )
    try:
        assert len(list(backend.get_all_packages())) == 1
    finally:
        backend.cache_manager.observer.stop()
        backend.cache_manager.observer.join()


@pytest.mark.parametrize("follow_links", [False, True])
def test_cache_manager_observer_matches_follow_links(follow_links):
    pytest.importorskip("watchdog")
    from watchdog.observers import Observer
    from watchdog.observers.polling import PollingObserver

    from pypiserver.cache import CacheManager

    cache = CacheManager(follow_links=follow_links)
    try:
        expected = PollingObserver if follow_links else Observer
        assert isinstance(cache.observer, expected)
    finally:
        cache.observer.stop()
        cache.observer.join()


def test_cache_manager_without_watchdog(monkeypatch):
    import builtins
    import importlib

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "watchdog" or name.startswith("watchdog."):
            raise ImportError(name)
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    sys.modules.pop("pypiserver.cache", None)
    try:
        cache = importlib.import_module("pypiserver.cache")
        assert cache.ENABLE_CACHING is False
        with pytest.raises(RuntimeError):
            cache.CacheManager()
    finally:
        monkeypatch.undo()
        sys.modules.pop("pypiserver.cache", None)
        importlib.import_module("pypiserver.cache")
