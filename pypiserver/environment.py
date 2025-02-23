import os
from typing import Optional


class Environment:
    """This class contains various environment configurations for Pypi-Server."""

    PYPISERVER_BOTTLE_MEMFILE_MAX_OVERRIDE_BYTES: Optional[int] = (
        int(override)
        if (
            override := os.getenv(
                "PYPISERVER_BOTTLE_MEMFILE_MAX_OVERRIDE_BYTES",
            )
        )
        else None
    )
