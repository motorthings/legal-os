"""
Input validation utilities for API endpoints
"""

import uuid
import secrets
import string
from fastapi import HTTPException, UploadFile
from typing import Optional
from config import MAX_UPLOAD_SIZE_MB


# File upload constraints (imported from config for consistency)
MAX_FILE_SIZE = MAX_UPLOAD_SIZE_MB * 1024 * 1024  # Convert MB to bytes
ALLOWED_FILE_TYPES = {
    'application/pdf',  # .pdf
    'text/plain',  # .txt
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',  # .docx
    'application/json',  # .json
    'application/xml',  # .xml
    'text/xml',  # .xml (alternative MIME type)
    'text/csv',  # .csv
    'text/markdown',  # .md
    'text/x-markdown',  # .md (alternative MIME type)
    'application/octet-stream',  # Generic binary - allow for various file types
}

ALLOWED_EXTENSIONS = {'.pdf', '.txt', '.docx', '.json', '.xml', '.csv', '.md'}  # Currently supported formats

# Avatar/Image upload constraints
MAX_AVATAR_SIZE = 5 * 1024 * 1024  # 5MB
ALLOWED_IMAGE_TYPES = {
    'image/jpeg',
    'image/jpg',
    'image/png',
    'image/webp'
}

ALLOWED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp'}


def validate_uuid(value: str, field_name: str = "id") -> str:
    """
    Validate that a string is a valid UUID.

    Args:
        value: String to validate
        field_name: Name of the field for error messages

    Returns:
        str: The validated UUID string

    Raises:
        HTTPException: If the value is not a valid UUID
    """
    if not value:
        raise HTTPException(
            status_code=400,
            detail=f"{field_name} is required"
        )

    try:
        # Try to parse as UUID
        uuid.UUID(value)
        return value
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid {field_name} format. Must be a valid UUID."
        )


def validate_file_upload(file: UploadFile) -> None:
    """
    Validate uploaded file for size and type.

    Args:
        file: The uploaded file

    Raises:
        HTTPException: If file is invalid
    """
    # Check file exists
    if not file:
        raise HTTPException(status_code=400, detail="No file provided")

    # Check filename
    if not file.filename:
        raise HTTPException(status_code=400, detail="File must have a filename")

    # Check file extension
    file_ext = None
    if '.' in file.filename:
        file_ext = '.' + file.filename.rsplit('.', 1)[1].lower()

    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type not allowed. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    # Check content type if provided
    if file.content_type and file.content_type not in ALLOWED_FILE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Content type '{file.content_type}' not allowed"
        )


def validate_file_size(file_content: bytes) -> None:
    """
    Validate that file size is within limits.

    Args:
        file_content: The file content bytes

    Raises:
        HTTPException: If file is too large
    """
    file_size = len(file_content)

    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size: {MAX_FILE_SIZE / 1024 / 1024}MB"
        )

    if file_size == 0:
        raise HTTPException(
            status_code=400,
            detail="File is empty"
        )


def validate_pagination(limit: int, offset: int) -> tuple[int, int]:
    """
    Validate and normalize pagination parameters.

    Args:
        limit: Maximum number of results
        offset: Number of results to skip

    Returns:
        tuple: (validated_limit, validated_offset)

    Raises:
        HTTPException: If parameters are invalid
    """
    if limit < 1:
        raise HTTPException(status_code=400, detail="limit must be at least 1")

    if limit > 100:
        raise HTTPException(status_code=400, detail="limit cannot exceed 100")

    if offset < 0:
        raise HTTPException(status_code=400, detail="offset cannot be negative")

    return limit, offset


def sanitize_string(value: Optional[str], max_length: int = 500) -> Optional[str]:
    """
    Sanitize string input by trimming whitespace and limiting length.

    Args:
        value: String to sanitize
        max_length: Maximum allowed length

    Returns:
        str or None: Sanitized string or None if input was None

    Raises:
        HTTPException: If string exceeds max length
    """
    if value is None:
        return None

    # Trim whitespace
    sanitized = value.strip()

    # Check length
    if len(sanitized) > max_length:
        raise HTTPException(
            status_code=400,
            detail=f"Input too long. Maximum length: {max_length} characters"
        )

    return sanitized if sanitized else None


def generate_secure_password(length: int = 16) -> str:
    """
    Generate a cryptographically secure random password.

    Uses secrets module (not random) for cryptographic strength.
    Includes mix of uppercase, lowercase, digits, and special characters.

    Args:
        length: Length of password (default: 16, minimum: 12)

    Returns:
        str: Secure random password

    Raises:
        ValueError: If length is less than 12
    """
    if length < 12:
        raise ValueError("Password length must be at least 12 characters")

    # Character sets
    lowercase = string.ascii_lowercase
    uppercase = string.ascii_uppercase
    digits = string.digits
    special = "!@#$%^&*()-_=+[]{}|;:,.<>?"

    # Ensure at least one character from each set
    password_chars = [
        secrets.choice(lowercase),
        secrets.choice(uppercase),
        secrets.choice(digits),
        secrets.choice(special)
    ]

    # Fill the rest with random characters from all sets
    all_chars = lowercase + uppercase + digits + special
    password_chars += [secrets.choice(all_chars) for _ in range(length - 4)]

    # Shuffle to avoid predictable pattern
    secrets.SystemRandom().shuffle(password_chars)

    return ''.join(password_chars)


def validate_image_upload(file: UploadFile) -> None:
    """
    Validate uploaded image file for size and type.

    Args:
        file: The uploaded image file

    Raises:
        HTTPException: If file is invalid
    """
    # Check file exists
    if not file:
        raise HTTPException(status_code=400, detail="No file provided")

    # Check filename
    if not file.filename:
        raise HTTPException(status_code=400, detail="File must have a filename")

    # Check file extension
    file_ext = None
    if '.' in file.filename:
        file_ext = '.' + file.filename.rsplit('.', 1)[1].lower()

    if file_ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Image type not allowed. Allowed types: {', '.join(ALLOWED_IMAGE_EXTENSIONS)}"
        )

    # Check content type if provided
    if file.content_type and file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Content type '{file.content_type}' not allowed. Must be an image."
        )


def validate_image_size(file_content: bytes) -> None:
    """
    Validate that image size is within limits.

    Args:
        file_content: The image file content bytes

    Raises:
        HTTPException: If image is too large
    """
    file_size = len(file_content)

    if file_size > MAX_AVATAR_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"Image too large. Maximum size: {MAX_AVATAR_SIZE / 1024 / 1024}MB"
        )

    if file_size == 0:
        raise HTTPException(
            status_code=400,
            detail="Image file is empty"
        )
