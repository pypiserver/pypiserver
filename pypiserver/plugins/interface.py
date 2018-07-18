"""Common plugin interface for pypiserver."""

from pypiserver.const import PY2

if PY2:
    # Create the equivalent of Python 3's ABC class
    from abc import ABCMeta, abstractproperty

    ABC = ABCMeta('ABC', (object,), {'__slots__', ()})

else:
    from abc import ABC
    from .util import py3_abstractproperty as abstractproperty


class PluginInterface(ABC):
    """Base plugin interface for pypiserver plugins."""

    @abstractproperty
    def plugin_name(self):
        """Return the plugin name.

        Note that this can (and should) just be defined as a class
        attribute, e.g.:

        .. code:: python

            class MyPlugin(PluginInterface):
                plugin_name = "My Plugin"

        """

    @abstractproperty
    def plugin_help(self):
        """Return user-facing one-line summary of plugin.

        :rtype: str
        :return: a short description of the plugin's purpose
        """

    @classmethod
    def update_parser(cls, parser):
        """Add arguments to the pypiserver argument parser.

        Generally, this will be a subcommand parser (usually for "run"),
        but it could vary by plugin type.

        :param argparse.ArgumentParser parser: the parser for the "run"
            subcommand
        """
