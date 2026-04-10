import io
import typing as t
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from pypiserver.backend import (
    SimpleFileBackend,
    listdir,
)
from pypiserver.config import _ConfigCommon
from pypiserver.upload_time import load_upload_times


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


def make_backend_config(root: Path):
    return t.cast(_ConfigCommon, SimpleNamespace(hash_algo=None, roots=[root]))


def test_simple_backend_add_package_persists_upload_time_metadata(tmp_path):
    backend = SimpleFileBackend(make_backend_config(tmp_path))

    backend.add_package("demo-1.0.tar.gz", io.BytesIO(b"payload"))

    assert (tmp_path / "demo-1.0.tar.gz").read_bytes() == b"payload"
    metadata = load_upload_times(tmp_path)
    assert set(metadata) == {"demo-1.0.tar.gz"}
    delta = metadata["demo-1.0.tar.gz"] - datetime.now(UTC)
    age_seconds = delta.total_seconds()
    assert abs(age_seconds) < 2
