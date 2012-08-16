__version_info__ = (0, 6, 2, 'dev')
version = __version__ = "0.6.2dev"


def app(root=None,
        redirect_to_fallback=True,
        fallback_url=None,
        password_file=None):
    import sys, os
    from pypiserver import core
    sys.modules.pop("pypiserver._app", None)
    __import__("pypiserver._app")
    _app = sys.modules["pypiserver._app"]

    import bottle

    if root is None:
        root = os.path.expanduser("~/packages")

    if fallback_url is None:
        fallback_url="http://pypi.python.org/simple"

    os.listdir(root)
    _app.configure(root=root, redirect_to_fallback=redirect_to_fallback, fallback_url=fallback_url,
                   password_file=password_file)
    _app.app.module = _app

    bottle.debug(True)
    return _app.app


def paste_app_factory(global_config, **local_conf):
    import os
    root = local_conf.get("root")
    if root and root.startswith("~"):
        root = os.path.expanduser(root)
    redirect_to_fallback = local_conf.get("redirect_to_fallback", "").lower() in ("yes", "on", "1")
    fallback_url = local_conf.get("fallback_url")
    password_file = local_conf.get("password_file")
    return app(root=root, redirect_to_fallback=redirect_to_fallback, fallback_url=fallback_url, password_file=password_file)
