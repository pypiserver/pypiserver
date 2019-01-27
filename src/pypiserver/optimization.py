"""Code enabling what optimizations may be easily made generically."""

import typing as t
from collections import OrderedDict
from functools import partial, wraps


def _prune_odict(when_len: int, odict: OrderedDict, count: int = 1) -> None:
    """Remove the items from the ordered dict if it contains the max."""
    if len(odict) == when_len:
        for _ in range(count):
            odict.popitem(last=False)


def _args_kwargs_to_dict_key(
    args: t.Tuple[t.Hashable, ...], kwargs: t.Dict[str, t.Hashable]
) -> t.Tuple[t.Hashable, ...]:
    """Convert args and kwargs to a potentially hashable format."""
    return (*args, *kwargs.items())


def memoize(max_records: int = 0) -> t.Callable:
    """Memoize functions results.

    Currently only appropriate for functions whose call values are
    automatically hashable.

    Params:
        max_records: the maximum number of records to store. The special
            value 0 indicates that infinite records should be stored.
    """

    if max_records:
        prune: t.Callable[[OrderedDict], None] = partial(
            _prune_odict, max_records
        )
    else:
        prune = lambda *x, **y: None

    def create_decorator(func: t.Callable) -> t.Callable:
        """Generate the decorator."""
        results: OrderedDict[t.Tuple[t.Hashable, ...], t.Any] = OrderedDict()

        @wraps(func)
        def wrapper(*args: t.Hashable, **kwargs: t.Hashable) -> t.Any:
            """Attempt to memoize function results."""
            arg_key = _args_kwargs_to_dict_key(args, kwargs)
            try:
                return results[arg_key]
            except KeyError:
                prune(results)
                res = func(*args, **kwargs)
                try:
                    results[arg_key] = res
                except TypeError as e:
                    raise TypeError(
                        "Memoized function {} received unhashable "
                        "arguments: {}".format(func.__name__, (args, kwargs))
                    ) from e
                return res

        return wrapper

    return create_decorator
