"""Test option specification."""

import pytest

from pypiserver.conf.option import Sources


# pylint: disable=no-self-use


class TestOptionSources:
    """Test the Sources class."""

    @pytest.mark.parametrize('sources', (
        Sources.CONF,
        Sources.CONF | Sources.ENV,
        Sources.CONF | Sources.ARGS,
        Sources.CONF | Sources.ENV | Sources.ARGS,
    ))
    def test_conf(self, sources):
        """Sources including CONF are parsed correctly."""
        assert Sources(sources).conf

    @pytest.mark.parametrize('sources', (
        Sources.ENV,
        Sources.ENV | Sources.CONF,
        Sources.ENV | Sources.ARGS,
        Sources.ENV | Sources.CONF | Sources.ARGS,
    ))
    def test_env(self, sources):
        """Sources including CONF are parsed correctly."""
        assert Sources(sources).env

    @pytest.mark.parametrize('sources', (
        Sources.ARGS,
        Sources.ARGS | Sources.CONF,
        Sources.ARGS | Sources.ENV,
        Sources.ARGS | Sources.CONF | Sources.ENV,
    ))
    def test_args(self, sources):
        """Sources including CONF are parsed correctly."""
        assert Sources(sources).args
