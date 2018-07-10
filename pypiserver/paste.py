"""Provide a paste-compatible entry point."""

import os

from ._app import app
from .config import str2bool, ConfigFactory


def _str_strip(string):
    """Provide a generic strip method to pass as a callback."""
    return string.strip()


def paste_app_factory(global_config, **local_conf):
    """Parse a paste config and return an app."""

    def upd_conf_with_bool_item(conf, attr, sdict):
        value = sdict.pop(attr, None)
        if value is not None and attr != '':
            # conf[attr] = str2bool(value)
            setattr(conf, attr, str2bool(value))

    def upd_conf_with_str_item(conf, attr, sdict):
        value = sdict.pop(attr, None)
        if value is not None:
            setattr(conf, attr, value)
            # conf[attr] = value

    def upd_conf_with_int_item(conf, attr, sdict):
        value = sdict.pop(attr, None)
        if value is not None:
            setattr(conf, attr, int(value))
            # conf[attr] = int(value)

    def upd_conf_with_list_item(conf, attr, sdict, sep=' ', parse=_str_strip):
        values = sdict.pop(attr, None)
        if values:
            # conf[attr] = list(filter(None, map(parse, values.split(sep))))
            setattr(
                conf, attr, list(filter(None, map(parse, values.split(sep))))
            )

    def _make_root(root):
        root = root.strip()
        if root.startswith("~"):
            return os.path.expanduser(root)
        return root

    c = ConfigFactory(
        parser_type='pypi-server'
    ).get_parser().parse_args([])

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

    return app(c)
