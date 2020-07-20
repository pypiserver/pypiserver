#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
AppEngine tailored plugin for pypiserver used to 
synchronize local and remote directories
"""

from pypiserver.community.appengine.logger import CustomLogger
from pypiserver.community.appengine.plugin import (StoragePluginBuilder,
                                                   SynchronizerPlugin)
from pypiserver.community.appengine.storage import (BasicStorageClient,
                                                    LocalFileStoreManager,
                                                    LocalToGoogleFileStoreManager)


def setup_synchronization_plugin(local_directory=None,
                                 remote_directory=None,
                                 storage_client=BasicStorageClient,
                                 file_store_manager=LocalFileStoreManager,
                                 logger=None):
    """Setup the new syncrhonization plugin on top of the pypiserver app.

    Args:
        pypiserver_app (pypiserver.app): an application definition of pypiserver
        local_location (str): location of the local files
        remote_location (str): location of the remote files
        storage_client (pypiserver.community.appengine.BasicStorageClient, optional): storage client to use. Defaults to BasicStorageClient.
        file_store_manager (pypiserver.community.appengine.storage.BaseFileStoreManager, optional): file storage manager to use. Defaults to LocalFileStoreManager.

    Returns:
        pypiserver.app: the pypiserver with the sync plugin setup
    """
    logger = logger if logger else CustomLogger()
    plugin_builder = StoragePluginBuilder(SynchronizerPlugin,
                                          storage_client,
                                          file_store_manager,
                                          logger=CustomLogger())
    synchronizer_plugin = plugin_builder.build_plugin(local_directory,
                                                      remote_directory)
    return synchronizer_plugin


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
    pypiserver_app = app(root=["/tmp/local_packages"])

    # Configure the plugin builder
    synchronizer_plugin = setup_synchronization_plugin(
        "/tmp/local_packages", "/tmp/remote_packages", file_store_manager=LocalFileStoreManager)

    # Register the plugin
    pypiserver_app = add_synchronization_app_hooks(
        pypiserver_app, synchronizer_plugin)

    return pypiserver_app
