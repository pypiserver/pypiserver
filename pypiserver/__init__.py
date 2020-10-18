import functools
import pathlib
import re as _re
import sys
import typing as t

from pypiserver.config import Config, RunConfig, strtobool

version = __version__ = "2.0.0dev1"
__version_info__ = tuple(_re.split("[.-]", __version__))
__updated__ = "2020-10-11 11:23:15"

__title__ = "pypiserver"
__summary__ = "A minimal PyPI server for use with pip/easy_install."
__uri__ = "https://github.com/pypiserver/pypiserver"


identity = lambda x: x


def backwards_compat_kwargs(kwargs: dict, warn: bool = True) -> dict:
    backwards_compat = {
        "authenticated": ("authenticate", identity),
        "passwords": ("password_file", identity),
        "root": (
            "roots",
            lambda root: [
                pathlib.Path(r).expanduser().resolve()
                for r in ([root] if isinstance(root, str) else root)
            ],
        ),
        "redirect_to_fallback": (
            "disable_fallback",
            lambda redirect: not redirect,
        ),
        "server": ("server_method", identity),
        "welcome_file": (
            "welcome_msg",
            lambda p: pathlib.Path(p).expanduser().resolve().read_text(),
        ),
    }
    if warn and any(k in backwards_compat for k in kwargs):
        replacement_strs = (
            f"{k} with {backwards_compat[k][0]}"
            for k in filter(lambda k: k in kwargs, backwards_compat)
        )
        warn_str = (
            "You are using deprecated arguments. Please replace the following: \n"
            f"  {', '.join(replacement_strs)}"
        )
        print(warn_str, file=sys.stderr)

    rv_iter = (
        (
            (k, v)
            if k not in backwards_compat
            else (backwards_compat[k][0], backwards_compat[k][1](v))
        )
        for k, v in kwargs.items()
    )
    return dict(rv_iter)


def app(**kwargs):
    """
    :param dict kwds: Any overrides for defaults, as fetched by
        :func:`default_config()`. Check the docstring of this function
        for supported kwds.
    """
    config = Config.default_with_updates(**backwards_compat_kwargs(kwargs))
    return app_from_config(config)


def app_from_config(config: RunConfig):
    _app = __import__("_app", globals(), locals(), ["."], 1)
    sys.modules.pop("pypiserver._app", None)
    _app.config = config
    _app.iter_packages = config.iter_packages
    _app.package_root = config.package_root
    _app.app.module = _app  # HACK for testing.
    return _app.app


T = t.TypeVar("T")


def paste_app_factory(_global_config, **local_conf):
    """Parse a paste config and return an app.

    The paste config is entirely strings, so we need to parse those
    strings into values usable for the config, if they're present.
    """

    def to_bool(val: t.Optional[str]) -> t.Optional[bool]:
        return val if val is None else strtobool(val)

    def to_int(val: t.Optional[str]) -> t.Optional[int]:
        return val if val is None else int(val)

    def to_list(
        val: t.Optional[str],
        sep: str = " ",
        transform: t.Callable[[str], T] = str.strip,
    ) -> t.Optional[t.List[T]]:
        if val is None:
            return val
        return list(filter(None, map(transform, val.split(sep))))

    def _make_root(root: str) -> pathlib.Path:
        return pathlib.Path(root.strip()).expanduser().resolve()

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

    mapped_conf = {
        k: maps.get(k, lambda i: i)(v) for k, v in local_conf.items()
    }
    updated_conf = backwards_compat_kwargs(mapped_conf)

    return app(**updated_conf)


def _logwrite(logger, level, msg):
    if msg:
        line_endings = ["\r\n", "\n\r", "\n"]
        for le in line_endings:
            if msg.endswith(le):
                msg = msg[: -len(le)]
        if msg:
            logger.log(level, msg)
