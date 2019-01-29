"""Model(s) related to a python package."""

from pypiserver.interfaces.package import (
    IPackage,
    IPackageName,
    IPackageVersion,
)
from pypiserver.interfaces.store import IStore
from .compliance import Pep426, Pep503


class PackageName(IPackageName):
    """A python package name."""

    __slots__ = ("normalized", "raw", "valid")

    def __init__(self, name: str):
        """Create a name instance."""
        self.raw = name

    def __str__(self) -> str:
        """Return a friendly representation of the object."""
        return f"'{self.raw}'"

    def __repr__(self) -> str:
        """Return a string representation of the object."""
        return f"PackageName('{self.raw}')"

    @property
    def normalized(self):
        """Return a standards-compliant package name."""
        return Pep503.normalized_name(self.raw)

    @property
    def valid(self) -> bool:
        """Return whether the package name is valid."""
        return Pep426.valid_name(self.raw)


class PackageVersion(IPackageVersion):
    """A python package version."""

    __slots__ = ("raw",)

    def __init__(self, version: str):
        """Create a version instance."""
        self.raw = version

    def __str__(self) -> str:
        """Return a friendly representation of the version."""
        return f"'{self.raw}'"

    def __repr__(self) -> str:
        """Return a string representation of the version."""
        return f"PackageVersion('{self.raw}'"


class Package(IPackage):
    """A python package."""

    __slots__ = ("name", "version")

    def __init__(self, store: Istore, name: PackageName, version: PackageVersion):
        """Create a python package instance."""
        self._store = store
        self._name = name
        self._version = version

    def __str__(self) -> str:
        """Return a string representation of the package."""
        return f"Package({self.name}, {self.version})"

    @property
    def name(self) -> PackageName:
        """Return the package name."""
        return self._name

    @property
    def version(self) -> PackageVersion:
        """Return the package version."""
        return self._version

    async def save(self):
        """Save the package to a data store."""
        pass
