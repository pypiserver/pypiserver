"""Interface for packages."""

from abc import ABC, abstractmethod


class IPackageName(ABC):
    """Package name interface."""

    @property
    @abstractmethod
    def normalized(self) -> str:
        """Return the normalized package name."""

    @property
    @abstractmethod
    def valid(self) -> bool:
        """Return whether the package name is valid."""


class IPackageVersion(ABC):
    """Package version interface."""


class IPackage(ABC):
    """Package interface."""

    @property
    @abstractmethod
    def name(self) -> IPackageName:
        """Return the package name."""

    @property
    @abstractmethod
    def version(self) -> IPackageVersion:
        """Return the package version."""

    @abstractmethod
    async def save(self):
        """Save the package to a data store."""
