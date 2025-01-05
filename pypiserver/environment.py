import os
from pypiserver.bottle_wrapper.bottle import BaseRequest


class Environment:
    """This class contains various environment configurations for Pypi-Server."""

    PYPISERVER_BOTTLE_MEMFILE_MAX_OVERRIDE_BYTES: int = int(
        os.getenv(
            "PYPISERVER_BOTTLE_MEMFILE_MAX_OVERRIDE_BYTES",
            BaseRequest.MEMFILE_MAX,
        )
    )
