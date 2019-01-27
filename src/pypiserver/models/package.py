"""Model(s) related to a python package."""

from pypiserver.optimization import memoize
from .compliance import Pep426, Pep503


class PackageName:
    """A python package name."""

    __slots__ = (
        'normalized',
        'raw',
        'valid',
    )

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


class PackageVersion:
    """A python package version."""

    __slots__ = (
        'raw',
    )

    def __init__(self, version: str):
        """Create a version instance."""
        self.raw = version

    def __str__(self) -> str:
        """Return a friendly representation of the version."""
        return f"'{self.raw}'"

    def __repr__(self) -> str:
        """Return a string representation of the version."""
        return f"PackageVersion('{self.raw}'"


class Package:
    """A python package."""

    __slots__ = ('name', 'version')

    def __init__(self, name: PackageName, version: PackageVersion):
        """Create a python package instance."""
        self.name = name
        self.version = version

    def __str__(self) -> str:
        """Return a string representation of the package."""
        return f"Package({self.name}, {self.version})"
