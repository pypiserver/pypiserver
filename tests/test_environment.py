import pytest


def test_default_bottle_memfile(monkeypatch):
    monkeypatch.delenv(
        "PYPISERVER_BOTTLE_MEMFILE_MAX_OVERRIDE_BYTES",
        raising=False,
    )

    from pypiserver.environment import Environment

    assert (
        Environment.PYPISERVER_BOTTLE_MEMFILE_MAX_OVERRIDE_BYTES == 102400
    ), "expected default 100 kb value"


def test_override_bottle_memfile(monkeypatch):
    value_100_mb = (2**20) * 100
    monkeypatch.setenv(
        "PYPISERVER_BOTTLE_MEMFILE_MAX_OVERRIDE_BYTES",
        str(value_100_mb),
    )

    from pypiserver.environment import Environment

    assert (
        Environment.PYPISERVER_BOTTLE_MEMFILE_MAX_OVERRIDE_BYTES == value_100_mb
    ), "expected default 100 kb value"
