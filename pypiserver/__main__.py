#! /usr/bin/env python
"""
.. NOTE:: To the developer:
    This module is moved to the root of the standalone zip-archive,
    to be used as its entry-point. Therefore DO NOT import relative.
"""
from __future__ import print_function

import functools as ft
import logging
import sys
import warnings
from os import path

import pypiserver
from pypiserver import bottle
from pypiserver.config import Config


log = logging.getLogger('pypiserver.main')


def init_logging(level=None, frmt=None, filename=None):
    """Initialize the logging system.

    :param int level: log level
    :param str frmt: log formatting string
    :param str filename: a filename to which to log
    """
    logging.basicConfig(level=level, format=frmt)
    rlog = logging.getLogger()
    rlog.setLevel(level)
    if filename:
        rlog.addHandler(logging.FileHandler(filename))


def _logwrite(logger, level, msg):
    """Cut newlines off the end of log messages."""
    if msg:
        line_endings = ['\r\n', '\n\r', '\n']
        for le in line_endings:
            if msg.endswith(le):
                msg = msg[:-len(le)]
        if msg:
            logger.log(level, msg)


def _update(config):
    """Output an update command or update packages."""
    from pypiserver.manage import update_all_packages
    update_all_packages(
        config.roots,
        config.download_directory,
        dry_run=not(config.execute),
        stable_only=not(config.unstable)
    )


def _run_app_from_config(config):
    """Run a bottle application for the given config."""
    init_logging(
        level=config.verbosity, filename=config.log_file, frmt=config.log_frmt
    )

    # Handle new config format
    if getattr(config, 'command', '') == 'update':
        return _update(config)
    # Handle deprecated config format
    elif getattr(config, 'update_packages', False):
        return _update(config)

    if (not config.authenticate and config.password_file != '.' or
            config.authenticate and config.password_file == '.'):
        auth_err = (
            "When auth-ops-list is empty (-a=.), password-file (-P=%r) "
            "must also be empty ('.')!"
        )
        sys.exit(auth_err % config.password_file)

    if config.server and config.server.startswith('gevent'):
        import gevent.monkey  # @UnresolvedImport
        gevent.monkey.patch_all()

    bottle.debug(config.verbosity < logging.INFO)
    bottle._stderr = ft.partial(
        _logwrite,
        logging.getLogger(bottle.__name__),
        logging.INFO
    )
    app = pypiserver.app(config)
    bottle.run(
        app=app,
        host=config.host,
        port=config.port,
        server=config.server,
    )


def _warn_deprecation():
    """Set warning filters to show a deprecation warning."""
    warnings.filterwarnings('always', category=DeprecationWarning)
    warnings.warn(DeprecationWarning(
        'The "pypi-server" command has been deprecated and will be removed '
        'in the next major release. Please use "pypiserver run" or '
        '"pypiserver update" instead.'
    ))
    warnings.filterwarnings('default', category=DeprecationWarning)


def main(argv=None):
    """Run the deprecated pypi-server command."""
    caller = path.basename(sys.argv[0])

    if caller == 'pypi-server':
        _warn_deprecation()
    elif caller != 'pypiserver':
        # Allow calling via API from other scripts, but adjust the caller
        # to get the default config type.
        caller = 'pypiserver'

    config = Config(parser_type=caller).get_parser().parse_args(args=argv)

    _run_app_from_config(config)


if __name__ == "__main__":
    main()
