from __future__ import annotations

import json
import logging
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path


logger = logging.getLogger(__name__)

SIDECAR_NAME = ".pypiserver-upload-times.json"


def sidecar_path(root: Path) -> Path:
    return Path(root) / SIDECAR_NAME


def normalize_upload_time_key(root: Path, package_path: Path) -> str:
    resolved_package = Path(package_path).resolve()
    resolved_root = Path(root).resolve()
    return resolved_package.relative_to(resolved_root).as_posix()


def format_upload_time(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def parse_upload_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


def load_upload_times(root: Path) -> dict[str, datetime]:
    path = sidecar_path(root)
    if not path.exists():
        return {}

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("sidecar metadata must be a JSON object")
        parsed = {}
        for key, value in raw.items():
            parsed[str(key)] = parse_upload_time(str(value))
        return parsed
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        logger.warning(
            "Failed to read upload-time metadata from %s: %s",
            path,
            exc,
        )
        return {}


def save_upload_times(root: Path, metadata: dict[str, datetime]) -> None:
    root = Path(root)
    path = sidecar_path(root)
    formatted = {}
    for key, value in sorted(metadata.items()):
        formatted[key] = format_upload_time(value)
    serialized = json.dumps(
        formatted,
        indent=2,
        sort_keys=True,
    )

    fd, tmp_name = tempfile.mkstemp(
        prefix=f"{SIDECAR_NAME}.",
        dir=root,
        text=True,
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(serialized)
            fh.write("\n")
        os.replace(tmp_name, path)
    except Exception:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass
        raise


def fallback_upload_time(package_path: Path) -> datetime:
    return datetime.fromtimestamp(Path(package_path).stat().st_mtime, tz=UTC)
