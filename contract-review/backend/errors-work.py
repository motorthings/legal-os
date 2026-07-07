"""
Standardized error handling for the API

Provides consistent error response format and custom exception classes.
"""

from typing import Optional, Dict, Any
from fastapi import HTTPException
from fastapi.responses import JSONResponse
from fastapi.requests import Request


class APIError(HTTPException):
    """
    Base class for API errors with standardized format.

    All API errors should inherit from this class to ensure
    consistent error response structure.
    """

    def __init__(
        self,
        status_code: int,
        error_code: str,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        self.error_code = error_code
        self.message = message
        self.details = details or {}

        super().__init__(
            status_code=status_code,
            detail={
                "success": False,
                "error": {
                    "code": error_code,
                    "message": message,
                    "details": self.details
                }
            }
        )


class ValidationError(APIError):
    """Validation error (400)"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=400,
            error_code="VALIDATION_ERROR",
            message=message,
            details=details
        )


class AuthenticationError(APIError):
    """Authentication error (401)"""
    def __init__(self, message: str = "Authentication required"):
        super().__init__(
            status_code=401,
            error_code="AUTHENTICATION_ERROR",
            message=message
        )


class AuthorizationError(APIError):
    """Authorization error (403)"""
    def __init__(self, message: str = "Not authorized to perform this action"):
        super().__init__(
            status_code=403,
            error_code="AUTHORIZATION_ERROR",
            message=message
        )


class NotFoundError(APIError):
    """Resource not found error (404)"""
    def __init__(self, resource: str, resource_id: Optional[str] = None):
        message = f"{resource} not found"
        if resource_id:
            message += f": {resource_id}"

        super().__init__(
            status_code=404,
            error_code="NOT_FOUND",
            message=message,
            details={"resource": resource, "id": resource_id}
        )


class ConflictError(APIError):
    """Resource conflict error (409)"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=409,
            error_code="CONFLICT",
            message=message,
            details=details
        )


class RateLimitError(APIError):
    """Rate limit exceeded (429)"""
    def __init__(self, message: str = "Rate limit exceeded. Please try again later."):
        super().__init__(
            status_code=429,
            error_code="RATE_LIMIT_EXCEEDED",
            message=message
        )


class ServerError(APIError):
    """Internal server error (500)"""
    def __init__(self, message: str = "An internal server error occurred"):
        super().__init__(
            status_code=500,
            error_code="SERVER_ERROR",
            message=message
        )


class DatabaseError(APIError):
    """Database operation error (500)"""
    def __init__(self, operation: str = "database operation"):
        super().__init__(
            status_code=500,
            error_code="DATABASE_ERROR",
            message=f"Failed to complete {operation}. Please try again."
        )


def handle_exception(e: Exception, operation: str, logger=None) -> HTTPException:
    """
    Safely handle exceptions without exposing internal details.

    Args:
        e: The exception that was raised
        operation: Human-readable description of the operation (e.g., "create user")
        logger: Optional logger to log the full error details

    Returns:
        HTTPException with safe error message for the client
    """
    # Log the full error internally if logger provided
    if logger:
        logger.error(f"Error during {operation}: {str(e)}", exc_info=True)

    # Return safe error message to client (no internal details)
    if isinstance(e, HTTPException):
        # Re-raise HTTP exceptions as-is (already safe)
        raise e
    elif isinstance(e, APIError):
        # Re-raise our custom API errors as-is
        raise e
    else:
        # Wrap unexpected errors in a safe message
        raise ServerError(f"Failed to {operation}. Please try again later.")


def format_success_response(data: Any, message: Optional[str] = None) -> Dict[str, Any]:
    """
    Format a successful API response.

    Args:
        data: Response data
        message: Optional success message

    Returns:
        Standardized success response
    """
    response = {
        "success": True,
        "data": data
    }

    if message:
        response["message"] = message

    return response


def format_error_response(
    error_code: str,
    message: str,
    details: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Format an error API response.

    Args:
        error_code: Machine-readable error code
        message: Human-readable error message
        details: Optional additional details

    Returns:
        Standardized error response
    """
    return {
        "success": False,
        "error": {
            "code": error_code,
            "message": message,
            "details": details or {}
        }
    }


async def api_error_handler(request: Request, exc: APIError) -> JSONResponse:
    """
    Global error handler for APIError exceptions.

    Args:
        request: The request that caused the error
        exc: The APIError exception

    Returns:
        JSON response with standardized error format
    """
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.detail
    )


async def generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Global error handler for unexpected exceptions.

    Args:
        request: The request that caused the error
        exc: The exception

    Returns:
        JSON response with generic server error
    """
    # Log the full error for debugging
    import traceback
    print(f"Unexpected error: {str(exc)}")
    print(traceback.format_exc())

    return JSONResponse(
        status_code=500,
        content=format_error_response(
            error_code="SERVER_ERROR",
            message="An unexpected error occurred. Please try again later.",
            details={"type": type(exc).__name__}
        )
    )
