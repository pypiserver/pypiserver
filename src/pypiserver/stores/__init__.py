"""Storage backends for pypiserver."""


class IStore:
    """Storage interface."""

    def package_bytes(self, package) -> bytes:
        """Return package bytes."""
        pass

    def save_package(self, package) -> None:
        """Save package."""
        pass

    def remove_package(self, package) -> None:
        """Delete package."""
        pass
