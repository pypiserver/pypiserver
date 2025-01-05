import os
from pypiserver.bottle_wrapper.bottle import BaseRequest


class __Environment__:
    """This class contains various environment configurations for Pypi-Server."""

    @property
    def PYPISERVER_BOTTLE_MEMFILE_MAX_OVERRIDE_BYTES(self) -> int:
        """A way to override the `MEMFILE_MAX` value set in `bottle`.

        Examples:
            - `PYPISERVER_BOTTLE_MEMFILE_MAX_OVERRIDE_BYTES`

            -- Default Value is 100 KB
            >>> environment = __Environment__()
            >>> environment.PYPISERVER_BOTTLE_MEMFILE_MAX_OVERRIDE_BYTES
            102400

            -- Can be patched via environment variables
            >>> new_value_100_mb = (2 ** 20) * 100
            >>> os.environ["PYPISERVER_BOTTLE_MEMFILE_MAX_OVERRIDE_BYTES"] = str(new_value_100_mb)
            >>> environment.PYPISERVER_BOTTLE_MEMFILE_MAX_OVERRIDE_BYTES
            104857600
        """
        return int(
            os.getenv(
                "PYPISERVER_BOTTLE_MEMFILE_MAX_OVERRIDE_BYTES",
                BaseRequest.MEMFILE_MAX,
            )
        )


ENVIRONMENT = __Environment__()
