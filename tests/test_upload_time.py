from __future__ import annotations

import json
from datetime import UTC, datetime

from pypiserver.upload_time import (
    SIDECAR_NAME,
    fallback_upload_time,
    load_upload_times,
    normalize_upload_time_key,
    save_upload_times,
)


def test_normalize_upload_time_key_uses_root_relative_unix_style(tmp_path):
    package = tmp_path / "nested" / "pkg-1.0.tar.gz"
    package.parent.mkdir()
    package.touch()

    expected = "nested/pkg-1.0.tar.gz"

    assert normalize_upload_time_key(tmp_path, package) == expected


def test_save_and_load_upload_times_round_trip(tmp_path):
    package = tmp_path / "subdir" / "pkg-1.0.tar.gz"
    package.parent.mkdir()
    package.touch()
    expected = datetime(2026, 4, 3, 10, 11, 12, 345678, tzinfo=UTC)

    save_upload_times(
        tmp_path,
        {normalize_upload_time_key(tmp_path, package): expected},
    )

    sidecar_path = tmp_path / SIDECAR_NAME
    assert json.loads(sidecar_path.read_text(encoding="utf-8")) == {
        "subdir/pkg-1.0.tar.gz": "2026-04-03T10:11:12.345678Z"
    }
    assert load_upload_times(tmp_path) == {"subdir/pkg-1.0.tar.gz": expected}


def test_fallback_upload_time_uses_file_mtime_as_utc_datetime(tmp_path):
    package = tmp_path / "pkg-1.0.tar.gz"
    package.touch()
    expected = datetime(2026, 4, 3, 10, 11, 12, 345678, tzinfo=UTC)
    timestamp = expected.timestamp()

    import os

    os.utime(package, (timestamp, timestamp))

    assert fallback_upload_time(package) == expected
