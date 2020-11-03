"""Module responsible for testing the appengine storage syncronization classes
"""

# Standard library imports
from unittest.mock import MagicMock, call, patch

# Third party imports
import pytest

# Local imports
from pypiserver.community.appengine.storage import (
    BaseFileStoreManager,
    BasicStorageClient,
    ContentChangeTypes,
)

REMOVAL_CHANGE_EVENT_PATCHER = patch(
    'pypiserver.community.appengine.storage.RemovalChangeEvent'
)
ADDITION_CHANGE_EVENT_PATCHER = patch(
    'pypiserver.community.appengine.storage.AdditionChangeEvent'
)
LAST_LOCAL_SNAPSHOT_PATCHER = patch.object(
    BasicStorageClient, 'get_last_local_snapshot'
)
GET_LOCAL_CONTENTS_PATCHER = patch.object(
    BasicStorageClient, 'get_local_contents'
)


def _stop_patchers(patchers=None):
    if not patchers:
        REMOVAL_CHANGE_EVENT_PATCHER.stop()
        ADDITION_CHANGE_EVENT_PATCHER.stop()
        LAST_LOCAL_SNAPSHOT_PATCHER.stop()
        GET_LOCAL_CONTENTS_PATCHER.stop()
    else:
        for patcher in patchers:
            patcher.stop()


def _get_difference(*args, **kwargs):
    return kwargs['difference']


def _get_basic_storage_client(file_store_manager):
    return BasicStorageClient(file_store_manager=file_store_manager)


@pytest.fixture
def file_store_manager():
    return MagicMock(spec=BaseFileStoreManager)


def test_BasicStorageClient_get_change_events_yields_all_removal_difference_events(
    file_store_manager,
):
    storage_client = _get_basic_storage_client(file_store_manager)
    expected_snapshot = {'a', 'b', 'c'}
    expected_local_contents = {'a', 'c'}
    mock_removal_change_event_class = REMOVAL_CHANGE_EVENT_PATCHER.start()
    mock_addition_change_event_class = ADDITION_CHANGE_EVENT_PATCHER.start()
    mock_last_local_snapshot = LAST_LOCAL_SNAPSHOT_PATCHER.start()
    mock_local_contents = GET_LOCAL_CONTENTS_PATCHER.start()
    mock_removal_change_event_class.side_effect = _get_difference
    mock_addition_change_event_class.side_effect = _get_difference
    expected_results = [
        mock_removal_change_event_class(difference={'b'}),
        mock_addition_change_event_class(difference=set()),
    ]
    mock_last_local_snapshot.return_value = expected_snapshot
    mock_local_contents.return_value = expected_local_contents
    result = list(storage_client.get_change_events())
    assert expected_results == result
    _stop_patchers()


def test_BasicStorageClient_get_change_events_yields_all_addition_difference_events(
    file_store_manager,
):
    storage_client = _get_basic_storage_client(file_store_manager)
    expected_snapshot = {'a', 'b'}
    expected_local_contents = {'a', 'b', 'c'}
    mock_removal_change_event_class = REMOVAL_CHANGE_EVENT_PATCHER.start()
    mock_addition_change_event_class = ADDITION_CHANGE_EVENT_PATCHER.start()
    mock_last_local_snapshot = LAST_LOCAL_SNAPSHOT_PATCHER.start()
    mock_local_contents = GET_LOCAL_CONTENTS_PATCHER.start()
    mock_removal_change_event_class.side_effect = _get_difference
    mock_addition_change_event_class.side_effect = _get_difference
    expected_results = [
        mock_removal_change_event_class(difference=set()),
        mock_addition_change_event_class(difference={'c'}),
    ]
    mock_last_local_snapshot.return_value = expected_snapshot
    mock_local_contents.return_value = expected_local_contents
    result = list(storage_client.get_change_events())
    assert expected_results == result
    _stop_patchers()


def test_BasicStorageClient_upload_to_remote_calls_the_process_of_event(
    file_store_manager,
):
    storage_client = _get_basic_storage_client(file_store_manager)
    mock_event = MagicMock(spec=ContentChangeTypes)
    storage_client.upload_to_remote(mock_event)
    mock_event.process.assert_called_once_with()
