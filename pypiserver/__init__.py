"""Simple PyPI-compliant package server."""


__title__ = "pypiserver"
__summary__ = "A minimal PyPI server for use with pip/easy_install."
__uri__ = "https://github.com/pypiserver/pypiserver"

# Interface
from ._app import app  # noqa
from ._version import __version__, __version_info__, version  # noqa
