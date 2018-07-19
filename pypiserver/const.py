"""Constant values for pypiserver."""

from sys import version_info


PLUGIN_GROUPS = ('authenticators',)
PY2 = version_info < (3,)
STANDALONE_WELCOME = 'standalone'
