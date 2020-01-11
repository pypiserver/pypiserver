import os
import re as _re
import sys

version = __version__ = "1.3.2"
__version_info__ = tuple(_re.split('[.-]', __version__))
__updated__ = "2020-01-11 17:25:20"

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
        host="0.0.0.0",
        port=8080,
        server=DEFAULT_SERVER,
        redirect_to_fallback=True,
        fallback_url=None,
        authenticated=['update'],
        password_file=None,
        overwrite=False,
        hash_algo='md5',
        verbosity=1,
        log_file=None,
        log_frmt="%(asctime)s|%(name)s|%(levelname)s|%(thread)d|%(message)s",
        log_req_frmt="%(bottle.request)s",
        log_res_frmt="%(status)s",
        log_err_frmt="%(body)s: %(exception)s \n%(traceback)s",
        welcome_file=None,
        cache_control=None,
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
            If `None`, defaults to '~/packages'.
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
    :param dict kwds: Any overrides for defaults, as fetched by
        :func:`default_config()`. Check the docstring of this function
        for supported kwds.
    """
    from . import core

    _app = __import__("_app", globals(), locals(), ["."], 1)
    sys.modules.pop('pypiserver._app', None)

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


def _str_strip(string):
    """Provide a generic strip method to pass as a callback."""
    return string.strip()


def paste_app_factory(global_config, **local_conf):
    """Parse a paste config and return an app."""

    def upd_conf_with_bool_item(conf, attr, sdict):
        conf[attr] = str2bool(sdict.pop(attr, None), conf[attr])

    def upd_conf_with_str_item(conf, attr, sdict):
        value = sdict.pop(attr, None)
        if value is not None:
            conf[attr] = value

    def upd_conf_with_int_item(conf, attr, sdict):
        value = sdict.pop(attr, None)
        if value is not None:
            conf[attr] = int(value)

    def upd_conf_with_list_item(conf, attr, sdict, sep=' ', parse=_str_strip):
        values = sdict.pop(attr, None)
        if values:
            conf[attr] = list(filter(None, map(parse, values.split(sep))))

    def _make_root(root):
        root = root.strip()
        if root.startswith("~"):
            return os.path.expanduser(root)
        return root

    c = default_config()

    upd_conf_with_bool_item(c, 'overwrite', local_conf)
    upd_conf_with_bool_item(c, 'redirect_to_fallback', local_conf)
    upd_conf_with_list_item(c, 'authenticated', local_conf, sep=' ')
    upd_conf_with_list_item(c, 'root', local_conf, sep='\n', parse=_make_root)
    upd_conf_with_int_item(c, 'verbosity', local_conf)
    str_items = [
        'fallback_url',
        'hash_algo',
        'log_err_frmt',
        'log_file',
        'log_frmt',
        'log_req_frmt',
        'log_res_frmt',
        'password_file',
        'welcome_file'
    ]
    for str_item in str_items:
        upd_conf_with_str_item(c, str_item, local_conf)
    # cache_control is undocumented; don't know what type is expected:
    # upd_conf_with_str_item(c, 'cache_control', local_conf)

    return app(**c)


def _logwrite(logger, level, msg):
    if msg:
        line_endings = ['\r\n', '\n\r', '\n']
        for le in line_endings:
            if msg.endswith(le):
                msg = msg[:-len(le)]
        if msg:
            logger.log(level, msg)
