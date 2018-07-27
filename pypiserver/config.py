"""Define utilities for parsing and consuming config options."""

import logging
import re
from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser
from hashlib import algorithms_available
from os import environ, path
from textwrap import dedent

import pkg_resources

from . import __version__
from .bottle import server_names
from .core import load_plugins
from .const import STANDALONE_WELCOME


_AUTH_RE = re.compile(r'[, ]+')
_AUTH_ACTIONS = ('download', 'list', 'update')
_FALSES = ('no', 'off', '0', 'false')


def str2bool(string):
    """Convert a string into a boolean."""
    return string.lower() not in _FALSES


def _get_welcome_file():
    """Get the welcome file or set a constant for the standalone package."""
    try:
        return pkg_resources.resource_filename(
            'pypiserver', _Defaults.welcome_file
        )
    except NotImplementedError:  # raised in standalone zipfile.
        return STANDALONE_WELCOME


class _Defaults(object):
    """Define default constants."""

    authenticate = 'update'
    fallback_url = 'https://pypi.org/simple'
    hash_algo = 'md5'
    host = '0.0.0.0'
    log_fmt = '%(asctime)s|%(name)s|%(levelname)s|%(thread)d|%(message)s'
    log_req_fmt = '%(bottle.request)s'
    log_res_fmt = '%(status)s'
    log_err_fmt = '%(body)s: %(exception)s \n%(traceback)s'
    overwrite = False
    port = 8080
    redirect_to_fallback = True
    roots = ['~/packages']
    server = 'auto'
    welcome_file = 'welcome.html'


class _HelpFormatter(ArgumentDefaultsHelpFormatter):
    """A custom formatter to flip our one confusing argument.

    ``--disable-fallback`` is stored as ``redirect_to_fallback``,
    so the actual boolean value is opposite of what one would expect.
    The :ref:`ArgumentDefaultsHelpFormatter` doesn't really have any
    way of dealing with this situation, so we special case it.
    """

    def _get_help_string(self, action):
        """Return the help string for the action."""
        if '--disable-fallback' in action.option_strings:
            return action.help + ' (default: False)'
        else:
            return super(_HelpFormatter, self)._get_help_string(action)


class _CustomParsers(object):
    """Collect custom parsers."""

    @staticmethod
    def auth(auth_str):
        """Parse the auth string to yield a list of authenticated actions.

        :param str auth_str: a string of comma-separated auth actions

        :return: a list of validated auth actions
        :rtype: List[str]
        """
        authed = [
            a.lower() for a in _AUTH_RE.split(auth_str.strip(' ,')) if a
        ]
        if len(authed) == 1 and authed[0] == '.':
            return []
        for a in authed:
            if a not in _AUTH_ACTIONS:
                errmsg = 'Authentication action "%s" not one of %s!'
                raise ValueError(errmsg % (a, _AUTH_ACTIONS))
        return authed

    @staticmethod
    def hash_algo(hash_algo):
        """Parse the hash algorithm.

        If the user set the algorithm to a falsey string, return ``None``.
        Otherwise, return the set or default value.
        """
        if not str2bool(hash_algo):
            return None
        return hash_algo

    @staticmethod
    def roots(roots):
        """Expand user home and update roots to absolute paths."""
        return [path.abspath(path.expanduser(r)) for r in roots]

    @staticmethod
    def verbosity(verbosity):
        """Convert the verbosity level to a logging level.

        :param int verbosity: the count of -v values from the commandline
        :return: a logging constant appropriate for the specified verbosity
        :rtype: int
        """
        verbosities = (
            logging.WARNING, logging.INFO, logging.DEBUG, logging.NOTSET
        )
        try:
            return verbosities[verbosity]
        except IndexError:
            return verbosities[-1]


class _PypiserverParser(ArgumentParser):
    """Allow extra actions following the final parse.

    Actions like "count", and regular "store" actions when "nargs" is
    specified, do not allow the specification of a "type" function,
    which means we can't do on-the-fly massaging of those values. Instead,
    we call them separately here.
    """

    extra_parsers = {
        'authenticate': _CustomParsers.auth,
        'hash_algo': _CustomParsers.hash_algo,
        'roots': _CustomParsers.roots,
        'verbosity': _CustomParsers.verbosity,
    }

    def parse_args(self, args=None, namespace=None):
        """Parse arguments."""
        parsed = super(_PypiserverParser, self).parse_args(
            args=args, namespace=namespace
        )
        for attr, parser in self.extra_parsers.items():
            if hasattr(parsed, attr):
                setattr(parsed, attr, parser(getattr(parsed, attr)))
        return parsed


class Config(object):
    """Factory for pypiserver configs and parsers."""

    def __init__(self, parser_cls=_PypiserverParser,
                 help_formatter=_HelpFormatter, parser_type='pypiserver'):
        """Instantiate the factory.

        :param argparse.HelpFormatter help_formatter: the HelpForamtter class
            to use for the parser
        :param str parser_type: one of 'pypi-server' (deprecated) or
            'pypiserver'
        """
        self.help_formatter = help_formatter
        self.parser_cls = parser_cls
        self.parser_type = parser_type
        self._plugins = load_plugins()

    def get_default(self, subcommand='run'):
        """Return a parsed config with default argument values.

        :param str subcommand:
            the subcommand for which to return default arguments.
        :rtype: argparse.Namespace
        """
        return self.get_parser().parse_args([subcommand])

    def get_parsed(self):
        """Return arguments parsed from the commandline.

        :rtype: argparse.Namespace
        """
        return self.get_parser().parse_args()

    def get_parser(self):
        """Return an ArgumentParser instance with all arguments populated.

        :rtype: PypiserverParser
        """
        if self.parser_type == 'pypiserver':
            return self._get_parser()
        elif self.parser_type == 'pypi-server':
            return self._get_deprecated_parser()
        else:
            raise ValueError(
                'Unsupported parser_type: {}'.format(self.parser_type)
            )

    def from_kwargs(self, **kwargs):
        """Return a default config updated with the provided kwargs.

        :param dict kwargs: key-value pairs with which to populate the
            config. Keys may be provided that are not in the default
            config.
        """
        conf = self.get_default()
        for key, value in kwargs.items():
            setattr(conf, key, value)
        return conf

    def _get_parser(self):
        """Return a hydrated parser."""
        parser = self.parser_cls(
            description='PyPI-compatible package server',
            formatter_class=self.help_formatter
        )
        self.add_root_args(parser)
        self.add_logging_arg_group(parser)
        subparsers = parser.add_subparsers(dest='command', help='commands')
        self.add_run_subcommand(subparsers)
        self.add_update_subcommand(subparsers)
        return parser

    def _get_deprecated_parser(self):
        """Return the deprecated parser."""
        parser = self.parser_cls(
            description='PyPI-compatible package server',
            formatter_class=self.help_formatter
        )
        self.add_root_args(parser)
        self.add_server_arg_group(parser)
        self.add_security_arg_group(parser)
        self.add_logging_arg_group(parser)
        self.add_http_logging_group(parser)
        self.add_deprecated_update_arg_group(parser)
        return parser

    @staticmethod
    def add_root_args(parser):
        """Add root-level arguments to the parser.

        :param ArgumentParser parser: an ArgumentParser instance
        """
        parser.add_argument(
            '-v', '--verbose',
            dest='verbosity',
            action='count',
            default=0,
            help=(
                'Increase verbosity. May be specified multiple times for '
                'extra verbosity'
            )
        )
        parser.add_argument(
            '--version',
            action='version',
            version='%(prog)s {}'.format(__version__),
        )

    def add_run_subcommand(self, subparsers):
        """Add the "update" command to the subparsers instance.

        :param subparsers: an ArgumentParser subparser.
        """
        run = subparsers.add_parser('run', help='run pypiserver')
        self.add_server_arg_group(run)
        self.add_security_arg_group(run)
        self.add_plugin_args_run(run)
        self.add_http_logging_group(run)

    @staticmethod
    def add_update_subcommand(subparsers):
        """Add the "update" command to the subparsers instance.

        :param subparsers: an ArgumentParser subparser.
        """
        update = subparsers.add_parser('update', help='update packages')
        update.add_argument(
            'roots',
            nargs='*',
            default=_Defaults.roots,
            metavar='root',
            help=('update packages in root(s). This command '
                  'searches pypi.org for updates and outputs a pip command '
                  'which can be run to update the packages')
        )
        update.add_argument(
            '-x', '--execute',
            action='store_true',
            help='execute the pip commands instead of only showing them'
        )
        update.add_argument(
            '--pre',
            action='store_true',
            help='allow updating to prerelease versions (alpha, beta, rc, dev)'
        )
        update.add_argument(
            '--download-directory',
            help=('download updates to this directory. The default is to use '
                  'the directory containing the packages to be updated')
        )

    @staticmethod
    def add_server_arg_group(parser):
        """Add arguments for running pypiserver.

        :param ArgumentParser parser: an ArgumentParser instance
        """
        server = parser.add_argument_group(
            title='Server',
            description='Configure the pypiserver instance'
        )
        server.add_argument(
            'roots',
            default=_Defaults.roots,
            metavar='root',
            nargs='*',
            help=(dedent('''\
                serve packages from the specified root directory. Multiple
                root directories may be specified. If no root directory is
                provided, %(default)s will be used. Root directories will
                be scanned recursively for packages. Files and directories
                starting with a dot are ignored.
            '''))
        )
        server.add_argument(
            '-i', '--interface',
            default=environ.get('PYPISERVER_INTERFACE', _Defaults.host),
            dest='host',
            help='listen on interface INTERFACE'
        )
        server.add_argument(
            '-p', '--port',
            default=environ.get('PYPISERVER_PORT', _Defaults.port),
            type=int,
            help='listen on port PORT',
        )
        server.add_argument(
            '-o', '--overwrite',
            action='store_true',
            default=environ.get('PYPISERVER_OVERWRITE', _Defaults.overwrite),
            help='allow overwriting existing package files',
        )
        server.add_argument(
            '--fallback-url',
            default=environ.get(
                'PYPISERVER_FALLBACK_URL',
                _Defaults.fallback_url,
            ),
            help=('for packages not found in the local index, return a '
                  'redirect to this URL')
        )
        server.add_argument(
            '--disable-fallback',
            action='store_false',
            default=environ.get(
                'PYPISERVER_DISABLE_FALLBACK',
                _Defaults.redirect_to_fallback,
            ),
            dest='redirect_to_fallback',
            help=('disable redirect to real PyPI index for packages not found '
                  'in the local index')
        )
        server.add_argument(
            '--server',
            choices=server_names,
            default=environ.get('PYPISERVER_SERVER', _Defaults.server),
            metavar='METHOD',
            help=(dedent('''\
                use METHOD to run the server. Valid values include paste,
                cherrypy, twisted, gunicorn, gevent, wsgiref, auto. The
                default is to use "auto" which chooses one of paste, cherrypy,
                twisted or wsgiref
            '''))
        )
        server.add_argument(
            '--hash-algo',
            choices=tuple(a.lower() for a in algorithms_available) + _FALSES,
            default=environ.get('PYPISERVER_HASH_ALGO', _Defaults.hash_algo),
            metavar='ALGO',
            help=('any `hashlib` available algo used as fragments on package '
                  'links. Set one of (0, no, off, false) to disabled it')
        )
        server.add_argument(
            '--welcome',
            default=environ.get(
                'PYPISERVER_WELCOME',
                _get_welcome_file()
            ),
            dest='welcome_file',
            metavar='HTML_FILE',
            help='uses the ASCII contents of HTML_FILE as welcome message'
        )
        server.add_argument(
            '--cache-control',
            default=environ.get('PYPISERVER_CACHE_CONTROL'),
            metavar='AGE',
            type=int,
            help=('Add "Cache-Control: max-age=AGE, public" header to package '
                  'downloads. Pip 6+ needs this for caching')
        )

    def add_security_arg_group(self, parser):
        """Add security arguments to the parser.

        :param ArgumentParser parser: an ArgumentParser instance
        """
        security = parser.add_argument_group(
            title='Security',
            description='Configure pypiserver access controls'
        )
        # TODO: pull some of this long stuff out into an epilog
        security.add_argument(
            '-a', '--authenticate',
            default=environ.get(
                'PYPISERVER_AUTHENTICATE',
                _Defaults.authenticate,
            ),
            help=dedent('''\
                comma-separated list of (case-insensitive) actions to
                authenticate. Use "." for no authentication. Requires the
                password (-P option) to be set. For example to password-protect
                package downloads (in addition to uploads), while leaving
                listings public, use: `-P foo/htpasswd.txt`  -a update,download
                To drop all authentications, use: `-P .  -a `.
                Note that when uploads are not protected, the `register`
                command is not necessary, but `~/.pypirc` still requires
                username and password fields, even if bogus. By default,
                only %(default)s is password-protected
            ''')
        )
        if self.parser_type == 'pypi-server':
            security.add_argument(
                '-P', '--passwords',
                dest='password_file',
                default=environ.get('PYPISERVER_PASSWORD_FILE'),
                help=dedent('''\
                    use apache htpasswd file PASSWORD_FILE to set usernames &
                    passwords when authenticating certain actions (see
                    -a option). If you want to allow unauthorized access,
                    set this option and -a to '.'
                ''')
            )
        security.add_argument(
            '--auth-backend',
            dest='auther',
            default=environ.get('PYPISERVER_AUTH_BACKEND'),
            choices=self._plugins['authenticators'].keys(),
            help=(
                'Specify an authentication backend. By default, will attempt '
                'to use an htpasswd file if provided. If specified, must '
                'correspond to an installed auth plugin.'
            )
        )

    @staticmethod
    def add_plugin_group(parser, name, plugin):
        """Add a plugin group to the parser."""
        group = parser.add_argument_group(
            title='{} ({} plugin)'.format(plugin.plugin_name, name),
            description=plugin.plugin_help,
        )
        plugin.update_parser(group)

    def add_plugin_args_run(self, parser):
        """Add plugin args for the "run" subcommand.

        :param ArgumentParser parser: the "run" subcommand parser
        """
        for name, plugin in self._plugins['authenticators'].items():
            self.add_plugin_group(parser, name, plugin)

    @staticmethod
    def add_logging_arg_group(parser):
        """Add pypiserver logging arguments.

        :param ArgumentParser parser: an ArgumentParser instance
        """
        logs = parser.add_argument_group(title='logs')
        logs.add_argument(
            '--log-file',
            default=environ.get('PYPISERVER_LOG_FILE'),
            help='write logging info into LOG_FILE'
        )
        logs.add_argument(
            '--log-frmt',
            default=environ.get('PYPISERVER_LOG_FRMT', _Defaults.log_fmt),
            metavar='FORMAT',
            help=('the logging format string. (see `logging.LogRecord` class '
                  'from standard python library)')
        )

    @staticmethod
    def add_http_logging_group(parser):
        """Add a group to with HTTP logging arguments.

        :param ArgumentParser parser: an ArgumentParser instance
        """
        http_logs = parser.add_argument_group(
            title='HTTP logs',
            description='Define the logging format for HTTP events'
        )
        http_logs.add_argument(
            '--log-req-frmt',
            default=environ.get(
                'PYPISERVER_LOG_REQ_FRMT',
                _Defaults.log_req_fmt,
            ),
            metavar='FORMAT',
            help=('a format-string selecting Http-Request properties to log; '
                  'set to "%s" to see them all')
        )
        http_logs.add_argument(
            '--log-res-frmt',
            default=environ.get(
                'PYPISERVER_LOG_RES_FRMT',
                _Defaults.log_res_fmt
            ),
            metavar='FORMAT',
            help=('a format-string selecting Http-Response properties to log; '
                  'set to "%s" to see them all')
        )
        http_logs.add_argument(
            '--log-err-frmt',
            default=environ.get(
                'PYPISERVER_LOG_ERR_FRMT',
                _Defaults.log_err_fmt
            ),
            metavar='FORMAT',
            help=('a format-string selecting Http-Error properties to log; '
                  'set to "%s" to see them all')
        )

    @staticmethod
    def add_deprecated_update_arg_group(parser):
        """Add arguments for the deprecated update packages command.

        :param ArgumentParser parser: an ArgumentParser instance
        """
        update = parser.add_argument_group(
            'update packages',
            description='Update packages instead of running the pypiserver.'
        )
        update.add_argument(
            '-U', '--update-packages',
            action='store_true',
            help=(
                'Update packages in specified diretories. This command '
                'searches pypi.org for updates and outputs a pip command '
                'which can be used to update the packages.'
            )
        )
        update.add_argument(
            '-x', '--execute',
            action='store_true',
            help='execute the pip commands instead of only showing them'
        )
        update.add_argument(
            '-u', '--unstable',
            action='store_true',
            help='allow updating to unstable versions (alpha, beta, rc, dev)'
        )
        update.add_argument(
            '--download-directory',
            help=('download updates to this directory. The default is to use '
                  'the directory containing the package to be updated')
        )
