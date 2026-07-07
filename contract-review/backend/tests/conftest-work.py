"""
Pytest configuration and fixtures
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, MagicMock


@pytest.fixture
def mock_supabase():
    """
    Mock Supabase client for testing
    """
    mock = MagicMock()
    mock.table.return_value = mock
    mock.select.return_value = mock
    mock.insert.return_value = mock
    mock.update.return_value = mock
    mock.delete.return_value = mock
    mock.eq.return_value = mock
    mock.execute.return_value = Mock(data=[])
    return mock


@pytest.fixture
def mock_user():
    """
    Mock authenticated user
    """
    return {
        'id': '123e4567-e89b-12d3-a456-426614174000',
        'email': 'test@example.com',
        'role': 'user',
        'client_id': '00000000-0000-0000-0000-000000000001',
        'name': 'Test User'
    }


@pytest.fixture
def mock_admin():
    """
    Mock admin user
    """
    return {
        'id': '123e4567-e89b-12d3-a456-426614174001',
        'email': 'admin@example.com',
        'role': 'admin',
        'client_id': '00000000-0000-0000-0000-000000000001',
        'name': 'Admin User'
    }
