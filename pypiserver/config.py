"""Define utilities for parsing and consuming config options."""

import logging
import re
from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser
from os import environ, path
from textwrap import dedent

from . import __version__


_AUTH_RE = re.compile(r'[, ]+')
_AUTH_ACTIONS = ('download', 'list', 'update')


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


class ArgumentFormatter(ArgumentDefaultsHelpFormatter):
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
            return super(ArgumentFormatter, self)._get_help_string(action)


def auth_parse(auth_str):
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


def roots_parse(roots):
    """Expand user home and update roots to absolute paths."""
    return [path.abspath(path.expanduser(r)) for r in roots]


def verbosity_parse(verbosity):
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


class CustomParser(ArgumentParser):
    """Allow extra actions following the final parse.

    Actions like "count", and regular "store" actions when "nargs" is
    specified, do not allow the specification of a "type" function,
    which means we can't do on-the-fly massaging of those values. Instead,
    we call them separately here.
    """

    extra_parsers = {
        'roots': roots_parse,
        'verbosity': verbosity_parse,
    }

    def parse_args(self, args=None, namespace=None):
        """Parse arguments."""
        parsed = super(CustomParser, self).parse_args(
            args=args, namespace=namespace
        )
        for attr, parser in self.extra_parsers.items():
            setattr(parsed, attr, parser(getattr(parsed, attr)))
        return parsed


def get_parser():
    """Return an argument parser."""
    parser = CustomParser(
        description='start PyPI compatible package server',
        formatter_class=ArgumentFormatter,
    )

    # ******************************************************************
    # Global Arguments
    # ******************************************************************

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

    # ******************************************************************
    # Server Arguments
    # ******************************************************************

    server = parser.add_argument_group('server')
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
        '-p', '--port', default=environ.get('PYPISERVER_PORT', _Defaults.port),
        type=int, help='listen on port PORT'
    )
    server.add_argument(
        '-o', '--overwrite',
        action='store_true',
        default=environ.get('PYPISERVER_OVERWRITE', _Defaults.overwrite),
        help='allow overwriting existing package files',
    )
    server.add_argument(
        '--fallback-url',
        default=environ.get('PYPISERVER_FALLBACK_URL', _Defaults.fallback_url),
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
        default=environ.get('PYPISERVER_HASH_ALGO', _Defaults.hash_algo),
        metavar='ALGO',
        help=('any `hashlib` available algo used as fragments on package '
              'links. Set one of (0, no, off, false) to disabled it')
    )
    server.add_argument(
        '--welcome',
        default=environ.get('PYPISERVER_WELCOME'),
        dest='welcome_file',
        metavar='HTML_FILE',
        help='uses the ASCII contents of HTML_FILE as welcome message'
    )
    server.add_argument(
        '--cache-control',
        default=environ.get('PYPISERVER_CACHE_CONTROL'),
        metavar='AGE',
        help=('Add "Cache-Control: max-age=AGE, public" header to package '
              'downloads. Pip 6+ needs this for caching')
    )

    # ******************************************************************
    # Security Arguments
    # ******************************************************************

    security = parser.add_argument_group('security')
    # TODO: pull some of this long stuff out into an epilog
    security.add_argument(
        '-a', '--authenticate',
        type=auth_parse,
        default=environ.get('PYPISERVER_AUTHENTICATE', _Defaults.authenticate),
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
    security.add_argument(
        '-P', '--passwords',
        dest='password_file',
        default=environ.get('PYPISERVER_PASSWORD_FILE'),
        help=dedent('''\
            use apache htpasswd file PASSWORD_FILE to set usernames &
            passwords when authenticating certain actions (see -a option).
            If you want to allow un-authorized access, set this option and -a
            to '.'
        ''')
    )

    logger = parser.add_argument_group('logger')
    logger.add_argument(
        '--log-file', default=environ.get('PYPISERVER_LOG_FILE'),
        help='write logging info into LOG_FILE'
    )
    logger.add_argument(
        '--log-frmt',
        default=environ.get('PYPISERVER_LOG_FRMT', _Defaults.log_fmt),
        metavar='FORMAT',
        help=('the logging format string. (see `logging.LogRecord` class '
              'from standard python library)')
    )
    logger.add_argument(
        '--log-req-frmt',
        default=environ.get('PYPISERVER_LOG_REQ_FRMT', _Defaults.log_req_fmt),
        metavar='FORMAT',
        help=('a format-string selecting Http-Request properties to log; set '
              'to "%s" to see them all')
    )
    logger.add_argument(
        '--log-res-frmt',
        default=environ.get('PYPISERVER_LOG_RES_FRMT', _Defaults.log_res_fmt),
        metavar='FORMAT',
        help=('a format-string selecting Http-Response properties to log; set '
              'to "%s" to see them all')
    )
    logger.add_argument(
        '--log-err-frmt',
        default=environ.get('PYPISERVER_LOG_ERR_FRMT', _Defaults.log_err_fmt),
        metavar='FORMAT',
        help=('a format-string selecting Http-Error properties to log; set '
              'to "%s" to see them all')
    )

    # ******************************************************************
    # Subcommand Parsers
    # ******************************************************************

    # subparsers = parser.add_subparsers(dest='sub_command', help='sub-commands')
    # update = subparsers.add_parser('update', help='update packages')
    # update.add_argument(
    #     'packages_directory',
    #     help=('update packages in PACKAGES_DIRECTORY. This command searches '
    #           'pypi.org for updates and outputs a pip command that can be '
    #           'run to perform package updates')
    # )
    # update.add_argument(
    #     '-x', '--execute',
    #     action='store_true',
    #     help='execute the pip commands instead of only showing them'
    # )
    # update.add_argument(
    #     '--pre', '-u', '--unstable',
    #     action='store_true',
    #     help='allow updating to unstable versions (alpha, beta, rc, dev)'
    # )
    # update.add_argument(
    #     '--download-directory',
    #     help=('download updates to this directory. The default is to use the '
    #           'directory containing the package to be updated')
    # )

    return parser
