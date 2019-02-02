"""An option implementation for use in a variety of sources."""

import typing as t

from pypiserver.immutable import Immutable, ImmutableStatic


class Sources(Immutable):
    """Represent the possible sources of an option."""

    NONE: int = 0
    CONF: int = 1
    ENV: int = 2
    ARGS: int = 4

    def __init__(self, sources: int):
        """Create an OptionSource with the provided sources.

        :param sources: sources may be combined using the bitwise OR
            operator, e.g. `OptionSource(Sources.CONF | Sources.ENV)`.
        """
        self._sources = sources

    @property
    def conf(self) -> bool:
        """Return whether sources include the config."""
        return Sources.CONF & self._sources == Sources.CONF

    @property
    def env(self) -> bool:
        """Return whether sources include the environment."""
        return Sources.ENV & self._sources == Sources.ENV

    @property
    def args(self) -> bool:
        """Return whether sources include commandline arguments."""
        return Sources.ARGS & self._sources == Sources.ARGS


class Option(Immutable):
    """An option that may be sourced from multiple locations."""

    def __init__(self, sources: Sources):
        """Create a representation of an option."""
        self.sources = sources
