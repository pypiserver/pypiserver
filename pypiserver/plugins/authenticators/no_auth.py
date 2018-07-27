"""An authenticator that always authenticates successfully."""

from .interface import AuthenticatorInterface


class NoAuthAuthenticator(AuthenticatorInterface):
    """Authenticate successfully all the time."""

    plugin_name = 'No-Auth Authenticator'
    plugin_help = 'Authenticate successfully all the time'

    def authenticate(self, request):
        """Authenticate the provided request."""
        return True
