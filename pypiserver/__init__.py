import re as _re

version = __version__ = "1.1.9-dev.3"
__version_info__ = tuple(_re.split('[.-]', __version__))
__updated__ = "2015-12-20"

__title__ = "pypiserver"
__summary__ = "A minimal PyPI server for use with pip/easy_install."
__uri__ = "https://github.com/pypiserver/pypiserver"


class Configuration(object):
    """
    .. see:: config-options: :func:`pypiserver.configure()`
    """

    def __init__(self, **kwds):
        vars(self).update(kwds)

    def __repr__(self, *args, **kwargs):
        return 'Configuration(**%s)' % vars(self)

    def __str__(self, *args, **kwargs):
        return 'Configuration:\n%s' % '\n'.join('%20s = %s' % (k, v)
                for k, v in sorted(vars(self).items()))

    def update(self, props):
        d = props if isinstance(props, dict) else vars(props)
        vars(self).update(props)


DEFAULT_SERVER = "auto"

def default_config():
    c = Configuration(
        VERSION=version,
        root=None,
        host = "0.0.0.0",
        port = 8080,
        server = DEFAULT_SERVER,
        redirect_to_fallback = True,
        fallback_url = None,
        authenticated = ['update'],
        password_file = None,
        overwrite = False,
        hash_algo = 'md5',
        verbosity = 1,
        log_file = None,
        log_frmt = "%(asctime)s|%(levelname)s|%(thread)d|%(message)s",
        log_req_frmt = "%(bottle.request)s",
        log_res_frmt = "%(status)s",
        log_err_frmt = "%(body)s: %(exception)s \n%(traceback)s",
        welcome_file = None,
        cache_control = None,
    )

    return c

def app(**kwds):
    """
    :param dict kwds:
            May use ``**vars(default_config())`.
    """
    from . import core, _app, bottle

    bottle.debug(True)
    config, packages = core.configure(**kwds)
    _app.config = config
    _app.packages = packages
    _app.app.module = _app # HACK for testing.

    return _app.app

def str2bool(s, default):
    if s is not None and s != '':
        return s.lower() not in ("no", "off", "0", "false")
        return default

def paste_app_factory(global_config, **local_conf):
    import os

    def upd_bool_attr_from_dict_str_item(conf, attr, sdict):
        setattr(conf, attr, str2bool(sdict.pop(attr, None), getattr(conf, attr)))

    def _make_root(root):
        root = root.strip()
        if root.startswith("~"):
            return os.path.expanduser(root)
        return root

    c = default_config()

    root = local_conf.get("root")
    if root:
        c.root = [_make_root(x) for x in root.split("\n") if x.strip()]

    upd_bool_attr_from_dict_str_item(c, 'redirect_to_fallback', local_conf)
    upd_bool_attr_from_dict_str_item(c, 'overwrite', local_conf)

    return app(**vars(c))
