"""Test doubles."""


class Namespace(object):
    """Simple namespace."""

    def __init__(self, **kwargs):
        """Instantiate the namespace with the provided kwargs."""
        for k, v in kwargs.items():
            setattr(self, k, v)
