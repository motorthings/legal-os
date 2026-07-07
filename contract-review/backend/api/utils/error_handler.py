"""
Centralized Error Handling Utilities

Provides custom exception classes, standardized error responses, and
FastAPI exception handlers for consistent error handling across the application.
"""

from typing import Optional, Dict, Any
from datetime import datetime
from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from logger_config import get_logger

logger = get_logger(__name__)


# ============================================================================
# Custom Exception Classes
# ============================================================================

class SuperAssistantError(Exception):
    """Base exception for all SuperAssistant errors"""

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
        super().__init__(self.message)


# Authentication & Authorization Errors
class AuthenticationError(SuperAssistantError):
    """Raised when authentication fails"""
    pass


class AuthorizationError(SuperAssistantError):
    """Raised when user lacks permission for an action"""
    pass


class TokenExpiredError(AuthenticationError):
    """Raised when authentication token has expired"""
    pass


# Document Processing Errors
class DocumentProcessingError(SuperAssistantError):
    """Base class for document processing errors"""
    pass


class DocumentNotFoundError(DocumentProcessingError):
    """Raised when a document cannot be found"""
    pass


class TextExtractionError(DocumentProcessingError):
    """Raised when text extraction from a file fails"""
    pass


class UnsupportedFileTypeError(DocumentProcessingError):
    """Raised when file type is not supported"""
    pass


class FileSizeLimitError(DocumentProcessingError):
    """Raised when file exceeds size limit"""
    pass


# Embedding & Vector Search Errors
class EmbeddingError(SuperAssistantError):
    """Base class for embedding-related errors"""
    pass


class EmbeddingGenerationError(EmbeddingError):
    """Raised when embedding generation fails"""
    pass


class VectorSearchError(EmbeddingError):
    """Raised when vector search fails"""
    pass


# External Service Errors
class ExternalServiceError(SuperAssistantError):
    """Base class for external service errors"""
    pass


class GoogleDriveError(ExternalServiceError):
    """Raised when Google Drive operations fail"""
    pass


class NotionError(ExternalServiceError):
    """Raised when Notion operations fail"""
    pass


class AnthropicAPIError(ExternalServiceError):
    """Raised when Anthropic API calls fail"""
    pass


class VoyageAPIError(ExternalServiceError):
    """Raised when Voyage AI API calls fail"""
    pass


# Database Errors
class DatabaseError(SuperAssistantError):
    """Base class for database errors"""
    pass


class DatabaseConnectionError(DatabaseError):
    """Raised when database connection fails"""
    pass


class QueryExecutionError(DatabaseError):
    """Raised when database query execution fails"""
    pass


# Validation Errors
class ValidationError(SuperAssistantError):
    """Base class for validation errors"""
    pass


class InvalidInputError(ValidationError):
    """Raised when input validation fails"""
    pass


class RateLimitError(SuperAssistantError):
    """Raised when rate limit is exceeded"""
    pass


# ============================================================================
# Error Response Formatting
# ============================================================================

def create_error_response(
    error: Exception,
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
    include_details: bool = True
) -> Dict[str, Any]:
    """
    Create a standardized error response dictionary.

    Args:
        error: The exception that occurred
        status_code: HTTP status code to return
        include_details: Whether to include detailed error information

    Returns:
        Dictionary with standardized error response format
    """
    response = {
        "error": {
            "type": error.__class__.__name__,
            "message": str(error),
            "timestamp": datetime.utcnow().isoformat()
        }
    }

    # Add error code if available (custom exceptions)
    if isinstance(error, SuperAssistantError):
        response["error"]["code"] = error.error_code

        # Add details if available and requested
        if include_details and error.details:
            response["error"]["details"] = error.details

    return response


def get_status_code_for_exception(error: Exception) -> int:
    """
    Determine appropriate HTTP status code for an exception.

    Args:
        error: The exception to evaluate

    Returns:
        Appropriate HTTP status code
    """
    # Authentication errors
    if isinstance(error, (AuthenticationError, TokenExpiredError)):
        return status.HTTP_401_UNAUTHORIZED

    # Authorization errors
    if isinstance(error, AuthorizationError):
        return status.HTTP_403_FORBIDDEN

    # Not found errors
    if isinstance(error, DocumentNotFoundError):
        return status.HTTP_404_NOT_FOUND

    # Validation errors
    if isinstance(error, (ValidationError, InvalidInputError, UnsupportedFileTypeError)):
        return status.HTTP_400_BAD_REQUEST

    # File size errors
    if isinstance(error, FileSizeLimitError):
        return status.HTTP_413_REQUEST_ENTITY_TOO_LARGE

    # Rate limit errors
    if isinstance(error, RateLimitError):
        return status.HTTP_429_TOO_MANY_REQUESTS

    # External service errors (may be temporary)
    if isinstance(error, ExternalServiceError):
        return status.HTTP_503_SERVICE_UNAVAILABLE

    # Database errors
    if isinstance(error, DatabaseError):
        return status.HTTP_503_SERVICE_UNAVAILABLE

    # Default to 500 for unexpected errors
    return status.HTTP_500_INTERNAL_SERVER_ERROR


# ============================================================================
# FastAPI Exception Handlers
# ============================================================================

async def superassistant_error_handler(
    request: Request,
    exc: SuperAssistantError
) -> JSONResponse:
    """
    Handle SuperAssistant custom exceptions.

    Logs the error with context and returns standardized JSON response.
    """
    status_code = get_status_code_for_exception(exc)

    # Log error with context
    logger.error(
        f"SuperAssistant error: {exc.__class__.__name__}",
        extra={
            "error_type": exc.__class__.__name__,
            "error_code": exc.error_code,
            "message": exc.message,
            "details": exc.details,
            "path": request.url.path,
            "method": request.method,
            "status_code": status_code
        }
    )

    # Create standardized response
    response_data = create_error_response(exc, status_code)

    return JSONResponse(
        status_code=status_code,
        content=response_data
    )


async def http_exception_handler(
    request: Request,
    exc: HTTPException
) -> JSONResponse:
    """
    Handle FastAPI HTTPException with standardized format.
    """
    logger.warning(
        f"HTTP exception: {exc.status_code}",
        extra={
            "status_code": exc.status_code,
            "detail": exc.detail,
            "path": request.url.path,
            "method": request.method
        }
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "type": "HTTPException",
                "message": exc.detail,
                "status_code": exc.status_code,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
    )


async def generic_exception_handler(
    request: Request,
    exc: Exception
) -> JSONResponse:
    """
    Handle unexpected exceptions with logging and generic error message.

    This is a catch-all handler for exceptions that don't have specific handlers.
    It logs the full exception but returns a generic message to avoid leaking
    implementation details.
    """
    # Log full exception with traceback
    logger.exception(
        "Unexpected error",
        extra={
            "error_type": exc.__class__.__name__,
            "path": request.url.path,
            "method": request.method
        },
        exc_info=True
    )

    # Return generic error message (don't leak implementation details)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "type": "InternalServerError",
                "message": "An unexpected error occurred. Please try again later.",
                "timestamp": datetime.utcnow().isoformat()
            }
        }
    )


# ============================================================================
# Error Context Manager
# ============================================================================

class ErrorContext:
    """
    Context manager for adding error handling context.

    Usage:
        with ErrorContext("Processing document", document_id=doc_id):
            process_document(doc_id)
    """

    def __init__(self, operation: str, **kwargs):
        self.operation = operation
        self.context = kwargs

    def __enter__(self):
        logger.debug(f"Starting: {self.operation}", extra=self.context)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            logger.error(
                f"Error in {self.operation}: {exc_val}",
                extra={**self.context, "error_type": exc_type.__name__},
                exc_info=True
            )
        else:
            logger.debug(f"Completed: {self.operation}", extra=self.context)

        # Don't suppress exceptions
        return False


# ============================================================================
# Helper Functions
# ============================================================================

def wrap_external_service_error(
    error: Exception,
    service_name: str,
    operation: str
) -> ExternalServiceError:
    """
    Wrap external service errors with context.

    Args:
        error: The original exception
        service_name: Name of the external service
        operation: Operation that was being performed

    Returns:
        ExternalServiceError with context
    """
    if "anthropic" in service_name.lower():
        return AnthropicAPIError(
            f"{service_name} {operation} failed: {str(error)}",
            details={"service": service_name, "operation": operation}
        )
    elif "voyage" in service_name.lower():
        return VoyageAPIError(
            f"{service_name} {operation} failed: {str(error)}",
            details={"service": service_name, "operation": operation}
        )
    elif "google" in service_name.lower() or "drive" in service_name.lower():
        return GoogleDriveError(
            f"{service_name} {operation} failed: {str(error)}",
            details={"service": service_name, "operation": operation}
        )
    elif "notion" in service_name.lower():
        return NotionError(
            f"{service_name} {operation} failed: {str(error)}",
            details={"service": service_name, "operation": operation}
        )
    else:
        return ExternalServiceError(
            f"{service_name} {operation} failed: {str(error)}",
            details={"service": service_name, "operation": operation}
        )


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    # Base exceptions
    'SuperAssistantError',
    # Authentication
    'AuthenticationError',
    'AuthorizationError',
    'TokenExpiredError',
    # Document processing
    'DocumentProcessingError',
    'DocumentNotFoundError',
    'TextExtractionError',
    'UnsupportedFileTypeError',
    'FileSizeLimitError',
    # Embeddings
    'EmbeddingError',
    'EmbeddingGenerationError',
    'VectorSearchError',
    # External services
    'ExternalServiceError',
    'GoogleDriveError',
    'NotionError',
    'AnthropicAPIError',
    'VoyageAPIError',
    # Database
    'DatabaseError',
    'DatabaseConnectionError',
    'QueryExecutionError',
    # Validation
    'ValidationError',
    'InvalidInputError',
    'RateLimitError',
    # Utilities
    'create_error_response',
    'get_status_code_for_exception',
    'ErrorContext',
    'wrap_external_service_error',
    # Exception handlers
    'superassistant_error_handler',
    'http_exception_handler',
    'generic_exception_handler',
]
