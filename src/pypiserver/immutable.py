"""Utilities to make immutability easier."""

import typing as t


class _ImmutableStaticMeta(type):
    """Metaclass to prevent setting of instance attributes post-creation."""

    def __new__(  # nopep8
        cls: "t.Type[_ImmutableStaticMeta]",
        name: str,
        bases: t.Tuple[type, ...],
        dct: t.Dict[str, t.Callable],
    ):
        """Create the class object."""

        def instance_init(self, *_, **__):
            """Prevent ImmutableStatic classes from being instantiated."""
            raise TypeError(
                "{} is immutably static and may not be instantiated".format(
                    self.__class__.__name__
                )
            )

        def instance_setattr(self, _, __):
            """Disallow setting of instance attributes."""
            raise TypeError("{} is immutable".format(self.__class__.__name__))

        dct["__init__"] = instance_init
        dct["__setattr__"] = instance_setattr

        return super().__new__(cls, name, bases, dct)

    def __setattr__(cls, attr, val):  # nopep8
        """Disallow setting of class attributes."""
        raise TypeError("{} is immutable".format(cls.__name__))


class ImmutableStatic(metaclass=_ImmutableStaticMeta):
    """An immutably static class.

    ImmutableStatic classes may not be instantiated, and their attributes
    may not be set dynamically.
    """
