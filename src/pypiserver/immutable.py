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


class _ImmutableMeta(type):
    """A metaclass disabling mutation after instantiation."""

    def __init__(  # nopep8
        cls: "_ImmutableMeta",
        name: str,
        bases: t.Tuple[type, ...],
        dct: t.Dict[str, t.Callable],
    ):
        """Create the class object."""

        super().__init__(name, bases, dct)

        def instance_setattr(self, attr, val):
            """Disallow setting of instance attributes."""
            if getattr(self, "_frozen", False):
                raise TypeError(
                    "{} is immutable".format(self.__class__.__name__)
                )
            else:
                object.__setattr__(self, attr, val)

        def default_init(self, *args, **kwargs):
            """Just a regular old init that we can wrap."""
            object.__init__(self, *args, **kwargs)

        def wrap_init(init_func):
            """Return a wrapped version of the class' __init__ method."""

            def init_wrapper(self, *args, **kwargs):
                """Instantiate the class, then freeze it."""
                init_func(self, *args, **kwargs)
                self._frozen = True  # pylint: disable=protected-access

            return init_wrapper

        if "__init__" in dct:
            setattr(cls, "__init__", wrap_init(dct["__init__"]))
        else:
            setattr(cls, "__init__", wrap_init(default_init))

        setattr(cls, "__setattr__", instance_setattr)


class Immutable(metaclass=_ImmutableMeta):
    """A class that may not be mutated outside of the __init__ method."""
