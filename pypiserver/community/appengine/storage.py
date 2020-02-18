import logging
import os
import shutil
import sys
import time

from google.cloud import storage
from pypiserver import app


class ContentChangeTypes:

    REMOVAL = "removal"
    ADDITION = "addition"
    ANY = "n/a"

    def __init__(self, difference=None, logger=None):
        self._type = self.ANY
        self._difference = difference
        self.logger = logger if logger else logging.getLogger(__name__)

    @property
    def change_type(self):
        return self._type

    @property
    def difference(self):
        return self._difference

    def handle(self, *args):
        raise NotImplementedError("Subclasses must implement a change handler")

    def process(self):
        try:
            results = [self.handle(file_name) for file_name in self.difference]
            self.logger.debug(
                "Completed handling own type: {} with results: {}".format(self.change_type, results))
            return True
        except Exception as error:
            self.logger.error(error)
            return False


class RemovalChangeEvent(ContentChangeTypes):

    def __init__(self, file_store_driver, difference=None, logger=None):
        super().__init__(difference=difference, logger=logger)
        self._type = self.REMOVAL
        self._file_store_driver = file_store_driver

    def handle(self, *args):
        self.logger.debug(
            "Handling {} with difference: {}".format(self.change_type, self.difference))
        return self._file_store_driver.remove_from_remote(*args)


class AdditionChangeEvent(ContentChangeTypes):

    def __init__(self, file_store_driver, difference=None, logger=None):
        super().__init__(difference=difference, logger=logger)
        self._type = self.ADDITION
        self._file_store_driver = file_store_driver

    def handle(self, *args):
        self.logger.debug(
            "Handling {} with difference: {}".format(self.change_type, self.difference))
        return self._file_store_driver.upload_to_remote(*args)


class BasicStorageClient:

    def __init__(self, file_store_driver=None, logger=None):
        self._file_storage = file_store_driver
        self._current_local_contents = None
        self.logger = logger if logger else logging.getLogger(__name__)

    def pull_remote_files(self):
        return self._file_storage.pull_all_remote_files()

    def get_local_contents(self):
        return set(self._file_storage.get_local_file_listing())

    def store_local_snapshot(self):
        self._current_local_contents = self.get_local_contents()

    def get_last_local_snapshot(self):
        if not self._current_local_contents:
            raise ValueError("Local snapshot have not been stored!")
        return self._current_local_contents

    def get_change_events(self):
        last_snapshot = self.get_last_local_snapshot()
        current_contents = self.get_local_contents()
        removal_difference = last_snapshot - current_contents
        addition_difference = current_contents - last_snapshot

        self.logger.debug("last snapshot: {}".format(last_snapshot))
        self.logger.debug("current snapshot: {}".format(current_contents))
        self.logger.debug("removal difference: {}".format(removal_difference))
        self.logger.debug(
            "addition difference: {}".format(addition_difference))

        yield RemovalChangeEvent(self._file_storage, difference=removal_difference, logger=self.logger)
        yield AdditionChangeEvent(self._file_storage, difference=addition_difference, logger=self.logger)

    def upload_to_remote(self, change_event):
        return change_event.process()


class StandardFileStoreDriver:

    def __init__(self, local_directory=None, remote_directory=None, logger=None):
        self._local_directory = local_directory
        self._remote_directory = remote_directory
        self.logger = logger if logger else logging.getLogger(__name__)

    @property
    def sync_directory_path(self):
        return self._remote_directory.rstrip("/")

    @property
    def source_directory_path(self):
        return self._local_directory.rstrip("/")

    def pull_all_remote_files(self):
        try:
            remote_files = self.get_remote_file_names()
            results = [self.copy_from_remote(file_name)
                       for file_name in remote_files]
            self.logger.debug(results)
            return results
        except Exception as error:
            self.logger.debug(error)
            raise

    def _get_remote_target_path(self, file_name):
        return "{}/{}".format(self.sync_directory_path, file_name)

    def _get_local_target_path(self, file_name):
        return "{}/{}".format(self.source_directory_path, file_name)

    def _get_remote_target_path(self, file_name):
        return "{}/{}".format(self.sync_directory_path, file_name)

    def _get_local_target_path(self, file_name):
        return "{}/{}".format(self.source_directory_path, file_name)

    def get_remote_file_names(self):
        raise NotImplementedError(
            "Subclasses must implement `get_remote_file_names`")

    def remove_from_remote(self, file_name):
        raise NotImplementedError(
            "Subclasses must implement `remove_from_remote`")

    def copy_from_remote(self, file_name):
        raise NotImplementedError(
            "Subclasses must implement `copy_from_remote`")

    def upload_to_remote(self, file_name):
        raise NotImplementedError(
            "Subclasses must implement `upload_to_remote`")


class LocalFileStoreDriver(StandardFileStoreDriver):

    def __init__(self, local_directory=None, remote_directory=None, logger=None):
        super().__init__(local_directory=local_directory,
                         remote_directory=remote_directory,
                         logger=logger)

    def get_remote_file_names(self):
        file_names = set(os.listdir(self.sync_directory_path))
        self.logger.debug("FILE NAMES")
        self.logger.debug(file_names)
        return file_names

    def get_local_file_listing(self):
        return set(os.listdir(self.source_directory_path))

    def remove_from_remote(self, file_name):
        return self._remove_file(trg=self._get_remote_target_path(file_name))

    def copy_from_remote(self, file_name):
        return self._copy_file(src=self._get_remote_target_path(file_name),
                               trg=self._get_local_target_path(file_name))

    def upload_to_remote(self, file_name):
        return self._copy_file(src=self._get_local_target_path(file_name),
                               trg=self._get_remote_target_path(file_name))

    def _copy_file(self, src=None, trg=None):
        self.logger.debug("{} -> {}".format(src, trg))
        try:
            shutil.copy(src, trg)
            return True
        except:
            return False

    def _remove_file(self, trg=None):
        self.logger.debug("{} -> x".format(trg))
        try:
            os.remove(trg)
            return True
        except:
            return False


class LocalToGoogleCloudStorageFileStoreDriver(StandardFileStoreDriver):

    def __init__(self, local_directory=None, remote_directory=None, bucket_name=None, logger=None):
        super().__init__(local_directory=local_directory,
                         remote_directory=remote_directory,
                         logger=logger)
        self._google_storage_client = storage.Client()
        self._bucket_name = bucket_name

    @property
    def bucket(self):
        return self._google_storage_client.get_bucket(self._bucket_name)

    def get_remote_file_names(self):
        def get_name(x): return x.name.split('/')[-1]
        def is_file(x): return not x.name.endswith("/")

        blobs = self._google_storage_client.list_blobs(
            self._bucket_name, prefix=self.sync_directory_path)
        file_names = set((get_name(blob) for blob in blobs if is_file(blob)))

        self.logger.debug(file_names)
        return file_names

    def get_local_file_listing(self):
        return set(os.listdir(self.source_directory_path))

    def remove_from_remote(self, file_name):
        return self._remove_remote_file(trg=self._get_remote_target_path(file_name))

    def copy_from_remote(self, file_name):
        return self._download_file(src=self._get_remote_target_path(file_name),
                                   trg=self._get_local_target_path(file_name))

    def upload_to_remote(self, file_name):
        return self._upload_file(src=self._get_local_target_path(file_name),
                                 trg=self._get_remote_target_path(file_name))

    def _download_file(self, src=None, trg=None):
        self.logger.debug("r: {} -> l: {}".format(src, trg))
        try:
            blob = self.bucket.blob(src)
            blob.download_to_filename(trg)
            return True
        except:
            return False

    def _upload_file(self, src=None, trg=None):
        self.logger.debug("l: {} -> r: {}".format(src, trg))
        try:
            blob = self.bucket.blob(trg)
            blob.upload_from_filename(src)
            return True
        except:
            return False

    def _remove_remote_file(self, trg=None):
        self.logger.debug("{} -> x".format(trg))
        try:
            blob = self.bucket.blob(trg)
            blob.delete()
            return True
        except:
            return False
