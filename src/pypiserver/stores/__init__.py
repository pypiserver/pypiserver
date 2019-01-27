"""Storage backends for pypiserver."""


class IStore:
    """Storage interface."""

    def package_bytes(self, package) -> bytes:
        pass

    def save_package(self, package) -> None:
        pass

    def remove_package(self, package) -> None:
        pass
