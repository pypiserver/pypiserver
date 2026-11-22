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


def test_index_project_lookup(simple_backend: SimpleFileBackend) -> None:
    for filename in (
        "foo-1.0.tar.gz",
        "FOO-2.0.tar.gz",
        "bar-1.0.tar.gz",
    ):
        simple_backend.roots[0].joinpath(filename).touch()

    assert len(list(simple_backend.find_project_packages("foo"))) == 2
    assert len(list(simple_backend.find_project_packages("FOO"))) == 2


def test_index_version_lookup(simple_backend: SimpleFileBackend) -> None:
    for filename in ("foo-1.0.tar.gz", "foo-2.0.tar.gz"):
        simple_backend.roots[0].joinpath(filename).touch()

    packages = list(simple_backend.find_version("foo", "1.0"))
    assert [pkg.relfn_unix for pkg in packages] == ["foo-1.0.tar.gz"]
    assert list(simple_backend.find_version("foo", "3.0")) == []


def test_index_by_relfn(simple_backend: SimpleFileBackend) -> None:
    nested_path = simple_backend.roots[0] / "sub" / "foo-1.0.tar.gz"
    nested_path.parent.mkdir()
    nested_path.touch()

    matched = simple_backend.get_by_relfn("sub/foo-1.0.tar.gz")
    assert matched is not None and matched.fn == str(nested_path)
    assert simple_backend.get_by_relfn("sub/missing-1.0.tar.gz") is None


def test_index_exists_by_basename(simple_backend: SimpleFileBackend) -> None:
    nested_path = simple_backend.roots[0] / "sub" / "foo-1.0.tar.gz"
    nested_path.parent.mkdir()
    nested_path.touch()

    assert simple_backend.exists("foo-1.0.tar.gz")


def test_index_count_and_projects(simple_backend: SimpleFileBackend) -> None:
    for filename in (
        "Foo.Bar-1.0.tar.gz",
        "foo_bar-2.0.tar.gz",
        "other-1.0.tar.gz",
    ):
        simple_backend.roots[0].joinpath(filename).touch()

    assert simple_backend.package_count() == 3
    assert set(simple_backend.get_projects()) == {"foo-bar", "other"}


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


def test_index_rebuild_on_root_mtime(
    simple_backend: SimpleFileBackend,
) -> None:
    assert list(simple_backend.find_project_packages("foo")) == []
    old_mtime = os.stat(simple_backend.roots[0]).st_mtime_ns

    simple_backend.roots[0].joinpath("foo-1.0.tar.gz").touch()
    root_stat = os.stat(simple_backend.roots[0])
    os.utime(
        simple_backend.roots[0],
        ns=(root_stat.st_atime_ns, old_mtime + 1_000_000_000),
    )

    assert simple_backend._current_index_token() != (old_mtime,)
    assert len(list(simple_backend.find_project_packages("foo"))) == 1


def test_index_token_stable_reuses_snapshot(
    simple_backend: SimpleFileBackend,
) -> None:
    assert simple_backend._ensure_index() is simple_backend._ensure_index()


def test_index_thread_safety(simple_backend: SimpleFileBackend) -> None:
    for filename in (
        "foo-1.0.tar.gz",
        "foo-2.0.tar.gz",
        "bar-1.0.tar.gz",
    ):
        simple_backend.roots[0].joinpath(filename).touch()

    barrier = threading.Barrier(8)

    def lookup_packages() -> None:
        barrier.wait()
        for _ in range(200):
            assert len(list(simple_backend.find_project_packages("foo"))) == 2

    with ThreadPoolExecutor(max_workers=8) as executor:
        results = [executor.submit(lookup_packages) for _ in range(8)]
        for result in results:
            result.result()


def test_simple_backend_get_all_packages_is_iterable(
    simple_backend: SimpleFileBackend,
) -> None:
    simple_backend.roots[0].joinpath("foo-1.0.tar.gz").touch()

    packages = simple_backend.get_all_packages()
    assert isinstance(packages, list)
    assert len(packages) == 1
    assert all(isinstance(pkg, PkgFile) for pkg in packages)


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
