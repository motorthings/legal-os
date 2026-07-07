"""
Tests for Celery task queue functionality
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio


@pytest.fixture
def mock_supabase():
    """Mock Supabase client"""
    mock = MagicMock()
    mock.table.return_value.update.return_value.eq.return_value.execute.return_value = None
    return mock


def test_celery_app_configuration():
    """Test Celery app is properly configured"""
    from celery_app import celery_app

    assert celery_app is not None
    assert celery_app.conf.task_serializer == 'json'
    assert celery_app.conf.task_time_limit == 900
    assert celery_app.conf.task_soft_time_limit == 600
    assert celery_app.conf.worker_prefetch_multiplier == 1


def test_task_routes():
    """Test task routing configuration"""
    from celery_app import celery_app

    routes = celery_app.conf.task_routes
    assert 'tasks.contract_tasks.process_contract_task' in routes
    assert routes['tasks.contract_tasks.process_contract_task']['queue'] == 'default'
    assert routes['tasks.contract_tasks.process_urgent_contract_task']['queue'] == 'urgent'
    assert routes['tasks.contract_tasks.process_batch_contract_task']['queue'] == 'batch'


@patch('tasks.contract_tasks.process_contract')
@patch('tasks.contract_tasks.get_supabase')
def test_process_contract_task_success(mock_get_supabase, mock_process_contract, mock_supabase):
    """Test successful contract processing"""
    from tasks.contract_tasks import process_contract_task

    # Setup mocks
    mock_get_supabase.return_value = mock_supabase
    document_id = "00000000-0000-0000-0000-000000000001"

    # Mock async function
    async def mock_async_process(doc_id):
        return {'success': True, 'document_id': doc_id}

    mock_process_contract.return_value = mock_async_process(document_id)

    # Create new event loop for test
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    with patch('asyncio.new_event_loop', return_value=loop):
        result = process_contract_task(document_id)

        # Verify status update was called
        mock_supabase.table.assert_called_with('documents')

    loop.close()


@patch('tasks.contract_tasks.get_supabase')
def test_process_contract_task_updates_status(mock_get_supabase, mock_supabase):
    """Test that task updates processing status in database"""
    from tasks.contract_tasks import process_contract_task

    mock_get_supabase.return_value = mock_supabase
    document_id = "00000000-0000-0000-0000-000000000001"

    # Setup mock chain
    mock_table = MagicMock()
    mock_supabase.table.return_value = mock_table
    mock_table.update.return_value.eq.return_value.execute.return_value = None

    with patch('tasks.contract_tasks.process_contract') as mock_process:
        async def mock_async_process(doc_id):
            return {'success': True}

        mock_process.return_value = mock_async_process(document_id)

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            with patch('asyncio.new_event_loop', return_value=loop):
                process_contract_task(document_id)

            # Verify processing status was set
            calls = mock_table.update.call_args_list
            assert any('processing_status' in str(call) for call in calls)
        finally:
            loop.close()


def test_contract_processing_task_retry_config():
    """Test retry configuration on ContractProcessingTask"""
    from tasks.contract_tasks import ContractProcessingTask

    assert ContractProcessingTask.autoretry_for == (Exception,)
    assert ContractProcessingTask.retry_kwargs['max_retries'] == 3
    assert ContractProcessingTask.retry_kwargs['countdown'] == 60
    assert ContractProcessingTask.retry_backoff is True
    assert ContractProcessingTask.retry_backoff_max == 600
    assert ContractProcessingTask.retry_jitter is True


@patch('tasks.contract_tasks.get_supabase')
def test_task_failure_handler(mock_get_supabase, mock_supabase):
    """Test on_failure callback updates database"""
    from tasks.contract_tasks import ContractProcessingTask

    mock_get_supabase.return_value = mock_supabase
    document_id = "00000000-0000-0000-0000-000000000001"

    # Create task instance
    task = ContractProcessingTask()

    # Mock request object
    task.request = MagicMock()

    # Call on_failure
    exc = Exception("Test failure")
    task.on_failure(exc, 'task-id', [document_id], {}, None)

    # Verify error status was updated
    mock_supabase.table.assert_called_with('documents')


def test_urgent_task_uses_correct_queue():
    """Test that urgent tasks are routed to urgent queue"""
    from celery_app import celery_app

    routes = celery_app.conf.task_routes
    assert routes['tasks.contract_tasks.process_urgent_contract_task']['queue'] == 'urgent'


def test_rate_limiting_configured():
    """Test that rate limiting is configured"""
    from celery_app import celery_app

    annotations = celery_app.conf.task_annotations
    assert 'tasks.contract_tasks.process_contract_task' in annotations
    assert annotations['tasks.contract_tasks.process_contract_task']['rate_limit'] == '10/m'


def test_cleanup_task_exists():
    """Test cleanup task is defined"""
    from tasks.contract_tasks import cleanup_old_results

    result = cleanup_old_results()
    assert result['status'] == 'cleaned'
