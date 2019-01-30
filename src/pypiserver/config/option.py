"""An option implementation for use in a variety of sources."""

from pypiserver.immutable import ImmutableStatic


class OptionSource(ImmutableStatic):
    """Sources from which an option value may come."""

    NONE: int = 0
    CONF: int = 1
    ENV: int = 2
    ARGS: int = 4


# class Option:
#     """An option that may be sourced from multiple locations."""

#     def __init__(self, )
