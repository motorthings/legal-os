"""
Async Supabase Helper Utilities
Reduces code duplication by providing reusable async wrappers for Supabase operations.

This module addresses the repeated pattern of:
  await asyncio.to_thread(lambda: supabase.table(...).select(...).execute())

Usage:
  from api.utils.supabase_async import async_select, async_insert

  # Instead of:
  result = await asyncio.to_thread(
      lambda: supabase.table('documents').select('*').eq('id', doc_id).execute()
  )

  # Use:
  result = await async_select('documents', filters={'id': doc_id})
"""

import asyncio
from typing import Dict, List, Any, Optional, Callable
from database import get_supabase

supabase = get_supabase()


async def async_query(query_func: Callable) -> Any:
    """
    Generic async wrapper for any Supabase query operation.

    Args:
        query_func: Lambda or function that returns a Supabase query result

    Returns:
        Query result from Supabase

    Example:
        result = await async_query(
            lambda: supabase.table('users').select('*').eq('id', user_id).execute()
        )
    """
    return await asyncio.to_thread(query_func)


async def async_select(
    table: str,
    columns: str = '*',
    filters: Optional[Dict[str, Any]] = None,
    order_by: Optional[str] = None,
    order_desc: bool = False,
    limit: Optional[int] = None,
    single: bool = False
) -> Any:
    """
    Simplified SELECT query with common filters.

    Args:
        table: Table name
        columns: Columns to select (default: '*')
        filters: Dictionary of column=value filters (uses .eq())
        order_by: Column to order by
        order_desc: If True, order descending
        limit: Limit number of results
        single: If True, use .single() to return single row

    Returns:
        Query result from Supabase

    Example:
        # SELECT * FROM documents WHERE user_id='123' ORDER BY created_at DESC LIMIT 10
        result = await async_select(
            'documents',
            filters={'user_id': '123'},
            order_by='created_at',
            order_desc=True,
            limit=10
        )
    """
    def query():
        q = supabase.table(table).select(columns)

        if filters:
            for key, value in filters.items():
                q = q.eq(key, value)

        if order_by:
            q = q.order(order_by, desc=order_desc)

        if limit:
            q = q.limit(limit)

        if single:
            q = q.single()

        return q.execute()

    return await asyncio.to_thread(query)


async def async_insert(
    table: str,
    data: List[Dict[str, Any]] | Dict[str, Any],
    batch_size: int = 500
) -> Any:
    """
    Simplified INSERT with automatic batching for large datasets.

    Args:
        table: Table name
        data: Single dict or list of dicts to insert
        batch_size: Maximum rows per batch (default: 500)

    Returns:
        Query result from Supabase (last batch result if multiple batches)

    Example:
        # Insert single row
        result = await async_insert('documents', {'title': 'Test', 'user_id': '123'})

        # Insert multiple rows with batching
        chunks = [{'content': f'Chunk {i}'} for i in range(1000)]
        result = await async_insert('document_chunks', chunks, batch_size=500)
    """
    # Convert single dict to list for uniform handling
    if isinstance(data, dict):
        data = [data]

    # If data fits in single batch, insert directly
    if len(data) <= batch_size:
        return await asyncio.to_thread(
            lambda: supabase.table(table).insert(data).execute()
        )

    # Batch insert for large datasets
    result = None
    for batch_start in range(0, len(data), batch_size):
        batch = data[batch_start:batch_start + batch_size]
        result = await asyncio.to_thread(
            lambda b=batch: supabase.table(table).insert(b).execute()
        )

    return result


async def async_update(
    table: str,
    data: Dict[str, Any],
    filters: Dict[str, Any]
) -> Any:
    """
    Simplified UPDATE query with filters.

    Args:
        table: Table name
        data: Dictionary of column=value to update
        filters: Dictionary of column=value filters (uses .eq())

    Returns:
        Query result from Supabase

    Example:
        # UPDATE documents SET processed=true WHERE id='abc123'
        result = await async_update(
            'documents',
            data={'processed': True},
            filters={'id': 'abc123'}
        )
    """
    def query():
        q = supabase.table(table).update(data)

        for key, value in filters.items():
            q = q.eq(key, value)

        return q.execute()

    return await asyncio.to_thread(query)


async def async_delete(
    table: str,
    filters: Dict[str, Any]
) -> Any:
    """
    Simplified DELETE query with filters.

    Args:
        table: Table name
        filters: Dictionary of column=value filters (uses .eq())

    Returns:
        Query result from Supabase

    Example:
        # DELETE FROM document_chunks WHERE document_id='abc123'
        result = await async_delete(
            'document_chunks',
            filters={'document_id': 'abc123'}
        )
    """
    def query():
        q = supabase.table(table).delete()

        for key, value in filters.items():
            q = q.eq(key, value)

        return q.execute()

    return await asyncio.to_thread(query)


async def async_rpc(
    function_name: str,
    params: Optional[Dict[str, Any]] = None
) -> Any:
    """
    Call a PostgreSQL RPC function asynchronously.

    Args:
        function_name: Name of the RPC function
        params: Dictionary of parameters to pass

    Returns:
        Query result from Supabase

    Example:
        result = await async_rpc(
            'get_ideation_velocity',
            params={'p_client_id': '123', 'p_start_date': '2025-01-01'}
        )
    """
    return await asyncio.to_thread(
        lambda: supabase.rpc(function_name, params or {}).execute()
    )


# Convenience exports for common patterns
__all__ = [
    'async_query',
    'async_select',
    'async_insert',
    'async_update',
    'async_delete',
    'async_rpc',
]
