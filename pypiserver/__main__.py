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

import pypiserver
from pypiserver import bottle
from pypiserver.config import ConfigFactory
from pypiserver.const import PY2



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


def _run_app_from_config(config):
    """Run a bottle application for the given config."""
    if (not config.authenticate and config.password_file != '.' or
            config.authenticate and config.password_file == '.'):
        auth_err = (
            "When auth-ops-list is empty (-a=.), password-file (-P=%r) "
            "must also be empty ('.')!"
        )
        sys.exit(auth_err % config.password_file)

    init_logging(
        level=config.verbosity, filename=config.log_file, frmt=config.log_frmt
    )

    if config.update_packages:
        from pypiserver.manage import update_all_packages
        update_all_packages(
            config.roots,
            config.download_directory,
            dry_run=not(config.execute),
            stable_only=not(config.unstable)
        )
        return

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


def main(argv=None):
    """Run the deprecated pypi-server command."""
    if PY2:
        # I honestly don't know why Python 2 is not raising this warning
        # with "default" as the filter.
        warnings.filterwarnings('always', category=DeprecationWarning)
    warnings.warn(DeprecationWarning(
        'The "pypi-server" command has been deprecated and will be removed '
        'in the next major release. Please use "pypiserver run" or '
        '"pypiserver update" instead.'
    ))
    if PY2:
        warnings.filterwarnings('default', category=DeprecationWarning)
    config = ConfigFactory(
        parser_type='pypi-server'
    ).get_parser().parse_args(args=argv)
    _run_app_from_config(config)


def _new_main():
    """Run the new pypiserver command."""
    _run_app_from_config(ConfigFactory().get_parsed())


if __name__ == "__main__":
    main()
