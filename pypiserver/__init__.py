import functools
import pathlib
import re as _re
import sys
import typing as t

from pypiserver.bottle import Bottle
from pypiserver.config import Config, RunConfig, strtobool

version = __version__ = "2.0.0dev1"
__version_info__ = tuple(_re.split("[.-]", __version__))
__updated__ = "2020-10-11 11:23:15"

__title__ = "pypiserver"
__summary__ = "A minimal PyPI server for use with pip/easy_install."
__uri__ = "https://github.com/pypiserver/pypiserver"


identity = lambda x: x


def backwards_compat_kwargs(kwargs: dict, warn: bool = True) -> dict:
    """Return a dict with deprecated kwargs converted to new kwargs.

    :param kwargs: the incoming kwargs to convert
    :param warn: whether to output a warning to stderr if there are deprecated
        kwargs found in the incoming kwargs
    """
    # A mapping of deprecated kwargs to a 2-tuple of their corresponding updated
    # kwarg and a function to convert the value of the deprecated kwarg to a
    # value for the new kwarg. `identity` is just a function that returns
    # whatever it is passed and is used in cases where the only change from
    # a legacy kwarg is its name.
    backwards_compat = {
        "authenticated": ("authenticate", identity),
        "passwords": ("password_file", identity),
        # `root` could be a string or an array of strings. Handle both cases,
        # converting strings to Path instances.
        "root": (
            "roots",
            lambda root: [
                # Convert strings to absolute Path instances
                pathlib.Path(r).expanduser().resolve()
                for r in ([root] if isinstance(root, str) else root)
            ],
        ),
        # `redirect_to_fallback` was changed to `disable_fallback` for clearer
        # use as a flag to disable the default behavior. Since its behavior
        # is the opposite, we negate it.
        "redirect_to_fallback": (
            "disable_fallback",
            lambda redirect: not redirect,
        ),
        "server": ("server_method", identity),
        # `welcome_msg` now is just provided as text, so that anyone using
        # pypiserver as a library doesn't need to worry about distributing
        # files if they don't need to. If we're still passed an old-style
        # `welcome_file` argument, we go ahead and resolve it to an absolute
        # path and read the text.
        "welcome_file": (
            "welcome_msg",
            lambda p: pathlib.Path(p).expanduser().resolve().read_text(),
        ),
    }
    # Warn the user if they're using any deprecated arguments
    if warn and any(k in backwards_compat for k in kwargs):
        # Make nice instructions like `Please replace the following:
        # 'authenticated' with 'authenticate'` and print to stderr.
        replacement_strs = (
            f"'{k}' with '{backwards_compat[k][0]}'"
            for k in filter(lambda k: k in kwargs, backwards_compat)
        )
        warn_str = (
            "You are using deprecated arguments. Please replace the following: \n"
            f"  {', '.join(replacement_strs)}"
        )
        print(warn_str, file=sys.stderr)

    # Create an iterable of 2-tuple to collect into the updated dictionary. Each
    # item will either be the existing key-value pair from kwargs, or, if the
    # keyword is a legacy keyword, the new key and potentially adjusted value
    # for that keyword. Note that depending on the order the argument are
    # specified, this _could_ mean an updated legacy keyword could override
    # a new argument if that argument is also specified. However, in that
    # case, our updated kwargs dictionary would have a different number of
    # keys compared to our incoming dictionary, so we check for that case
    # below.
    rv_iter = (
        (
            (k, v)
            if k not in backwards_compat
            else (backwards_compat[k][0], backwards_compat[k][1](v))
        )
        for k, v in kwargs.items()
    )
    updated_kwargs = dict(rv_iter)

    # If our dictionaries have different lengths, we must have gotten duplicate
    # legacy/modern keys. Figure out which keys were dupes and throw an error.
    if len(updated_kwargs) != len(kwargs):
        legacy_to_modern = {k: v[0] for k, v in backwards_compat.items()}
        dupes = [
            (k, v)
            for k, v in legacy_to_modern.items()
            if k in kwargs and v in kwargs
        ]
        raise ValueError(
            "Keyword arguments for pypiserver app() constructor contained "
            "duplicate legacy and modern keys. Duplicates are shown below, in "
            "the form (legacy_key, modern_key):\n"
            f"{dupes}"
        )

    return updated_kwargs


def app(**kwargs: t.Any) -> Bottle:
    """Construct a bottle app running pypiserver.

    :param kwds: Any overrides for defaults. Any property of RunConfig
        (or its base), defined in `pypiserver.config`, may be overridden.
    """
    config = Config.default_with_overrides(**backwards_compat_kwargs(kwargs))
    return app_from_config(config)


def app_from_config(config: RunConfig) -> Bottle:
    """Construct a bottle app from the provided RunConfig."""
    # The _app module instantiates a Bottle instance directly when it is
    # imported. That is `_app.app`. We directly mutate some global variables
    # on the imported `_app` module so that its endpoints will behave as
    # we expect.
    _app = __import__("_app", globals(), locals(), ["."], 1)
    # Because we're about to mutate our import, we pop it out of the imported
    # modules map, so that any future imports do not receive our mutated version
    sys.modules.pop("pypiserver._app", None)
    _app.config = config
    # Add a reference to our config on the Bottle app for easy access in testing
    # and other contexts.
    _app.app._pypiserver_config = config
    return _app.app


T = t.TypeVar("T")


def paste_app_factory(_global_config, **local_conf):
    """Parse a paste config and return an app.

    The paste config is entirely strings, so we need to parse those
    strings into values usable for the config, if they're present.
    """

    def to_bool(val: t.Optional[str]) -> t.Optional[bool]:
        """Convert a string value, if provided, to a bool."""
        return val if val is None else strtobool(val)

    def to_int(val: t.Optional[str]) -> t.Optional[int]:
        """Convert a string value, if provided, to an int."""
        return val if val is None else int(val)

    def to_list(
        val: t.Optional[str],
        sep: str = " ",
        transform: t.Callable[[str], T] = str.strip,
    ) -> t.Optional[t.List[T]]:
        """Convert a string value, if provided, to a list.

        :param sep: the separator between items in the string representation
            of the list
        :param transform: an optional function to call on each string item of
            the list
        """
        if val is None:
            return val
        return list(filter(None, map(transform, val.split(sep))))

    def _make_root(root: str) -> pathlib.Path:
        """Convert a specified string root into an absolute Path instance."""
        return pathlib.Path(root.strip()).expanduser().resolve()

    # A map of config keys we expect in the paste config to the appropriate
    # function to parse the string config value. This map includes both
    # current and legacy keys.
    maps = {
        "cache_control": to_int,
        "roots": functools.partial(to_list, sep="\n", transform=_make_root),
        # root is a deprecated argument for roots
        "root": functools.partial(to_list, sep="\n", transform=_make_root),
        "disable_fallback": to_bool,
        # redirect_to_fallback is a deprecated argument for disable_fallback
        "redirect_to_fallback": to_bool,
        "overwrite": to_bool,
        "authenticate": functools.partial(to_list, sep=" "),
        # authenticated is a deprecated argument for authenticate
        "authenticated": functools.partial(to_list, sep=" "),
        "verbosity": to_int,
    }

    # First, convert values from strings to whatever types we need, or leave
    # them as strings if there's no mapping function available for them.
    mapped_conf = {k: maps.get(k, identity)(v) for k, v in local_conf.items()}
    # Convert any legacy key/value pairs into their modern form.
    updated_conf = backwards_compat_kwargs(mapped_conf)

    return app(**updated_conf)
