"""Filesystem storage for pypiserver python packages."""

import typing as t

from pypiserver.interfaces.package import IPackage
from pypiserver.interfaces.store import IStore


class LocalFSStore(IStore):
    """Store for packages saved on a local filesystem."""

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
