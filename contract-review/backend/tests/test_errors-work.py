"""
Tests for error handling utilities
"""
import pytest
from errors import (
    APIError,
    ValidationError,
    AuthenticationError,
    AuthorizationError,
    NotFoundError,
    format_success_response,
    format_error_response
)


class TestAPIError:
    """Tests for base APIError class"""

    def test_api_error_structure(self):
        """Test APIError has correct structure"""
        error = APIError(
            status_code=400,
            error_code="TEST_ERROR",
            message="Test error message",
            details={"field": "test"}
        )
        assert error.status_code == 400
        assert error.error_code == "TEST_ERROR"
        assert error.message == "Test error message"
        assert error.details == {"field": "test"}


class TestValidationError:
    """Tests for ValidationError"""

    def test_validation_error_status(self):
        """Test ValidationError has correct status code"""
        error = ValidationError("Invalid input")
        assert error.status_code == 400
        assert error.error_code == "VALIDATION_ERROR"

    def test_validation_error_with_details(self):
        """Test ValidationError with details"""
        error = ValidationError(
            "Invalid input",
            details={"field": "email", "reason": "invalid format"}
        )
        assert error.details["field"] == "email"


class TestAuthenticationError:
    """Tests for AuthenticationError"""

    def test_authentication_error_status(self):
        """Test AuthenticationError has correct status code"""
        error = AuthenticationError()
        assert error.status_code == 401
        assert error.error_code == "AUTHENTICATION_ERROR"

    def test_authentication_error_custom_message(self):
        """Test AuthenticationError with custom message"""
        error = AuthenticationError("Invalid token")
        assert error.message == "Invalid token"


class TestAuthorizationError:
    """Tests for AuthorizationError"""

    def test_authorization_error_status(self):
        """Test AuthorizationError has correct status code"""
        error = AuthorizationError()
        assert error.status_code == 403
        assert error.error_code == "AUTHORIZATION_ERROR"


class TestNotFoundError:
    """Tests for NotFoundError"""

    def test_not_found_error_basic(self):
        """Test NotFoundError with resource type only"""
        error = NotFoundError("User")
        assert error.status_code == 404
        assert error.error_code == "NOT_FOUND"
        assert "User not found" in error.message

    def test_not_found_error_with_id(self):
        """Test NotFoundError with resource ID"""
        error = NotFoundError("Document", "doc-123")
        assert "doc-123" in error.message
        assert error.details["resource"] == "Document"
        assert error.details["id"] == "doc-123"


class TestResponseFormatters:
    """Tests for response formatting functions"""

    def test_format_success_response_data_only(self):
        """Test formatting success response with data only"""
        response = format_success_response({"id": "123"})
        assert response["success"] is True
        assert response["data"] == {"id": "123"}
        assert "message" not in response

    def test_format_success_response_with_message(self):
        """Test formatting success response with message"""
        response = format_success_response(
            {"id": "123"},
            message="Created successfully"
        )
        assert response["success"] is True
        assert response["message"] == "Created successfully"

    def test_format_error_response_basic(self):
        """Test formatting error response"""
        response = format_error_response(
            error_code="TEST_ERROR",
            message="Test error"
        )
        assert response["success"] is False
        assert response["error"]["code"] == "TEST_ERROR"
        assert response["error"]["message"] == "Test error"
        assert response["error"]["details"] == {}

    def test_format_error_response_with_details(self):
        """Test formatting error response with details"""
        response = format_error_response(
            error_code="VALIDATION_ERROR",
            message="Invalid input",
            details={"field": "email"}
        )
        assert response["error"]["details"]["field"] == "email"
