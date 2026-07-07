"""
Error handling utilities
Helpers for consistent error handling across routes
"""
from errors import NotFoundError, AuthorizationError
from typing import Any


def require_resource_access(
    resource_type: str,
    resource: dict,
    user: dict,
    client_id_field: str = 'client_id'
):
    """
    Helper to check if user can access a resource

    Args:
        resource_type: Type of resource (for error message)
        resource: The resource dict from database
        user: Current user dict from auth
        client_id_field: Name of client_id field in resource

    Raises:
        AuthorizationError: If user doesn't have access
    """
    if user['role'] not in ['admin', 'client_admin']:
        if resource.get(client_id_field) != user.get('client_id'):
            raise AuthorizationError(
                f"You don't have access to this {resource_type}"
            )


def get_or_404(result: Any, resource_type: str, resource_id: str = None):
    """
    Helper to return data or raise 404

    Args:
        result: Supabase query result
        resource_type: Type of resource (for error message)
        resource_id: Optional resource ID for error message

    Returns:
        Result data if found

    Raises:
        NotFoundError: If no data found
    """
    if not result.data:
        raise NotFoundError(resource_type, resource_id)
    return result.data
