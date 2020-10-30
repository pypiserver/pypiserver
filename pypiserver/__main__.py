#! /usr/bin/env python
"""Entrypoint for pypiserver."""

from __future__ import print_function

import logging
import sys
import typing as t

import functools as ft
from pypiserver.config import Config, UpdateConfig


log = logging.getLogger("pypiserver.main")


def init_logging(
    level=logging.NOTSET,
    frmt=None,
    filename=None,
    stream: t.Optional[t.IO] = sys.stderr,
    logger=None,
):
    logger = logger or logging.getLogger()
    logger.setLevel(level)

    formatter = logging.Formatter(frmt)
    if len(logger.handlers) == 0 and stream is not None:
        handler = logging.StreamHandler(stream)
        handler.setFormatter(formatter)
        logger.addHandler(logging.StreamHandler(stream))

    if filename:
        handler = logging.FileHandler(filename)
        handler.setFormatter(formatter)
        logger.addHandler(handler)


def main(argv=None):
    """Application entrypoint for pypiserver.

    This function drives the application (as opposed to the library)
    implementation of pypiserver. Usage from the commandline will result in
    this function being called.
    """
    import pypiserver

    if argv is None:
        # The first item in sys.argv is the name of the python file being
        # executed, which we don't need
        argv = sys.argv[1:]

    config = Config.from_args(argv)

    init_logging(
        level=config.log_level,
        filename=config.log_file,
        frmt=config.log_frmt,
        stream=config.log_stream,
    )

    # Check to see if we were asked to run an update command instead of running
    # the server
    if isinstance(config, UpdateConfig):
        from pypiserver.manage import update_all_packages

        update_all_packages(
            config.roots,
            config.download_directory,
            dry_run=not config.execute,
            stable_only=config.allow_unstable,
            ignorelist=config.ignorelist,
        )
        return

    # Fixes #49:
    #    The gevent server adapter needs to patch some
    #    modules BEFORE importing bottle!
    if config.server_method.startswith("gevent"):
        import gevent.monkey  # @UnresolvedImport

        gevent.monkey.patch_all()

    from pypiserver import bottle

    bottle.debug(config.verbosity > 1)
    bottle._stderr = ft.partial(
        _logwrite, logging.getLogger(bottle.__name__), logging.INFO
    )

    # Here `app` is a Bottle instance, which we pass to bottle.run() to run
    # the server
    app = pypiserver.app_from_config(config)
    bottle.run(
        app=app,
        host=config.host,
        port=config.port,
        server=config.server_method,
    )


def _logwrite(logger, level, msg):
    if msg:
        line_endings = ["\r\n", "\n\r", "\n"]
        for le in line_endings:
            if msg.endswith(le):
                msg = msg[: -len(le)]
        if msg:
            logger.log(level, msg)


if __name__ == "__main__":
    main()
