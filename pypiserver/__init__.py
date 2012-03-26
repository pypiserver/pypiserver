__version_info__ = (0, 5, 2)
version = __version__ = "0.5.2"


def app(root=None,
        redirect_to_fallback=True,
        fallback_url="http://pypi.python.org/simple"):
    import os
    from pypiserver import core
    import bottle

    if root is None:
        root = os.path.expanduser("~/packages")
    os.listdir(root)
    core.packages = core.pkgset(root)
    core.config.redirect_to_fallback = redirect_to_fallback
    core.config.fallback_url = fallback_url
    bottle.debug(True)
    return bottle.default_app()
