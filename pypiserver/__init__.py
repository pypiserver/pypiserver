import re as _re
version = __version__ = "1.1.9-dev.3"
__version_info__ = tuple(_re.split('[.-]', __version__))
__updated__ = "2015-12-20"

__title__ = "pypiserver"
__summary__ = "A minimal PyPI server for use with pip/easy_install."
__uri__ = "https://github.com/pypiserver/pypiserver"


def app(**kwds):
    from . import core, _app, bottle

    bottle.debug(True)
    config, packages = core.configure(**kwds)
    _app.config = config
    _app.packages = packages
    _app.app.module = _app # HACK for testing.

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

    def str2bool(s, default):
        if s is not None and s != '':
            return s.lower() not in ("no", "off", "0", "false")
        return default

    redirect_to_fallback = str2bool(
            local_conf.pop('redirect_to_fallback', None), True)
    overwrite = str2bool(local_conf.get('overwrite', None), False)
    return app(root=roots,
            redirect_to_fallback=redirect_to_fallback, overwrite=overwrite,
            **local_conf)
