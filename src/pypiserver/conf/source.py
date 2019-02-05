"""Sources for commands and their arguments."""

from enum import Enum


class Source(Enum):
    """Enumerate option sources and provide convenience methods."""

    NONE = 0
    CONF = 1
    ENV = 2
    ARGS = 4

    def __or__(self, other: "Source"):
        """Implement binary OR."""
        return self.value | other.value

    def __ror__(self, other: "Source"):
        """Implement binary OR."""
        if isinstance(other, int):
            return other | self.value
        return other.value | self.value

    def __and__(self, other: "Source"):
        """Implement binary AND."""
        return self.value & other.value

    def __rand__(self, other: "Source"):
        """Implement binary AND."""
        if isinstance(other, int):
            return other & self.value
        return other.value & self.value

    @classmethod
    def conf(cls, src: int) -> bool:
        """Return whether sources include the config."""
        return cls.CONF.value & src == cls.CONF.value

    @classmethod
    def env(cls, src: int) -> bool:
        """Return whether sources include the environment."""
        return cls.ENV.value & src == cls.ENV.value

    @classmethod
    def args(cls, src: int) -> bool:
        """Return whether sources include commandline arguments."""
        return cls.ARGS.value & src == cls.ARGS.value
