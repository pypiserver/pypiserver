"""Authentication based on an htpasswd file."""

from os import environ
from textwrap import dedent

from passlib.apache import HtpasswdFile

from .interface import AuthenticatorInterface


class HtpasswdAuthenticator(AuthenticatorInterface):
    """Authenticate using passlib and an htpasswd file."""

    plugin_name = 'Htpasswd Authenticator'
    plugin_help = 'Authenticate using an Apache htpasswd file'

    def __init__(self, config):
        """Instantiate the authenticator."""
        self.config = config

    @classmethod
    def update_parser(cls, parser):
        """Add htpasswd arguments to the config parser.

        :param argparse.ArgumentParser parser: the config parser
        """
        parser.add_argument(
            '-P', '--passwords',
            dest='password_file',
            default=environ.get('PYPISERVER_PASSWORD_FILE'),
            help=dedent('''\
                use apache htpasswd file PASSWORD_FILE to set usernames &
                passwords when authenticating certain actions (see -a option).
            ''')
        )

    def authenticate(self, request):
        """Authenticate the provided request."""
        if (self.config.password_file is None or
                self.config.password_file == '.'):
            return True
        pwd_file = HtpasswdFile(self.config.password_file)
        pwd_file.load_if_changed()
        return pwd_file.check_password(*request.auth)
