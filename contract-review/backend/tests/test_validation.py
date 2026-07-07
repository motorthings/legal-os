"""
Tests for validation utilities
"""
import pytest
from fastapi import HTTPException
from validation import (
    validate_uuid,
    validate_file_size,
    generate_secure_password,
    sanitize_string
)


class TestValidateUUID:
    """Tests for UUID validation"""

    def test_valid_uuid(self):
        """Test UUID validation with valid UUID"""
        valid_uuid = "123e4567-e89b-12d3-a456-426614174000"
        result = validate_uuid(valid_uuid)
        assert result == valid_uuid

    def test_invalid_uuid(self):
        """Test UUID validation with invalid UUID"""
        with pytest.raises(HTTPException) as exc_info:
            validate_uuid("not-a-uuid")
        assert exc_info.value.status_code == 400
        assert "Invalid" in exc_info.value.detail

    def test_empty_uuid(self):
        """Test UUID validation with empty string"""
        with pytest.raises(HTTPException) as exc_info:
            validate_uuid("")
        assert exc_info.value.status_code == 400
        assert "required" in exc_info.value.detail

    def test_none_uuid(self):
        """Test UUID validation with None"""
        with pytest.raises(HTTPException):
            validate_uuid(None)


class TestValidateFileSize:
    """Tests for file size validation"""

    def test_valid_file_size(self):
        """Test file size validation with valid size"""
        small_file = b"x" * 1024  # 1KB
        # Should not raise
        validate_file_size(small_file)

    def test_file_too_large(self):
        """Test file size validation rejects large files"""
        large_file = b"x" * (51 * 1024 * 1024)  # 51MB
        with pytest.raises(HTTPException) as exc_info:
            validate_file_size(large_file)
        assert exc_info.value.status_code == 413

    def test_empty_file(self):
        """Test file size validation rejects empty files"""
        empty_file = b""
        with pytest.raises(HTTPException) as exc_info:
            validate_file_size(empty_file)
        assert exc_info.value.status_code == 400
        assert "empty" in exc_info.value.detail.lower()


class TestGenerateSecurePassword:
    """Tests for password generation"""

    def test_default_length(self):
        """Test password generation creates default length password"""
        password = generate_secure_password()
        assert len(password) == 16

    def test_custom_length(self):
        """Test password generation with custom length"""
        password = generate_secure_password(20)
        assert len(password) == 20

    def test_password_complexity(self):
        """Test password contains required character types"""
        password = generate_secure_password(16)
        assert any(c.isupper() for c in password), "Missing uppercase"
        assert any(c.islower() for c in password), "Missing lowercase"
        assert any(c.isdigit() for c in password), "Missing digit"
        # Check for special characters
        special_chars = "!@#$%^&*()-_=+[]{}|;:,.<>?"
        assert any(c in special_chars for c in password), "Missing special char"

    def test_minimum_length_enforced(self):
        """Test password generation enforces minimum length"""
        with pytest.raises(ValueError):
            generate_secure_password(8)  # Less than minimum 12

    def test_uniqueness(self):
        """Test multiple password generations are unique"""
        passwords = [generate_secure_password() for _ in range(100)]
        # All should be unique
        assert len(set(passwords)) == 100


class TestSanitizeString:
    """Tests for string sanitization"""

    def test_trim_whitespace(self):
        """Test string sanitization trims whitespace"""
        result = sanitize_string("  hello  ")
        assert result == "hello"

    def test_none_input(self):
        """Test string sanitization with None"""
        result = sanitize_string(None)
        assert result is None

    def test_max_length_enforced(self):
        """Test string sanitization enforces max length"""
        long_string = "x" * 1000
        with pytest.raises(HTTPException) as exc_info:
            sanitize_string(long_string, max_length=500)
        assert exc_info.value.status_code == 400
        assert "too long" in exc_info.value.detail.lower()

    def test_empty_string_becomes_none(self):
        """Test empty string after trimming becomes None"""
        result = sanitize_string("   ")
        assert result is None
