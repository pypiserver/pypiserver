__version_info__ = (0, 5, 2)
version = __version__ = "0.5.2"


def app(root=None,
        redirect_to_fallback=True,
        fallback_url=None):
    import os
    from pypiserver import core
    import bottle

    if root is None:
        root = os.path.expanduser("~/packages")

    if fallback_url is None:
        fallback_url="http://pypi.python.org/simple"

    os.listdir(root)
    core.packages = core.pkgset(root)
    core.config.redirect_to_fallback = redirect_to_fallback
    core.config.fallback_url = fallback_url
    bottle.debug(True)
    return bottle.default_app()


def paste_app_factory(global_config, **local_conf):
    root = local_conf.get("root")
    redirect_to_fallback = local_conf.get("redirect_to_fallback", "").lower() in ("yes", "on", "1")
    fallback_url = local_conf.get("fallback_url")
    return app(root=root, redirect_to_fallback=redirect_to_fallback, fallback_url=fallback_url)
