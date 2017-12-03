"""
===============================
Setup-tools Plugin Architecture
===============================

`setup.py` configurations
-------------------------
To implement a new plugin, you have to package your code as a regular
python distribution and add the following declaration inside its
:file:`setup.py`::

    setup(
        # ...
        entry_points = {
            'pypiserver.plugins': [
                'plugin_1 = <bar.plugin.module>   [dep1, dep2]',        ## Load only.
                'plugin_2 = <foo.plugin.module>:<plugin-install-func>', ## Load & install.
            ]
        }
    )


Implementing a plugin
---------------------
The plugins are initialized alphabetically in a 2-stage procedure
during *import time* by :func:`init_plugins()`:

- A plugin is *loaded* and
- optionally *installed* if the configuration in `setup.py ` specifies
  a no-args ``<plugin-install-func>``.

Any collected ``<plugin-install-func>`` callables are invoked AFTER all
plugin-modules have finished loading.

.. Warning::
   When appending into "hook" lists during installation, remember to avoid
   re-inserting duplicate items.  In general try to well-behave even when
   **plugins are initialized multiple times**!

"""
from collections import OrderedDict
import logging

import pkg_resources


#: Used to discover *setuptools* extension-points.
_PLUGIN_GROUP_NAME = 'pypiserver.plugins'

log = logging.getLogger(__name__)

def _init_plugins(plugin_group_name=_PLUGIN_GROUP_NAME):
    "Discover and load *setup-tools* plugins. "
    global _plugins_installed

    def stringify_EntryPoint(ep):
        return "%r@%s" % (ep, ep.dist)

    plugin_loaders = []
    entry_points = sorted(
        pkg_resources.working_set.iter_entry_points(plugin_group_name),
        key=lambda ep: ep.name)
    for ep in entry_points:
        try:
            _plugins_installed[stringify_EntryPoint(ep)] = 0
            plugin_loader = ep.load()
            _plugins_installed[stringify_EntryPoint(ep)] = 1
            if callable(plugin_loader):
                plugin_loaders.append((ep, plugin_loader))
        except Exception as ex:
            log.error('Failed LOADING plugin(%r@%s) due to: %s',
                      ep, ep.dist, ex, exc_info=1)

    for ep, plugin_loader in plugin_loaders:
        try:
            plugin_loader()
            _plugins_installed[stringify_EntryPoint(ep)] = 2
        except Exception as ex:
            log.error('Failed INSTALLING plugin(%r@%s) due to: %s',
                      ep, ep.dist, ex, exc_info=1)


#: A list of 2-tuples for each plugin installed of :class:`pkg_resources.EntryPoint`
#: and the number of completed stages (integer).
#:
#: The *EntryPoint* gets stringified to avoid memory-leaks.
_plugins_installed = OrderedDict()

