import re as _re
version = __version__ = "1.1.9-dev.3"
__version_info__ = tuple(_re.split('[.-]', __version__))
__updated__ = "2015-12-20"

__title__ = "pypiserver"
__summary__ = "A minimal PyPI server for use with pip/easy_install."
__uri__ = "https://github.com/pypiserver/pypiserver"


def app(**kwds):
    from . import core, _app, bottle

    config, packages = core.configure(**kwds)
    _app.config = config
    _app.packages = packages
    _app.app.module = _app # HACK for testing.

    bottle.debug(True)
    return _app.app


def paste_app_factory(global_config, **local_conf):
    import os

    def _make_root(root):
        root = root.strip()
        if root.startswith("~"):
            return os.path.expanduser(root)
        return root

    root = local_conf.get("root")
    if root:
        roots = [_make_root(x) for x in root.split("\n") if x.strip()]
    else:
        roots = None

    redirect_to_fallback = local_conf.get(
        "redirect_to_fallback", "").lower() in ("yes", "on", "1")
    fallback_url = local_conf.get("fallback_url")
    password_file = local_conf.get("password_file")
    return app(root=roots, redirect_to_fallback=redirect_to_fallback, fallback_url=fallback_url, password_file=password_file)
