from importlib import reload

import pytest

import pypiserver.environment as environment


def test_default_bottle_memfile_is_none(monkeypatch):
    monkeypatch.delenv(
        "PYPISERVER_BOTTLE_MEMFILE_MAX_OVERRIDE_BYTES",
        raising=False,
    )

    reload(environment)

    assert (
        environment.Environment.PYPISERVER_BOTTLE_MEMFILE_MAX_OVERRIDE_BYTES
        is None
    ), "expected default None value"


def test_override_bottle_memfile_is_set(monkeypatch):
    value_100_mb = (2**20) * 100
    monkeypatch.setenv(
        "PYPISERVER_BOTTLE_MEMFILE_MAX_OVERRIDE_BYTES",
        str(value_100_mb),
    )

    reload(environment)

    assert (
        environment.Environment.PYPISERVER_BOTTLE_MEMFILE_MAX_OVERRIDE_BYTES
        == value_100_mb
    ), "expected new 100 mb value"
