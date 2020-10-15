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


def backwards_compat_kwargs(kwargs: dict) -> dict:
    backwards_compat = {
        "root": (
            "roots",
            lambda root: [pathlib.Path(r).expanduser().resolve() for r in root],
        ),
        "server": ("server_method", identity),
        "redirect_to_fallback": (
            "disable_fallback",
            lambda redirect: not redirect,
        ),
        "authenticated": ("authenticate", identity),
        "welcome_file": (
            "welcome_msg",
            lambda p: pathlib.Path(p).expanduser().resolve().read_text(),
        ),
    }
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


def paste_app_factory(global_config, **local_conf):
    """Parse a paste config and return an app.

    The paste config is entirely strings, so we need to parse those
    strings into values usable for the config, if they're present.
    """

    def to_bool(val: t.Optional[str]) -> t.Optional[bool]:
        return val if val is None else strtobool(val)

    def to_int(val: t.Optional[str]) -> t.Optional[int]:
        return val if val is None else int(val)

    def to_list(
        val: str, sep: str = " ", transform: t.Callable[[str], T] = str.strip
    ) -> t.Optional[t.List[T]]:
        if val is None:
            return val
        return list(filter(None, map(transform, val.split(sep))))

    def _make_root(root: str) -> pathlib.Path:
        return pathlib.Path(root.strip()).expanduser().resolve()

    deprecated_args = {
        "redirect_to_fallback": "disable_fallback",
        "authenticated": "authenticate",
        "root": "roots",
    }

    if any(k in local_conf for k in deprecated_args):
        replacements_strs = (
            f"{k} with {deprecated_args[k]}"
            for k in (k for k in deprecated_args if k in local_conf)
        )
        warn_str = (
            "You are using deprecated arguments. Please replace the following: \n"
            "  {', '.join(replacement_strs)}"
        )
        print(warn_str, file=sys.stderr)

    _config_updates = {
        "cache_control": to_int(local_conf.get("cache_control")),
        "overwrite": to_bool(local_conf.get("overwrite")),
        "disable_fallback": (
            to_bool(local_conf["disable_fallback"])
            if "disable_fallback" in local_conf
            # Support old-style config arguments
            else (
                # Because we need to negate this, don't juse pass the
                # .get("redirect_to_fallback") to `to_bool`, because we want
                # to retain the `None` if it's abasent, rather than negating
                # it and turning it into a True
                not to_bool(local_conf["redirect_to_fallback"])
                if "disable_fallback" in local_conf
                else None
            )
        ),
        "authenticate": to_list(
            # Support old-style config arguments
            local_conf.get("authenticate", local_conf.get("authenticated")),
            sep=" ",
        ),
        "roots": to_list(
            # Support old-style config arguments
            local_conf.get("roots", local_conf.get("root")),
            sep="\n",
            transform=_make_root,
        ),
        "verbosity": to_int(local_conf.get("verbosity")),
    }

    # Items requiring no tranformation
    str_items = (
        "fallback_url",
        "hash_algo",
        "log_err_frmt",
        "log_file",
        "log_frmt",
        "log_req_frmt",
        "log_res_frmt",
        "password_file",
        "welcome_file",
    )

    _config_updates = {
        **_config_updates,
        **{k: local_conf.get(k) for k in str_items},
    }

    config_updates = {k: v for k, v in _config_updates.items() if v is not None}

    # cache_control is undocumented; don't know what type is expected:
    # upd_conf_with_str_item(c, 'cache_control', local_conf)

    return app(**config_updates)


def _logwrite(logger, level, msg):
    if msg:
        line_endings = ["\r\n", "\n\r", "\n"]
        for le in line_endings:
            if msg.endswith(le):
                msg = msg[: -len(le)]
        if msg:
            logger.log(level, msg)
