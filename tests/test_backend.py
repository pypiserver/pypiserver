import io
import os
import threading
import typing as t
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace

import pytest

from pypiserver.backend import (
    ENABLE_CACHING,
    Backend,
    CachingFileBackend,
    SimpleFileBackend,
    listdir,
)
from pypiserver.config import Configuration
from pypiserver.core import PkgFile


@pytest.fixture
def backend_config(tmp_path: Path) -> Configuration:
    return t.cast(
        Configuration, SimpleNamespace(hash_algo=None, roots=[tmp_path])
    )


@pytest.fixture
def simple_backend(backend_config: Configuration) -> SimpleFileBackend:
    return SimpleFileBackend(backend_config)


@pytest.fixture
def caching_backend(tmp_path: Path) -> t.Iterator[CachingFileBackend]:
    if not ENABLE_CACHING:
        pytest.skip("watchdog is not installed, so caching is disabled")
    cached_root = tmp_path / "cached"
    cached_root.mkdir()
    config = t.cast(
        Configuration, SimpleNamespace(hash_algo=None, roots=[cached_root])
    )
    backend = CachingFileBackend(config)
    try:
        yield backend
    finally:
        backend.cache_manager.observer.stop()
        backend.cache_manager.observer.join()


@pytest.fixture
def write_backends(
    simple_backend: SimpleFileBackend, tmp_path: Path
) -> t.Iterator[list[SimpleFileBackend]]:
    if not ENABLE_CACHING:
        yield [simple_backend]
        return

    cached_root = tmp_path / "cached"
    cached_root.mkdir()
    config = t.cast(
        Configuration, SimpleNamespace(hash_algo=None, roots=[cached_root])
    )
    cached = CachingFileBackend(config)
    try:
        yield [simple_backend, cached]
    finally:
        cached.cache_manager.observer.stop()
        cached.cache_manager.observer.join()


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


def test_index_project_lookup(caching_backend: CachingFileBackend) -> None:
    for filename in (
        "foo-1.0.tar.gz",
        "FOO-2.0.tar.gz",
        "bar-1.0.tar.gz",
    ):
        caching_backend.roots[0].joinpath(filename).touch()

    assert len(list(caching_backend.find_project_packages("foo"))) == 2
    assert len(list(caching_backend.find_project_packages("FOO"))) == 2


def test_index_version_lookup(caching_backend: CachingFileBackend) -> None:
    for filename in ("foo-1.0.tar.gz", "foo-2.0.tar.gz"):
        caching_backend.roots[0].joinpath(filename).touch()

    packages = list(caching_backend.find_version("foo", "1.0"))
    assert [pkg.relfn_unix for pkg in packages] == ["foo-1.0.tar.gz"]
    assert list(caching_backend.find_version("foo", "3.0")) == []


def test_index_by_relfn(caching_backend: CachingFileBackend) -> None:
    nested_path = caching_backend.roots[0] / "sub" / "foo-1.0.tar.gz"
    nested_path.parent.mkdir()
    nested_path.touch()
    caching_backend.cache_manager.invalidate_root_cache(
        caching_backend.roots[0]
    )

    matched = caching_backend.get_by_relfn("sub/foo-1.0.tar.gz")
    assert matched is not None and matched.fn == str(nested_path)
    assert caching_backend.get_by_relfn("sub/missing-1.0.tar.gz") is None


def test_index_exists_by_basename(caching_backend: CachingFileBackend) -> None:
    nested_path = caching_backend.roots[0] / "sub" / "foo-1.0.tar.gz"
    nested_path.parent.mkdir()
    nested_path.touch()
    caching_backend.cache_manager.invalidate_root_cache(
        caching_backend.roots[0]
    )

    assert caching_backend.exists("foo-1.0.tar.gz")


def test_index_count_and_projects(caching_backend: CachingFileBackend) -> None:
    for filename in (
        "Foo.Bar-1.0.tar.gz",
        "foo_bar-2.0.tar.gz",
        "other-1.0.tar.gz",
    ):
        caching_backend.roots[0].joinpath(filename).touch()

    assert caching_backend.package_count() == 3
    assert set(caching_backend.get_projects()) == {"foo-bar", "other"}


def test_index_invalidated_on_add(
    write_backends: list[SimpleFileBackend],
) -> None:
    for backend in write_backends:
        root = backend.roots[0]
        assert list(backend.find_project_packages("foo")) == []
        before = root.stat()
        backend.add_package("foo-1.0.tar.gz", io.BytesIO(b"package"))
        os.utime(root, ns=(before.st_atime_ns, before.st_mtime_ns))
        assert len(list(backend.find_project_packages("foo"))) == 1


def test_index_invalidated_on_remove(
    write_backends: list[SimpleFileBackend],
) -> None:
    for backend in write_backends:
        root = backend.roots[0]
        (root / "foo-1.0.tar.gz").touch()
        pkg = list(backend.find_project_packages("foo"))[0]
        before = root.stat()
        backend.remove_package(pkg)
        os.utime(root, ns=(before.st_atime_ns, before.st_mtime_ns))
        assert list(backend.find_project_packages("foo")) == []


def test_index_rebuild_on_generation(
    caching_backend: CachingFileBackend,
) -> None:
    assert list(caching_backend.find_project_packages("foo")) == []
    generation = caching_backend.cache_manager.generation

    caching_backend.roots[0].joinpath("foo-1.0.tar.gz").touch()
    caching_backend.cache_manager.invalidate_root_cache(
        caching_backend.roots[0]
    )

    assert caching_backend._current_index_token() != generation
    assert len(list(caching_backend.find_project_packages("foo"))) == 1


def test_index_token_stable_reuses_snapshot(
    caching_backend: CachingFileBackend,
) -> None:
    assert caching_backend._ensure_index() is caching_backend._ensure_index()


def test_index_thread_safety(caching_backend: CachingFileBackend) -> None:
    for filename in (
        "foo-1.0.tar.gz",
        "foo-2.0.tar.gz",
        "bar-1.0.tar.gz",
    ):
        caching_backend.roots[0].joinpath(filename).touch()

    barrier = threading.Barrier(8)

    def lookup_packages() -> None:
        barrier.wait()
        for _ in range(200):
            assert len(list(caching_backend.find_project_packages("foo"))) == 2

    with ThreadPoolExecutor(max_workers=8) as executor:
        results = [executor.submit(lookup_packages) for _ in range(8)]
        for result in results:
            result.result()


def test_simple_backend_get_all_packages_is_iterable(
    simple_backend: SimpleFileBackend,
) -> None:
    simple_backend.roots[0].joinpath("foo-1.0.tar.gz").touch()

    packages = list(simple_backend.get_all_packages())
    assert len(packages) == 1
    assert all(isinstance(pkg, PkgFile) for pkg in packages)


def test_simple_backend_sees_package_added_to_subdirectory(
    backend_config: Configuration,
) -> None:
    """The plain backend rescans, so a subdirectory drop is visible at once.

    A root mtime token cannot see this write: creating ``sub/`` and the file
    inside it never touches the root's own mtime. Caching the index for this
    backend is exactly why ``/packages/<file>`` 404'd until something bumped
    the root.
    """
    backend = SimpleFileBackend(backend_config)
    root = backend.roots[0]
    assert list(backend.get_all_packages()) == []
    before = os.stat(root).st_mtime_ns

    nested = root / "sub" / "late-1.0.tar.gz"
    nested.parent.mkdir()
    nested.touch()
    os.utime(root, ns=(before, before))

    assert [pkg.relfn_unix for pkg in backend.get_all_packages()] == [
        "sub/late-1.0.tar.gz"
    ]
    assert backend.get_by_relfn("sub/late-1.0.tar.gz") is not None
    assert backend.exists("late-1.0.tar.gz")


def test_simple_backend_digest_reflects_in_place_replace(
    tmp_path: Path,
) -> None:
    """Rescanning also rebuilds the PkgFile, so its memoised digest is fresh."""
    config = t.cast(
        Configuration, SimpleNamespace(hash_algo="sha256", roots=[tmp_path])
    )
    backend = SimpleFileBackend(config)
    path = tmp_path / "foo-1.0.tar.gz"

    path.write_bytes(b"first")
    first_digest = backend.digest(list(backend.get_all_packages())[0])

    path.write_bytes(b"second")
    second_digest = backend.digest(list(backend.get_all_packages())[0])

    assert first_digest is not None
    assert second_digest is not None
    assert first_digest != second_digest


def test_custom_backend_falls_back_to_linear_scan(
    backend_config: Configuration,
) -> None:
    class CustomBackend(Backend):
        def get_all_packages(self) -> t.Iterable[PkgFile]:
            return [package]

        def add_package(self, filename: str, stream: t.BinaryIO) -> None:
            raise NotImplementedError

        def remove_package(self, pkg: PkgFile) -> None:
            raise NotImplementedError

        def exists(self, filename: str) -> bool:
            raise NotImplementedError

    package_path = backend_config.roots[0] / "foo-1.0.tar.gz"
    package_path.touch()
    package = list(listdir(backend_config.roots[0]))[0]
    custom_backend = CustomBackend(backend_config)

    assert custom_backend.get_by_relfn("foo-1.0.tar.gz") is package
