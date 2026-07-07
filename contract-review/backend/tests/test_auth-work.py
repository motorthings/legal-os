"""
Tests for authentication and authorization
"""
import pytest
from unittest.mock import Mock, patch
from auth import decode_jwt, get_current_user, require_role
from fastapi import HTTPException


class TestJWTDecoding:
    """Test JWT token decoding and validation"""

    def test_decode_valid_jwt(self):
        """Test decoding a valid JWT token"""
        # This would require a real JWT token for testing
        # For now, test the structure
        with patch('auth.jwt.decode') as mock_decode:
            mock_decode.return_value = {
                'sub': 'user-123',
                'email': 'test@example.com'
            }

            result = decode_jwt('fake-token')

            assert result is not None
            assert result['sub'] == 'user-123'
            assert result['email'] == 'test@example.com'

    def test_decode_invalid_jwt(self):
        """Test decoding an invalid JWT token"""
        with patch('auth.jwt.decode', side_effect=Exception("Invalid token")):
            result = decode_jwt('invalid-token')
            assert result is None


class TestCurrentUser:
    """Test current user extraction from JWT"""

    @patch('auth.get_supabase')
    @patch('auth.decode_jwt')
    def test_get_current_user_success(self, mock_decode, mock_supabase):
        """Test successful user extraction"""
        # Mock JWT decode
        mock_decode.return_value = {
            'sub': 'user-123',
            'email': 'test@example.com'
        }

        # Mock database response
        mock_client = Mock()
        mock_result = Mock()
        mock_result.data = {'role': 'admin', 'client_id': 'client-1'}
        mock_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = mock_result
        mock_supabase.return_value = mock_client

        # Mock credentials
        mock_credentials = Mock()
        mock_credentials.credentials = 'fake-token'

        result = get_current_user(mock_credentials)

        assert result['id'] == 'user-123'
        assert result['email'] == 'test@example.com'
        assert result['role'] == 'admin'
        assert result['client_id'] == 'client-1'

    @patch('auth.decode_jwt')
    def test_get_current_user_invalid_token(self, mock_decode):
        """Test user extraction with invalid token"""
        mock_decode.return_value = None
        mock_credentials = Mock()
        mock_credentials.credentials = 'invalid-token'

        with pytest.raises(HTTPException) as exc_info:
            get_current_user(mock_credentials)

        assert exc_info.value.status_code == 401


class TestRoleAuthorization:
    """Test role-based authorization"""

    def test_require_admin_with_admin_user(self):
        """Test admin requirement with admin user"""
        mock_user = {'id': 'user-1', 'role': 'admin'}
        checker = require_role(['admin'])
        result = checker(mock_user)
        assert result == mock_user

    def test_require_admin_with_regular_user(self):
        """Test admin requirement with regular user"""
        mock_user = {'id': 'user-1', 'role': 'user'}
        checker = require_role(['admin'])

        with pytest.raises(HTTPException) as exc_info:
            checker(mock_user)

        assert exc_info.value.status_code == 403

    def test_require_multiple_roles(self):
        """Test authorization with multiple allowed roles"""
        checker = require_role(['admin', 'client_admin'])

        # Test admin user
        admin_user = {'id': 'user-1', 'role': 'admin'}
        result = checker(admin_user)
        assert result == admin_user

        # Test client_admin user
        client_admin = {'id': 'user-2', 'role': 'client_admin'}
        result = checker(client_admin)
        assert result == client_admin

        # Test regular user (should fail)
        regular_user = {'id': 'user-3', 'role': 'user'}
        with pytest.raises(HTTPException) as exc_info:
            checker(regular_user)
        assert exc_info.value.status_code == 403
