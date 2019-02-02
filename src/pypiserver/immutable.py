"""Utilities to make immutability easier.

This module defines `ImmutableStatic`, `Immutable`, and `Freezable`
classes. Inherit from these classes to use their properties. Note that
none of the immutability conferred by these classes extends to their
attributes. If `immutable.a` is a dict, the dict does not magically
become immutable, at least not yet.

`ImmutableStatic` classes may not be instantiated. Static attributes and
methods (class or static) may be specified in the class definition, but
may not be altered thereafter.

`Immutable` classes may be instantiated, but neither instances or class
references are mutable.

`Freezable` classes are mutable by default, but provide a `.freeze()`
method to convert them to an immutable state. A `.thaw()` method is also
provided to make them mutable again.

Attempting to assign a value to an immutable or frozen class or instance
will raise a subclass of `AttributeError`, either `ImmutableAssignmentError`
or `FrozenAssignmentError` as appropriate.

Attempting to instantiate an `ImmutableStatic` class will raise a
subclass of `TypeError`, `ImmutableInstantiationError`.
"""

import typing as t
from functools import wraps


class ImmutableInstantiationError(TypeError):
    """An immutable static class may not be instantiated."""


class ImmutableAssignmentError(AttributeError):
    """An attribute could not be set because the object is immutable."""


class FrozenAssignmentError(AttributeError):
    """An attribute could not be set because the object is frozen."""


class _ImmutableStaticMeta(type):
    """Metaclass to prevent setting of instance attributes post-creation."""

    @staticmethod
    def _instance_init(inst, *_, **__):
        """Prevent ImmutableStatic classes from being instantiated."""
        raise ImmutableInstantiationError(
            "{} is immutably static and may not be instantiated".format(
                inst.__class__.__name__
            )
        )

    @staticmethod
    def _instance_setattr(inst, _, __):
        """Disallow setting of instance attributes."""
        raise ImmutableAssignmentError(
            "{} is immutable".format(inst.__class__.__name__)
        )

    def __new__(  # nopep8
        cls: "t.Type[_ImmutableStaticMeta]",
        name: str,
        bases: t.Tuple[type, ...],
        dct: t.Dict[str, t.Any],
    ):
        """Create the class object."""
        dct["__init__"] = cls._instance_init
        dct["__setattr__"] = cls._instance_setattr
        return super().__new__(cls, name, bases, dct)

    def __setattr__(cls, attr, val):  # nopep8
        """Disallow setting of class attributes."""
        raise ImmutableAssignmentError("{} is immutable".format(cls.__name__))


class ImmutableStatic(metaclass=_ImmutableStaticMeta):
    """An immutably static class.

    ImmutableStatic classes may not be instantiated, and their attributes
    may not be set dynamically.
    """


class _ImmutableMeta(type):
    """A metaclass disabling instance mutation after instantiation."""

    @staticmethod
    def _wrap_init(kls, init):
        """Wrap the initializer of a class instance."""

        @wraps(init)
        def new_init(inst, *args, **kwargs):
            """Ensure we cannot set values post-init."""
            # pylint: disable=protected-access
            kls._kls_frozen = False
            object.__setattr__(inst, "_inst_frozen", False)

            delay_freeze = kwargs.pop("delay_freeze", False)

            init(inst, *args, **kwargs)

            if not delay_freeze:
                kls._kls_frozen = True
                object.__setattr__(inst, "_inst_frozen", True)

        return new_init

    @staticmethod
    def _instance_setattr(inst, attr, val):
        """Disallow setting attributes once frozen."""
        if inst._inst_frozen:  # pylint: disable=protected-access
            raise ImmutableAssignmentError(
                "{} is immutable".format(inst.__class__.__name__)
            )
        object.__setattr__(inst, attr, val)

    @staticmethod
    def _get_init(bases: t.Tuple[type, ...]):
        """Return any init method present in bases."""
        for base in bases:  # pylint: disable=not-an-iterable
            if "__init__" in base.__dict__:
                return base.__dict__["__init__"]

        return lambda self, *_, **__: object.__init__(self)

    def __new__(  # nopep8
        cls: "t.Type[_ImmutableMeta]",
        name: str,
        bases: t.Tuple[type, ...],
        dct: t.Dict[str, t.Any],
    ):
        """Create the class object."""
        dct["_kls_frozen"] = True
        dct["_inst_frozen"] = False
        if "__init__" in dct:
            dct["__init__"] = cls._wrap_init(cls, dct["__init__"])
        else:
            dct["__init__"] = cls._wrap_init(cls, cls._get_init(bases))
        dct["__setattr__"] = cls._instance_setattr
        return super().__new__(cls, name, bases, dct)

    def __setattr__(cls, attr, val):  # nopep8
        """Disallow setting class attributes while class is frozen."""
        if attr != "_kls_frozen" and cls._kls_frozen:
            raise ImmutableAssignmentError(
                "{} is immutable".format(cls.__name__)
            )
        super().__setattr__(attr, val)


class Immutable(metaclass=_ImmutableMeta):
    """A class that may have instances but not be mutated.

    The `Immutable` class may have any attributes assigned to it desired
    in class construction. In addition, instance attributes may be set
    in the `__init__()` method.

    However, the class may not have attributes assigned or altered
    outside of its initial constructor. Similarly, instances may not
    have instance attributes assigned or altered after the class is
    instantiated.

    Immutable classes may serve as parent classes, and things generally
    work as expected. However, it is important to note that the
    `__init__()` method generally has a hook on it to freeze the
    instance, so if you call `super().__init__()` early in your
    child class' `__init__()` method, you may find that instance
    attributes are then unsettable, even inside `__init__()`! There
    are two solutions to this. The first is to put the `super().__init__()`
    call at the bottom of the child class' `__init_()` method. The
    other is to call `super().__init__()` with the keyword argument
    `delay_freeze=True`. `super().__init__(delay_freeze=True)` will,
    as you might imagine, delay freezing the class until the end of
    the sub-class' `__init__()`. PyLint may yell at you about the parent's
    `__init__()` not expecting the `delay_freeze` argument, but not to
    worry. PyLint is wrong, and the argument will be popped before the
    parent `__init__()` is called.
    """


class _FreezableMeta(type):
    """A metaclass for instances that can be frozen and unfrozen."""

    def __init__(  # nopep8
        cls: "_FreezableMeta",
        name: str,
        bases: t.Tuple[type, ...],
        dct: t.Dict[str, t.Any],
    ):
        """Create the class object."""

        super().__init__(name, bases, dct)

        def instance_setattr(self, attr: str, val: t.Any):
            """Disallow setting of instance attributes."""
            if self._frozen:  # pylint: disable=protected-access
                raise FrozenAssignmentError(
                    "{} is frozen".format(self.__class__.__name__)
                )
            else:
                object.__setattr__(self, attr, val)

        def freeze(self):
            """Freeze the instance."""
            # pylint: disable=protected-access
            if not self._frozen:
                self._frozen = True

        def thaw(self):
            """Unfreeze the instance."""
            if self._frozen:  # pylint: disable=protected-access
                object.__setattr__(self, "_frozen", False)

        cls._frozen = False
        cls.freeze = freeze
        cls.thaw = thaw
        setattr(cls, "__setattr__", instance_setattr)


class Freezable(metaclass=_FreezableMeta):
    """A class that may not be mutated outside of the __init__ method."""
