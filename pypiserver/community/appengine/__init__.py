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
from pypiserver.community.appengine.storage import (BasicStorageClient,
                                                    LocalFileStoreDriver,
                                                    LocalToGoogleCloudStorageFileStoreDriver)


def setup_synchronization_plugin(pypiserver_app,
                                 local_location,
                                 remote_location,
                                 storage_client=BasicStorageClient,
                                 file_store=LocalFileStoreDriver):
    """Setup the new syncrhonization plugin on top of the pypiserver app.

    Args:
        pypiserver_app (pypiserver.app): [description]
        local_location (str): location of the local files
        remote_location (str): location of the remote files
        storage_client (pypiserver.community.appengine.BasicStorageClient, optional): storage client to use. Defaults to BasicStorageClient.
        file_store (pypiserver.community.appengine.storage.BaseFileStoreDriver, optional): file storage driver to use. Defaults to LocalFileStoreDriver.

    Returns:
        pypiserver.app: the pypiserver with the sync plugin setup
    """
    plugin_builder = StoragePluginBuilder(SynchronizerPlugin,
                                          storage_client,
                                          file_store,
                                          logger=CustomLogger())
    synchronizer_plugin = plugin_builder.build_plugin(local_location,
                                                      remote_location)
    return add_synchronization_app_hooks(pypiserver_app, synchronizer_plugin)


def add_synchronization_app_hooks(pypiserver_app, plugin):
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
    pypiserver_app = app(
        root=[GlobalSettings.LOCAL_DIRECTORY], password_file="htpasswd.txt")

    # Configure the plugin builder
    plugin_builder = StoragePluginBuilder(SynchronizerPlugin,
                                          BasicStorageClient,
                                          LocalFileStoreDriver,
                                          logger=CustomLogger())

    # create the plugin
    synchronizer_plugin = plugin_builder.build_plugin(
        GlobalSettings.LOCAL_DIRECTORY,  GlobalSettings.REMOTE_DIRECTORY)
    return add_synchronization_app_hooks(pypiserver_app, synchronizer_plugin)
