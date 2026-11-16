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


def test_listdir_marks_yanked_package_with_reason(tmp_path):
    create_path(tmp_path, Path("pkg-1.0.zip"))
    (tmp_path / "pkg-1.0.zip.yanked").write_text("  broken build\n")

    (pkg,) = listdir(tmp_path)
    assert pkg.yanked == "broken build"


def test_listdir_marks_yanked_package_without_reason(tmp_path):
    create_path(tmp_path, Path("some/nested/pkg-1.0.zip"))
    create_path(tmp_path, Path("some/nested/pkg-1.0.zip.yanked"))

    (pkg,) = listdir(tmp_path)
    assert pkg.yanked == ""


def test_listdir_doesnt_yank_other_packages(tmp_path):
    create_path(tmp_path, Path("pkg-1.0.zip"))
    create_path(tmp_path, Path("pkg-1.1.zip"))
    create_path(tmp_path, Path("pkg-1.0.zip.yanked"))

    yanked = {pkg.version: pkg.yanked for pkg in listdir(tmp_path)}
    assert yanked == {"1.0": "", "1.1": None}


@pytest.mark.parametrize(
    "path_name",
    ["pkg-1.0.zip.yanked", "pkg-1.0-py3.8.egg.yanked", "orphan-1.0.zip.yanked"],
)
def test_listdir_doesnt_list_yank_markers(tmp_path, path_name):
    create_path(tmp_path, Path(path_name))
    assert not list(listdir(tmp_path))
