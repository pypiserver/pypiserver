"PluginBuilder and Sycnronizer plugin are used to provide the decoration to the pypiserver app"

import logging


class StoragePluginBuilder:
    """A shallow builder of the supplied plugin class, storage clients and drivers

    Args:
        plugin_class (type): a constructor for the plugin
        client_class (type): constructor for the storage client detecting the changes
        driver_class (type): constructor for the file storage driver that provides file operations
    """

    def __init__(self, plugin_class, client_class, driver_class, logger=None):
        self.plugin_class = plugin_class
        self.client_class = client_class
        self.driver_class = driver_class
        self.logger = logger if logger else logging.getLogger(__name__)

    def build_plugin(self, local_location, remote_location):
        """Construct the plugin instance with specified client and driver
        classe configured for specified local and remote locations.

        Args:
            local_location (str): location for the package files locally
            remote_location (str): location for the package files remotely

        Returns:
            pypiserver.community.appengine.SynchronizerPlugin: the created plugin instance
        """
        driver = self.create_driver(local_location, remote_location)
        storage_client = self.create_client(driver)
        return self.create_plugin(storage_client)

    def create_driver(self, local_directory, remote_directory):
        """Construct plugin storage driver instance

        Args:
            local_directory (str): a name of the local directory
            remote_directory (str): a name of the remote directory

        Returns:
            pypiserver.community.appengine.storage.BaseFileStoreDriver: a new driver instance
        """
        return self.driver_class(local_directory=local_directory, remote_directory=remote_directory)

    def create_client(self, storage_driver):
        """Construct new storage client instance

        Args:
            storage_driver (pypiserver.community.appengine.storage.BaseFileStoreDriver): a storage driver instance

        Returns:
            pypiserver.community.appengine.BasicStorageClient: a new client instance
        """
        return self.client_class(file_store_driver=storage_driver)

    def create_plugin(self, storage_client):
        """Construct plugin given the storage client instance

        Args:
            storage_client (pypiserver.community.appengine.BasicStorageClient): a storage client instance

        Returns:
            pypiserver.community.appengine.SynchronizerPlugin: a new plugin instance
        """
        return self.plugin_class(storage_client=storage_client, logger=self.logger)

    def describe_configuration(self):
        """Log information about the given plugin builer
        """
        self.logger.info(str(self))

    def __str__(self):
        """Returns a string representation of itself

        Returns:
            str: a formatted string of own configuration
        """
        return "Plugin builder configured with:\n\tPlugin:{plugin}\n\tStorageClient:{client}\n\tFileStoreDriver:{driver}".format(
            plugin=self.plugin_class,
            client=self.client_class,
            driver=self.driver_class
        )


class SynchronizerPlugin:
    """Plugin for allowing synchronization of files before and after changes

    Args:
        storage_client (pypiserver.community.appengine.BasicStorageClient): a storage client to operate on files
        logger (Logger): a logger instance
    """

    def __init__(self, storage_client=None, logger=None):
        self.storage_client = storage_client
        self.logger = logger if logger else logging.getLogger(__name__)

    def sync_data_before_change(self):
        self.logger.info("Checking out newest remote state")

        self.storage_client.pull_remote_files()
        self.storage_client.store_local_snapshot()

        self.logger.debug(self.storage_client.get_local_contents())
        self.logger.info("Ready to process!")

    def sync_data_after_change(self):
        self.logger.info("Syncronizing data after request handling")

        change_events = self.storage_client.get_change_events()

        result = [self.storage_client.upload_to_remote(
            change_event) for change_event in change_events]

        self.logger.debug("Handled events: {}".format(result))
        self.logger.info("Done!")
