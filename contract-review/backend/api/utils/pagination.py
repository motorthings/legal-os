"""
Pagination utilities
Helpers for paginating list endpoints
"""
from typing import TypeVar, Generic, List
from pydantic import BaseModel

T = TypeVar('T')


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response model"""
    items: List[T]
    total: int
    limit: int
    offset: int
    has_more: bool

    class Config:
        arbitrary_types_allowed = True


def paginate(items: List[T], total: int, limit: int, offset: int) -> dict:
    """
    Create a paginated response

    Args:
        items: List of items for current page
        total: Total number of items
        limit: Items per page
        offset: Number of items to skip

    Returns:
        Dict with pagination metadata
    """
    return {
        'success': True,
        'items': items,
        'total': total,
        'limit': limit,
        'offset': offset,
        'has_more': offset + len(items) < total
    }
