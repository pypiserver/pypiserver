"""Model(s) related to a python package."""

import typing as t
from pypiserver.interfaces.package import (
    IPackage,
    IPackageName,
    IPackageVersion,
)
from pypiserver.interfaces.store import IStore
from .compliance import Pep426, Pep503


class PackageName(IPackageName):
    """A python package name."""

    __slots__ = ("_normalized", "_valid", "_raw", "normalized", "raw", "valid")

    def __init__(self, name: str):
        """Create a name instance."""
        self._normalized: t.Optional[str] = None
        self._valid: t.Optional[bool] = None
        self._raw: str = name

    def __str__(self) -> str:
        """Return a friendly representation of the object."""
        return f"'{self.raw}'"

    def __repr__(self) -> str:
        """Return a string representation of the object."""
        return f"PackageName('{self.raw}')"

    @property
    def normalized(self) -> str:
        """Return a standards-compliant package name."""
        if self._normalized is None:
            self._normalized = Pep503.normalized_name(self.raw)
        return self._normalized

    @property
    def raw(self) -> str:
        """Return the passed name without normalization."""
        return self._raw

    @property
    def valid(self) -> bool:
        """Return whether the package name is valid."""
        if self._valid is None:
            self._valid = Pep426.valid_name(self.raw)
        return self._valid


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

    __slots__ = (
        "_store",
        "_name",
        "_version",
        "data",
        "name",
        "save",
        "version",
    )

    def __init__(
        self, store: IStore, name: PackageName, version: PackageVersion
    ):
        """Create a python package instance."""
        self._store = store
        self._name = name
        self._version = version

    def __str__(self) -> str:
        """Return a string representation of the package."""
        return f"Package({self.name}, {self.version})"

    @property
    def data(self) -> bytes:
        """Return package data."""
        return b""

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
