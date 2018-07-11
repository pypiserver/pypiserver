"""Interface for authentication backends for pypiserver."""

from abc import abstractmethod

from pypiserver.plugins.interface import PluginInterface


class AuthenticatorInterface(PluginInterface):
    """Defines the interface for pypiserver auth plugins."""

    def __init__(self, config):
        """Instantiate the auth plugin with the current config.

        :param argparse.Namespace config: the active config for the
            running server
        """

    @abstractmethod
    def authenticate(self, request):
        """Authenticate the passed request and return a success bool.

        :param bottle.Request request: the request being authenticated
        :return: whether the request was successfully authenticated
        :rtype: bool
        """
