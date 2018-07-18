"""Utilities for plugin definition."""

from abc import abstractmethod


class py2_abstractclassmethod(classmethod):
    """An implementation of @abstractclassmethod for Python 2."""

    __isabstractmethod__ = True

    def __init__(self, callable):
        """Mark a callable classmethod as an abstract method.

        :param Callable callable: a callable to mark
        """
        callable.__isabstractmethod__ = True
        super(py2_abstractclassmethod, self).__init__(callable)


def py3_abstractproperty(callable):
    """Create the equivalent of a Python 2 @abstractproperty.

    While @abstractproperty still exists in Python 3, it was deprecated
    in Python 3.3, and will probably be removed at some point. This
    decorator is equivalent.

    :param Callable callable: the callable to mark as an abstract
        property
    """
    return property(abstractmethod(callable))
