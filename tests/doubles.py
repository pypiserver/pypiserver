"""Utilities for constructing test doubles."""


class GenericNamespace(object):
    """A generic namespace constructed from kwargs."""

    def __init__(self, **kwargs):
        """Convert kwargs to attributes on the instantiated object."""
        for key, value in kwargs.items():
            setattr(self, key, value)
