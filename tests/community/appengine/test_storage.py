'''Module responsible for testing the appengine storage syncronization classes
'''

# Standard library imports
from unittest.mock import MagicMock, call, patch

# Third party imports
import pytest

# Local imports
from pypiserver.community.appengine.storage import BasicStorageClient, BaseFileStoreManager, ContentChangeTypes


def _get_difference(*args, **kwargs):
    return kwargs['difference']


def _get_basic_storage_client(file_store_manager):
    return BasicStorageClient(file_store_manager=file_store_manager)


@pytest.fixture
def file_store_manager():
    return MagicMock(spec=BaseFileStoreManager)


def test_BasicStorageClient_get_change_events_yields_all_removal_difference_events(file_store_manager):
    storage_client = _get_basic_storage_client(file_store_manager)
    expected_snapshot = set(['a', 'b', 'c'])
    expected_local_contents = set(['a', 'c'])
    with patch('pypiserver.community.appengine.storage.RemovalChangeEvent') as mock_removal_change_event_class:
        with patch('pypiserver.community.appengine.storage.AdditionChangeEvent') as mock_addition_change_event_class:
            mock_removal_change_event_class.side_effect = _get_difference
            mock_addition_change_event_class.side_effect = _get_difference
            with patch.object(BasicStorageClient, 'get_last_local_snapshot') as mock_last_local_snapshot:
                with patch.object(BasicStorageClient, 'get_local_contents') as mock_local_contents:
                    expected_results = [mock_removal_change_event_class(difference={'b'}),
                                        mock_addition_change_event_class(difference=set())]
                    mock_last_local_snapshot.return_value = expected_snapshot
                    mock_local_contents.return_value = expected_local_contents
                    result = list(storage_client.get_change_events())
                    assert expected_results == result


def test_BasicStorageClient_get_change_events_yields_all_addition_difference_events(file_store_manager):
    storage_client = _get_basic_storage_client(file_store_manager)
    expected_snapshot = set(['a', 'b', ])
    expected_local_contents = set(['a', 'b', 'c'])
    with patch('pypiserver.community.appengine.storage.RemovalChangeEvent') as mock_removal_change_event_class:
        with patch('pypiserver.community.appengine.storage.AdditionChangeEvent') as mock_addition_change_event_class:
            mock_removal_change_event_class.side_effect = _get_difference
            mock_addition_change_event_class.side_effect = _get_difference
            with patch.object(BasicStorageClient, 'get_last_local_snapshot') as mock_last_local_snapshot:
                with patch.object(BasicStorageClient, 'get_local_contents') as mock_local_contents:
                    expected_results = [mock_removal_change_event_class(difference=set()),
                                        mock_addition_change_event_class(difference={'c'})]
                    mock_last_local_snapshot.return_value = expected_snapshot
                    mock_local_contents.return_value = expected_local_contents
                    result = list(storage_client.get_change_events())
                    assert expected_results == result


def test_BasicStorageClient_upload_to_remote_calls_the_process_of_event(file_store_manager):
    storage_client = _get_basic_storage_client(file_store_manager)
    mock_event = MagicMock(spec=ContentChangeTypes)
    storage_client.upload_to_remote(mock_event)
    mock_event.process.assert_called_once_with()
