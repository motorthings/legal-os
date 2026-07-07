"""
Tests for configuration module
"""
import os
import pytest
from unittest.mock import patch
from config import (
    get_default_client_id,
    get_client_id_for_user,
    is_multi_tenant_mode,
    get_client_name,
    get_assistant_name
)


class TestDefaultClient:
    """Tests for default client configuration"""

    def test_get_default_client_id(self):
        """Test getting default client ID"""
        client_id = get_default_client_id()
        assert client_id == "00000000-0000-0000-0000-000000000001"

    def test_get_client_id_for_user_single_tenant(self):
        """Test get client ID for user in single-tenant mode"""
        user = {"id": "user-123", "email": "test@example.com"}
        client_id = get_client_id_for_user(user)
        # Should return default client in single-tenant mode
        assert client_id == "00000000-0000-0000-0000-000000000001"


class TestMultiTenant:
    """Tests for multi-tenant mode"""

    def test_is_multi_tenant_mode_default(self):
        """Test multi-tenant mode returns False by default"""
        with patch.dict(os.environ, {}, clear=False):
            assert is_multi_tenant_mode() is False

    def test_is_multi_tenant_mode_enabled(self):
        """Test multi-tenant mode when enabled"""
        with patch.dict(os.environ, {"MULTI_TENANT_MODE": "true"}):
            assert is_multi_tenant_mode() is True

    def test_is_multi_tenant_mode_disabled(self):
        """Test multi-tenant mode when explicitly disabled"""
        with patch.dict(os.environ, {"MULTI_TENANT_MODE": "false"}):
            assert is_multi_tenant_mode() is False


class TestClientNames:
    """Tests for client and assistant name configuration"""

    def test_get_client_name_default(self):
        """Test getting default client name"""
        with patch.dict(os.environ, {}, clear=False):
            name = get_client_name()
            assert name == "Your Organization"

    def test_get_client_name_custom(self):
        """Test getting custom client name"""
        with patch.dict(os.environ, {"CLIENT_NAME": "Acme Corp"}):
            name = get_client_name()
            assert name == "Acme Corp"

    def test_get_assistant_name_default(self):
        """Test getting default assistant name"""
        with patch.dict(os.environ, {}, clear=False):
            name = get_assistant_name()
            assert name == "SuperAssistant"

    def test_get_assistant_name_custom(self):
        """Test getting custom assistant name"""
        with patch.dict(os.environ, {"ASSISTANT_NAME": "HelperBot"}):
            name = get_assistant_name()
            assert name == "HelperBot"
