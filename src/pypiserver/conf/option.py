"""An option implementation for use in a variety of sources."""

from pypiserver.immutable import Immutable
from .source import Source


class Option(Immutable):
    """An option that may be sourced from multiple locations."""

    def __init__(self, sources: int, help_txt: str = ""):
        """Create a representation of an option."""
        self._sources = sources
        self._help = help_txt

    @property
    def is_conf_opt(self) -> bool:
        """Return whether the opt is a config option."""
        return Source.conf(self._sources)

    @property
    def is_env_opt(self) -> bool:
        """Return whether the opt is an env option."""
        return Source.env(self._sources)

    @property
    def is_args_opt(self) -> bool:
        """Return whether the opt is a commandline option."""
        return Source.args(self._sources)

    @property
    def help(self) -> str:
        """Return the help text for this option."""
        return self._help
