import re as _re

version = __version__ = "1.2.0.dev1"
__version_info__ = tuple(_re.split('[.-]', __version__))
__updated__ = "2016-XX-XX"

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
        vars(self).update(d)


DEFAULT_SERVER = "auto"

def default_config(
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
        log_frmt = "%(asctime)s|%(name)s|%(levelname)s|%(thread)d|%(message)s",
        log_req_frmt = "%(bottle.request)s",
        log_res_frmt = "%(status)s",
        log_err_frmt = "%(body)s: %(exception)s \n%(traceback)s",
        welcome_file = None,
        cache_control = None,
        auther=None,
        VERSION=__version__):
    """
    Fetch default-opts with overridden kwds, capable of starting-up pypiserver.

    Does not validate overridden options.
    Example usage::

        kwds = pypiserver.default_config(<override_kwds> ...)
        ## More modifications on kwds.
        pypiserver.app(**kwds)``.

    Kwds correspond to same-named cmd-line opts, with '-' --> '_' substitution.
    Non standard args are described below:

    :param return_defaults_only:
            When `True`, returns defaults, otherwise,
            configures "runtime" attributes and returns also the "packages"
            found in the roots.
    :param root:
            A list of paths, derived from the packages specified on cmd-line.
    :param redirect_to_fallback:
            see :option:`--disable-fallback`
    :param authenticated:
            see :option:`--authenticate`
    :param password_file:
            see :option:`--passwords`
    :param log_file:
            see :option:`--log-file`
            Not used, passed here for logging it.
    :param log_frmt:
            see :option:`--log-frmt`
            Not used, passed here for logging it.
    :param callable auther:
            An API-only options that if it evaluates to a callable,
            it is invoked to allow access to protected operations
            (instead of htpaswd mechanism) like that::

                auther(username, password): bool

            When defined, `password_file` is ignored.
    :param host:
            see :option:`--interface`
            Not used, passed here for logging it.
    :param port:
            see :option:`--port`
            Not used, passed here for logging it.
    :param server:
            see :option:`--server`
            Not used, passed here for logging it.
    :param verbosity:
            see :option:`-v`
            Not used, passed here for logging it.
    :param VERSION:
            Not used, passed here for logging it.

    :return: a dict of defaults

    """
    return locals()


def app(**kwds):
    """
    :param dict kwds:
            Any overrides for defaults, as fetched by :func:`default_config()`.
            Check the docstring of this function for supported kwds.
    """
    from . import core, _app

    kwds = default_config(**kwds)
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
        c['root'] = [_make_root(x) for x in root.split("\n") if x.strip()]

    upd_bool_attr_from_dict_str_item(c, 'redirect_to_fallback', local_conf)
    upd_bool_attr_from_dict_str_item(c, 'overwrite', local_conf)

    return app(**vars(c))

def _logwrite(logger, level, msg):
    if msg:
        line_endings = ['\r\n', '\n\r', '\n']
        for le in line_endings:
            if msg.endswith(le):
                msg = msg[:-len(le)]
        if msg:
            logger.log(level, msg)
