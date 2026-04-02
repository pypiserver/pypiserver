import io
import os
import typing as t
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from pypiserver.backend import (
    CachingFileBackend,
    PkgFile,
    SimpleFileBackend,
    listdir,
)
from pypiserver.cache import CacheManager
from pypiserver.config import _ConfigCommon
from pypiserver.upload_time import load_upload_times, save_upload_times


def create_path(root: Path, path: Path):
    if path.is_absolute():
        msg = "Only test using relative paths to prevent leaking outside "
        msg += "test environment"
        raise ValueError(msg)
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


def test_listdir_uses_sidecar_upload_time_when_present(tmp_path):
    package_path = tmp_path / "demo-1.0.tar.gz"
    package_path.touch()
    expected = datetime(2026, 4, 3, 10, 11, 12, 345678, tzinfo=UTC)
    save_upload_times(tmp_path, {"demo-1.0.tar.gz": expected})

    package = list(listdir(tmp_path))[0]

    assert package.upload_time == expected


def test_listdir_falls_back_to_file_mtime_when_sidecar_metadata_missing(
    tmp_path,
):
    package_path = tmp_path / "demo-1.0.tar.gz"
    package_path.touch()
    expected = datetime(2026, 4, 3, 10, 11, 12, 345678, tzinfo=UTC)
    timestamp = expected.timestamp()
    os.utime(package_path, (timestamp, timestamp))

    package = list(listdir(tmp_path))[0]

    assert package.upload_time == expected


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


def make_backend_config(root: Path):
    return t.cast(_ConfigCommon, SimpleNamespace(hash_algo=None, roots=[root]))


def make_pkgfile(root: Path, relfn: str) -> PkgFile:
    filename = root / relfn
    return PkgFile(
        pkgname="demo",
        version="1.0",
        fn=str(filename),
        root=str(root),
        relfn=relfn,
    )


def test_simple_backend_add_package_persists_upload_time_metadata(tmp_path):
    backend = SimpleFileBackend(make_backend_config(tmp_path))

    backend.add_package("demo-1.0.tar.gz", io.BytesIO(b"payload"))

    assert (tmp_path / "demo-1.0.tar.gz").read_bytes() == b"payload"
    metadata = load_upload_times(tmp_path)
    assert set(metadata) == {"demo-1.0.tar.gz"}
    delta = metadata["demo-1.0.tar.gz"] - datetime.now(UTC)
    age_seconds = delta.total_seconds()
    assert abs(age_seconds) < 2


def test_simple_backend_add_package_refreshes_upload_time_on_overwrite(
    tmp_path,
):
    backend = SimpleFileBackend(make_backend_config(tmp_path))
    upload_times_path = tmp_path / ".pypiserver-upload-times.json"

    backend.add_package("demo-1.0.tar.gz", io.BytesIO(b"first"))
    first_upload_time = load_upload_times(tmp_path)["demo-1.0.tar.gz"]
    initial_sidecar_mtime = upload_times_path.stat().st_mtime_ns

    backend.add_package("demo-1.0.tar.gz", io.BytesIO(b"second"))

    assert (tmp_path / "demo-1.0.tar.gz").read_bytes() == b"second"
    assert load_upload_times(tmp_path)["demo-1.0.tar.gz"] > first_upload_time
    assert upload_times_path.stat().st_mtime_ns >= initial_sidecar_mtime


def test_simple_backend_remove_package_deletes_upload_time_metadata(tmp_path):
    backend = SimpleFileBackend(make_backend_config(tmp_path))
    backend.add_package("demo-1.0.tar.gz", io.BytesIO(b"payload"))

    backend.remove_package(make_pkgfile(tmp_path, "demo-1.0.tar.gz"))

    assert not (tmp_path / "demo-1.0.tar.gz").exists()
    assert load_upload_times(tmp_path) == {}


def test_simple_backend_remove_package_normalizes_windows_style_relfn(tmp_path):
    backend = SimpleFileBackend(make_backend_config(tmp_path))
    package_path = tmp_path / "nested" / "demo-1.0.tar.gz"
    package_path.parent.mkdir(parents=True)
    package_path.write_bytes(b"payload")
    save_upload_times(
        tmp_path,
        {"nested/demo-1.0.tar.gz": datetime(2026, 4, 3, tzinfo=UTC)},
    )

    backend.remove_package(
        PkgFile(
            pkgname="demo",
            version="1.0",
            fn=str(package_path),
            root=str(tmp_path),
            relfn="nested\\demo-1.0.tar.gz",
        )
    )

    assert not package_path.exists()
    assert load_upload_times(tmp_path) == {}


class CacheManagerSpy:
    def __init__(self):
        self.invalidated_roots = []

    def invalidate_root_cache(self, root):
        self.invalidated_roots.append(Path(root))

    def listdir(self, root, impl):
        return impl(root)

    def digest_file(self, fpath, hash_algo, impl_fn):
        return impl_fn(fpath, hash_algo)


def test_caching_backend_add_and_remove_update_metadata_and_invalidate_cache(
    tmp_path,
):
    cache_manager = CacheManagerSpy()
    backend = CachingFileBackend(
        make_backend_config(tmp_path),
        cache_manager=t.cast(CacheManager, cache_manager),
    )

    backend.add_package("demo-1.0.tar.gz", io.BytesIO(b"payload"))
    assert "demo-1.0.tar.gz" in load_upload_times(tmp_path)
    assert cache_manager.invalidated_roots == [tmp_path]

    backend.remove_package(make_pkgfile(tmp_path, "demo-1.0.tar.gz"))

    assert load_upload_times(tmp_path) == {}
    assert cache_manager.invalidated_roots == [tmp_path, tmp_path]
