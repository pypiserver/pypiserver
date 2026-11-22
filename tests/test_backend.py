from io import BytesIO
from pathlib import Path

import pytest

from pypiserver.backend import listdir, write_file


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


def _write_with_interrupted_stream(destination: Path) -> None:
    class FailingStream(BytesIO):
        reads = 0

        def read(self, size: int | None = -1) -> bytes:
            self.reads += 1
            if self.reads == 2:
                raise OSError("boom")
            return super().read(size)

    with FailingStream(b"x" * ((2**20) + 2)) as stream:
        stream.seek(1)
        with pytest.raises(OSError, match="^boom$"):
            write_file(stream, destination)
        assert stream.tell() == 1


def test_write_file_creates_destination(tmp_path: Path) -> None:
    destination = tmp_path / "pkg-1.0.zip"
    write_file(BytesIO(b"abc"), destination)

    assert destination.read_bytes() == b"abc"


def test_write_file_restores_stream_position(tmp_path: Path) -> None:
    stream = BytesIO(b"abcd")
    stream.read(2)
    destination = tmp_path / "pkg-1.0.zip"
    write_file(stream, destination)

    assert stream.tell() == 2
    assert destination.read_bytes() == b"cd"


def test_write_file_failure_leaves_no_partial(tmp_path: Path) -> None:
    destination = tmp_path / "pkg-1.0.zip"
    _write_with_interrupted_stream(destination)

    assert not destination.exists()
    assert list(tmp_path.iterdir()) == []


def test_write_file_failure_keeps_existing_content(tmp_path: Path) -> None:
    destination = tmp_path / "pkg-1.0.zip"
    destination.write_bytes(b"old")
    _write_with_interrupted_stream(destination)

    assert destination.read_bytes() == b"old"
    assert list(tmp_path.iterdir()) == [destination]


def test_write_file_overwrites_atomically(tmp_path: Path) -> None:
    destination = tmp_path / "pkg-1.0.zip"
    destination.write_bytes(b"old")
    write_file(BytesIO(b"new"), destination)

    assert destination.read_bytes() == b"new"
    assert list(tmp_path.iterdir()) == [destination]


def test_write_file_temp_name_is_hidden(tmp_path: Path) -> None:
    names_during_upload: set[str] = set()
    packages_during_upload: list[str | None] = []

    class ObservedStream(BytesIO):
        def read(self, size: int | None = -1) -> bytes:
            names_during_upload.update(path.name for path in tmp_path.iterdir())
            packages_during_upload.extend(
                pkg.relfn_unix for pkg in listdir(tmp_path)
            )
            return super().read(size)

    destination = tmp_path / "pkg-1.0.zip"
    write_file(ObservedStream(b"abc"), destination)

    (temp_name,) = names_during_upload
    assert temp_name.startswith(".")
    assert temp_name.endswith(".part")
    assert packages_during_upload == []
    assert list(tmp_path.iterdir()) == [destination]
