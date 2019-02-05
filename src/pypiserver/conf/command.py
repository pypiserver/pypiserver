"""Provide an interface for pypiserver commands."""

import typing as t

from pypiserver.immutable import Immutable

from .option import Option


class Command(Immutable):
    """A pypiserver [sub]command."""

    def __init__(self, name: str, *options: Option) -> None:
        """Create a command instance."""
        self._name = name
        self._options = options

    @property
    def name_for_args(self) -> str:
        """Return the command name normalized for args."""
        return self._name.replace("_", "-").lower()

    @property
    def name_for_config(self) -> str:
        """Return the command name normalized for a config file."""
        return self.name_for_args

    @property
    def name_internal(self) -> str:
        """Return the python-style command name."""
        return self._name.replace("-", "_").lower()

    @property
    def options(self) -> t.Generator[Option, None, None]:
        """Yield options associated with the command."""
        yield from self._options


class CommandGroup(Immutable):
    """A group of pypiserver commands."""

    def __init__(self, name: str, *commands: Command):
        """Create a command group."""
        self._name = name
        self._commands = commands

    @property
    def name_internal(self) -> str:
        """Return the internal python var name of the group."""
        return self._name.replace("-", "_").lower()

    @property
    def commands(self) -> t.Generator[Command, None, None]:
        """Yield commands associated with the group."""
        yield from self._commands
