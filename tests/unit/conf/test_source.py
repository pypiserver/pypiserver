"""Test option/command sources."""

import pytest

from pypiserver.conf.source import Source


# pylint: disable=no-self-use


class TestOptionSources:
    """Test the Sources class."""

    @pytest.mark.parametrize('sources', (
        Source.CONF,
        Source.CONF | Source.ENV,
        Source.CONF | Source.ARGS,
        Source.CONF | Source.ENV | Source.ARGS,
    ))
    def test_conf(self, sources):
        """Sources including CONF are parsed correctly."""
        assert Source.conf(sources)

    @pytest.mark.parametrize('sources', (
        Source.ENV,
        Source.ENV | Source.CONF,
        Source.ENV | Source.ARGS,
        Source.ENV | Source.CONF | Source.ARGS,
    ))
    def test_env(self, sources):
        """Sources including CONF are parsed correctly."""
        assert Source.env(sources)

    @pytest.mark.parametrize('sources', (
        Source.ARGS,
        Source.ARGS | Source.CONF,
        Source.ARGS | Source.ENV,
        Source.ARGS | Source.CONF | Source.ENV,
    ))
    def test_args(self, sources):
        """Sources including CONF are parsed correctly."""
        assert Source.args(sources)
