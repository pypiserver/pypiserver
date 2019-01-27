"""Simple test doubles, for when unittest.mock is too heavy."""

import typing as t


class Namespace:
    """A generic, configurable namespace."""

    def __init__(self, **kwargs):
        """Create the namespace, with kwargs converted to attributes."""
        for k, v in kwargs.items():
            setattr(self, k, v)


class Call:
    """A tracked call of a callable."""

    CallTuple = t.Tuple[t.Tuple, t.Dict[str, t.Any]]

    def __init__(self, args: t.Tuple, kwargs: t.Dict[str, t.Any]):
        """Instantiate the call."""
        self.args = args
        self.kwargs = kwargs

    def __eq__(self, other):
        """Check if a call is equivalent to another call."""
        if isinstance(other, self.__class_):
            return self.args == other.args and self.kwargs == other.kwargs
        elif isinstance(other, self.CallTuple):
            return self.args == other[0] and self.kwargs == other [1]
        raise TypeError(
            "{} must be Call or call tuple, not {}".format(other, type(other))
        )


class Calls:
    """A list of calls with some extra utilities added."""

    def __init__(self):
        """Instantiate the call list."""
        self._calls = []

    def __contains__(self, call: Call):
        """Check whether the list contains a call."""
        return call in self._calls

    def __getattr__(self, attr: str):
        """Proxy unknown attributes to the inner list."""
        return getattr(self._calls, attr)

    def __getitem__(self, index: int) -> Call:
        """Get a call from the list at the given index."""
        return self._calls[index]

    def __len__(self) -> int:
        """Return the length of the call list."""
        return len(self._calls)

    def append(self, call: Call) -> None:
        """Add a call to the cal list."""
        self._calls.append(call)

    @property
    def count(self) -> int:
        """Return the number of calls in the call list."""
        return len(self._calls)


class Spy:
    """A simple callable that tracks its calls."""

    def __init__(self, returns: t.Any = None):
        """Create the spy."""
        self.calls: Calls = Calls()
        self.returns = returns

    def __call__(self, *args, **kwargs):
        """Return any provided return value and store the call."""
        self.calls.append(Call(args, kwargs))
        return self.returns
