'''Module responsible for testing the appengine plugin
'''

# Standard library imports
from unittest.mock import MagicMock, call

# Third party imports
import pytest

# Local imports
from pypiserver.community.appengine.plugin import (StoragePluginBuilder,
                                                   SynchronizerPlugin)
from pypiserver.community.appengine.storage import BasicStorageClient


def _get_syncronizer_plugin(storage_client):
    return SynchronizerPlugin(storage_client=storage_client)


@pytest.fixture
def storage_client():
    return MagicMock(spec=BasicStorageClient)


def test_SynchronizerPlugin_sync_data_before_change_pulls_remote_files(storage_client: MagicMock):
    plugin = _get_syncronizer_plugin(storage_client)
    plugin.sync_data_before_change()
    storage_client.pull_remote_files.assert_called_once_with()


def test_SynchronizerPlugin_sync_data_before_change_stores_latest_local_files(storage_client: MagicMock):
    plugin = _get_syncronizer_plugin(storage_client)
    plugin.sync_data_before_change()
    storage_client.store_local_files_snapshot.assert_called_once_with()


def test_SynchronizerPlugin_sync_data_after_change_gets_all_changes(storage_client: MagicMock):
    plugin = _get_syncronizer_plugin(storage_client)
    plugin.sync_data_after_change()
    storage_client.get_change_events.assert_called_once_with()


def test_SynchronizerPlugin_sync_data_after_change_processes_all_changes(storage_client: MagicMock):
    expected_events = ['foo', 'bar']
    storage_client.get_change_events.return_value = expected_events
    plugin = _get_syncronizer_plugin(storage_client)
    plugin.sync_data_after_change()
    storage_client.upload_to_remote.assert_has_calls(
        [call(event) for event in expected_events])
