"""Filesystem storage for pypiserver python packages."""

import typing as t

from pypiserver.interfaces.package import IPackage
from pypiserver.interfaces.store import IStore
from .async_util import AsyncStore


class LocalFSStore(AsyncStore, IStore):
    """Store for packages saved on a local filesystem."""

    def _read_file(self, path: str, mode: str = 'r') -> t.Awaitable:
        """Read the contents of a file in the threadpool & return."""

        def closure():
            with open(path, mode) as fp:
                return fp.read()

        return self._loop.run_in_executor(None, closure)

    async def delete_package(self, package: IPackage) -> None:
        """Delete package."""

    async def iter_packages(
        self, match=None
    ) -> t.AsyncGenerator[IPackage, None]:
        """Iterate packages, optionally conforming to match."""

    async def replace_package(self, original: IPackage, update: IPackage):
        """Replace one package with another."""

    async def save_package(self, package: IPackage):
        """Return package bytes."""
