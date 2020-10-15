#! /usr/bin/env python
"""Entrypoint for pypiserver."""

from __future__ import print_function

import logging
import os
import sys
import typing as t

import functools as ft
from pypiserver.config import Config, UpdateConfig


log = logging.getLogger("pypiserver.main")


def init_logging(
    level=logging.NOTSET,
    frmt=None,
    filename=None,
    stream: t.IO = None,
    logger=None,
):
    logger = logger or logging.getLogger()
    stream = stream or sys.stderr
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
    import pypiserver

    if argv is None:
        argv = sys.argv

    config = Config.from_args(argv)

    # roots = [os.path.abspath(x) for x in roots]
    # c.root = roots

    verbose_levels = [
        logging.WARNING,
        logging.INFO,
        logging.DEBUG,
        logging.NOTSET,
    ]
    log_level = list(zip(verbose_levels, range(config.verbosity)))[-1][0]

    valid_streams = {"none": None, "stderr": sys.stderr, "stdout": sys.stdout}
    if config.log_stream not in valid_streams:
        sys.exit(
            f"Invalid log stream {c.log_stream}."
            f" Choose one of {', '.join(valid_streams.keys())}"
        )

    init_logging(
        level=log_level,
        filename=config.log_file,
        frmt=config.log_frmt,
        stream=config.log_stream,
    )

    if isinstance(config, UpdateConfig):
        from pypiserver.manage import update_all_packages

        update_all_packages(
            config.roots,
            config.download_directory,
            dry_run=not config.execute,
            stable_only=config.allow_unstable,
            blacklist_file=config.ignorelist,
        )
        return

    # Fixes #49:
    #    The gevent server adapter needs to patch some
    #    modules BEFORE importing bottle!
    if config.server_method.startswith("gevent"):
        import gevent.monkey  # @UnresolvedImport

        gevent.monkey.patch_all()

    from pypiserver import bottle

    if config.server_method not in bottle.server_names:
        sys.exit(
            f"Unknown server {c.server}."
            f" Choose one of {', '.join(bottle.server_names.keys())}"
        )

    bottle.debug(config.verbosity > 1)
    bottle._stderr = ft.partial(
        pypiserver._logwrite, logging.getLogger(bottle.__name__), logging.INFO
    )
    app = pypiserver.app_from_config(config)
    bottle.run(
        app=app,
        host=config.interface,
        port=config.port,
        server=config.server_method,
    )


if __name__ == "__main__":
    main()
