__version_info__ = (1, 1, 5)
version = __version__ = "1.1.5"


def app(root=None,
        redirect_to_fallback=True,
        fallback_url=None,
        password_file=None,
        overwrite=False):
    import sys, os
    from pypiserver import core
    sys.modules.pop("pypiserver._app", None)
    __import__("pypiserver._app")
    _app = sys.modules["pypiserver._app"]

    import bottle

    if root is None:
        root = os.path.expanduser("~/packages")

    if fallback_url is None:
        fallback_url = "http://pypi.python.org/simple"

    _app.configure(root=root, redirect_to_fallback=redirect_to_fallback, fallback_url=fallback_url,
                   password_file=password_file, overwrite=overwrite)
    _app.app.module = _app

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

    redirect_to_fallback = local_conf.get("redirect_to_fallback", "").lower() in ("yes", "on", "1")
    fallback_url = local_conf.get("fallback_url")
    password_file = local_conf.get("password_file")
    return app(root=roots, redirect_to_fallback=redirect_to_fallback, fallback_url=fallback_url, password_file=password_file)
