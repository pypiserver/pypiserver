"""Filesystem storage for pypiserver python packages."""

from . import IStore


class LocalFSStore(IStore):
    """Store for packages saved on a local filesystem."""
