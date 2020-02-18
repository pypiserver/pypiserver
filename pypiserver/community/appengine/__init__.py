#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
AppEngine tailored plugin for pypiserver used to 
synchronize local and remote directories
"""

from pypiserver.community.appengine.logger import CustomLogger
from pypiserver.community.appengine.plugin import (StoragePluginBuilder,
                                                   SynchronizerPlugin)
from pypiserver.community.appengine.settings import GlobalSettings
from pypiserver.community.appengine.storage import (
    BasicStorageClient, LocalFileStoreDriver,
    LocalToGoogleCloudStorageFileStoreDriver)


def decorate_app_with_storage_sync(pypiserver_app, plugin):
    """Decorate the pypiserver bottle app with data synchronisation plugin

    Args:
        pypiserver_app (pypiserver.app): an application definition of pypiserver
        plugin_builder (pypiserver.community.appengine.SynchronizerPlugin): builder to create plugins

    Returns:
        pypiserver.app: a decorated app instance
    """
    pypiserver_app.add_hook("before_request", plugin.sync_data_before_change)
    pypiserver_app.add_hook("after_request", plugin.sync_data_after_change)
    return pypiserver_app


def __example__():
    # Given community imports are present (see above)
    from pypiserver import app

    # Like usual initialize the pypiserver application
    pypiserver_app = app(root=[GlobalSettings.LOCAL_DIRECTORY],
                         password_file="htpasswd.txt")

    # Configure the plugin builder
    plugin_builder = StoragePluginBuilder(SynchronizerPlugin,
                                          BasicStorageClient,
                                          LocalFileStoreDriver,
                                          logger=CustomLogger())

    synchronizer_plugin = plugin_builder.build_plugin(
        plugin_builder.build_client(plugin_builder.build_driver(
            GlobalSettings.LOCAL_DIRECTORY, GlobalSettings.REMOTE_DIRECTORY))
    )

    return decorate_app_with_storage_sync(pypiserver_app, synchronizer_plugin)
