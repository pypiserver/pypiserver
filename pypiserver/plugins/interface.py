"""Common plugin interface for pypiserver."""

from abc import ABCMeta, abstractmethod

from pypiserver.const import PY2

if PY2:
    # Create the equivalent of Python 3's ABC class
    ABC = ABCMeta('ABC', (object,), {'__slots__', ()})
else:
    from abc import ABC


class PluginInterface(ABC):
    """Base plugin interface for pypiserver plugins."""

    @abstractmethod
    def plugin_help(self):
        """Return some general help text for the plugin.

        :rtype: str
        :return: a short description of the plugin's purpose
        """

    @classmethod
    def add_config_arguments(cls, parser):
        """Add arguments to the argument parser."""

    def add_config_subcommand(self, root_parser):
        """Add a subcommand to the root parser."""

    def add_config_root_argument_group(self, root_parser):
        """Add a config argument group to the root parser."""

    def add_config_run_argument_group(self, run_parser):
        """Add a config argument group to the "run" parser."""

    def add_config_update_argument_group(self, update_parser):
        """Add a config argument group to the "update" parser."""
