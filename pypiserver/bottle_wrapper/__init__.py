"""
This `__init__.py` allows to wrap and patch the default `bottle.py` implementation.
"""

from pypiserver.bottle_wrapper.bottle import *
from pypiserver.environment import Environment

BaseRequest.MEMFILE_MAX = (
    override
    if (override := Environment.PYPISERVER_BOTTLE_MEMFILE_MAX_OVERRIDE_BYTES)
    else BaseRequest.MEMFILE_MAX
)
