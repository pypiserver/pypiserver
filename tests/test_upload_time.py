from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path

from pypiserver.upload_time import (
    SIDECAR_NAME,
    fallback_upload_time,
    format_upload_time,
    load_upload_times,
    normalize_upload_time_key,
    parse_upload_time,
    save_upload_times,
)


def test_normalize_upload_time_key_uses_root_relative_unix_style(tmp_path):
    package = tmp_path / "nested" / "pkg-1.0.tar.gz"
    package.parent.mkdir()
    package.touch()

    expected_key = "nested/pkg-1.0.tar.gz"
    assert normalize_upload_time_key(tmp_path, package) == expected_key


def test_format_upload_time_uses_utc_z_suffix():
    value = datetime(2026, 4, 3, 10, 11, 12, 345678, tzinfo=UTC)

    assert format_upload_time(value) == "2026-04-03T10:11:12.345678Z"


def test_parse_upload_time_supports_utc_z_suffix():
    parsed = parse_upload_time("2026-04-03T10:11:12.345678Z")

    assert parsed == datetime(2026, 4, 3, 10, 11, 12, 345678, tzinfo=UTC)


def test_load_upload_times_returns_empty_for_missing_sidecar(tmp_path):
    assert load_upload_times(tmp_path) == {}


def test_load_upload_times_returns_empty_and_logs_warning_for_corrupt_json(
    tmp_path,
    caplog,
):
    (tmp_path / SIDECAR_NAME).write_text("{not-json", encoding="utf-8")

    with caplog.at_level(logging.WARNING):
        result = load_upload_times(tmp_path)

    assert result == {}
    assert any(SIDECAR_NAME in record.message for record in caplog.records)


def test_save_upload_times_writes_atomic_sidecar_with_formatted_timestamps(
    tmp_path,
):
    package = tmp_path / "subdir" / "pkg-1.0.tar.gz"
    package.parent.mkdir()
    package.touch()
    metadata = {
        normalize_upload_time_key(tmp_path, package): datetime(
            2026,
            4,
            3,
            10,
            11,
            12,
            345678,
            tzinfo=UTC,
        )
    }

    save_upload_times(tmp_path, metadata)

    sidecar_path = tmp_path / SIDECAR_NAME
    assert sidecar_path.exists()
    assert sorted(path.name for path in tmp_path.iterdir()) == [
        SIDECAR_NAME,
        "subdir",
    ]
    assert json.loads(sidecar_path.read_text(encoding="utf-8")) == {
        "subdir/pkg-1.0.tar.gz": "2026-04-03T10:11:12.345678Z"
    }


def test_load_upload_times_parses_saved_timestamps(tmp_path):
    sidecar_path = tmp_path / SIDECAR_NAME
    sidecar_path.write_text(
        json.dumps({"pkg-1.0.tar.gz": "2026-04-03T10:11:12.345678Z"}),
        encoding="utf-8",
    )

    assert load_upload_times(tmp_path) == {
        "pkg-1.0.tar.gz": datetime(
            2026,
            4,
            3,
            10,
            11,
            12,
            345678,
            tzinfo=UTC,
        )
    }


def test_fallback_upload_time_uses_file_mtime_as_utc_datetime(tmp_path):
    package = tmp_path / "pkg-1.0.tar.gz"
    package.touch()
    expected = datetime(2026, 4, 3, 10, 11, 12, 345678, tzinfo=UTC)
    timestamp = expected.timestamp()
    package.touch()
    package.chmod(0o644)
    import os

    os.utime(package, (timestamp, timestamp))

    assert fallback_upload_time(package) == expected
