from pathlib import Path

import pytest

from pypiserver.backend import listdir


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
