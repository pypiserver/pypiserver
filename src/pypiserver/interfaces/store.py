"""Interface for data stores."""

import typing as t
from abc import ABC, abstractmethod

from .package import IPackage


class IStore(ABC):
    """Storage interface."""

    @abstractmethod
    async def delete_package(self, package: IPackage) -> None:
        """Delete package."""

    @abstractmethod
    async def iter_packages(
        self, match=None
    ) -> t.AsyncGenerator[IPackage, None]:
        """Iterate packages, optionally conforming to match."""

    @abstractmethod
    async def replace_package(self, original: IPackage, update: IPackage):
        """Replace one package with another."""

    @abstractmethod
    async def save_package(self, package: IPackage):
        """Return package bytes."""
