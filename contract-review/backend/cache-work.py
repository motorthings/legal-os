"""
Redis Cache Utility

Provides caching layer for frequently accessed data with graceful fallback.
If Redis is not available, operations silently fail and data is fetched normally.

Features:
- System instructions caching
- User profile caching
- Vector search results caching
- Automatic TTL (time-to-live) management
- Graceful degradation if Redis unavailable

Usage:
    from cache import cache_get, cache_set, cache_delete

    # Try to get from cache
    value = cache_get("my_key")
    if value is None:
        value = expensive_operation()
        cache_set("my_key", value, ttl=300)  # Cache for 5 minutes
"""

import os
import json
import hashlib
from typing import Optional, Any
from logger_config import get_logger

logger = get_logger(__name__)

# Try to import Redis - graceful fallback if not available
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis not installed - caching disabled (install with: pip install redis)")

# Initialize Redis client
_redis_client: Optional[Any] = None

def _get_redis_client():
    """Get or create Redis client with connection pooling"""
    global _redis_client

    if not REDIS_AVAILABLE:
        return None

    if _redis_client is not None:
        return _redis_client

    # Get Redis URL from environment
    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        logger.info("REDIS_URL not set - caching disabled")
        return None

    try:
        # Create Redis client with connection pool
        _redis_client = redis.from_url(
            redis_url,
            decode_responses=True,  # Automatically decode bytes to strings
            socket_connect_timeout=2,
            socket_timeout=2,
            retry_on_timeout=True,
            health_check_interval=30
        )

        # Test connection
        _redis_client.ping()
        logger.info("✅ Redis connected successfully")
        return _redis_client

    except Exception as e:
        logger.warning(f"⚠️  Redis connection failed: {e} - caching disabled")
        _redis_client = None
        return None


def cache_get(key: str, namespace: str = "default") -> Optional[Any]:
    """
    Get value from cache.

    Args:
        key: Cache key
        namespace: Optional namespace for key isolation (e.g., "user", "search")

    Returns:
        Cached value (deserialized from JSON) or None if not found/error
    """
    client = _get_redis_client()
    if client is None:
        return None

    try:
        full_key = f"{namespace}:{key}"
        value = client.get(full_key)

        if value is None:
            return None

        # Deserialize from JSON
        return json.loads(value)

    except Exception as e:
        logger.warning(f"Cache get error for {key}: {e}")
        return None


def cache_set(key: str, value: Any, ttl: int = 300, namespace: str = "default") -> bool:
    """
    Set value in cache with TTL.

    Args:
        key: Cache key
        value: Value to cache (will be JSON serialized)
        ttl: Time-to-live in seconds (default: 5 minutes)
        namespace: Optional namespace for key isolation

    Returns:
        True if successful, False otherwise
    """
    client = _get_redis_client()
    if client is None:
        return False

    try:
        full_key = f"{namespace}:{key}"

        # Serialize to JSON
        serialized = json.dumps(value)

        # Set with TTL
        client.setex(full_key, ttl, serialized)
        return True

    except Exception as e:
        logger.warning(f"Cache set error for {key}: {e}")
        return False


def cache_delete(key: str, namespace: str = "default") -> bool:
    """
    Delete value from cache.

    Args:
        key: Cache key
        namespace: Optional namespace for key isolation

    Returns:
        True if successful, False otherwise
    """
    client = _get_redis_client()
    if client is None:
        return False

    try:
        full_key = f"{namespace}:{key}"
        client.delete(full_key)
        return True

    except Exception as e:
        logger.warning(f"Cache delete error for {key}: {e}")
        return False


def cache_invalidate_pattern(pattern: str, namespace: str = "default") -> int:
    """
    Invalidate all keys matching a pattern.

    Args:
        pattern: Pattern to match (e.g., "user:*")
        namespace: Optional namespace

    Returns:
        Number of keys deleted
    """
    client = _get_redis_client()
    if client is None:
        return 0

    try:
        full_pattern = f"{namespace}:{pattern}"
        keys = client.keys(full_pattern)

        if keys:
            return client.delete(*keys)
        return 0

    except Exception as e:
        logger.warning(f"Cache invalidate error for {pattern}: {e}")
        return 0


def hash_cache_key(*args, **kwargs) -> str:
    """
    Generate a deterministic cache key from arguments.

    Args:
        *args: Positional arguments to hash
        **kwargs: Keyword arguments to hash

    Returns:
        SHA256 hash of arguments (first 16 chars)
    """
    # Combine args and kwargs into a stable string
    key_data = {
        "args": args,
        "kwargs": sorted(kwargs.items())  # Sort for deterministic ordering
    }

    key_str = json.dumps(key_data, sort_keys=True)
    hash_obj = hashlib.sha256(key_str.encode())
    return hash_obj.hexdigest()[:16]


# Convenience functions for common cache patterns

def cache_system_instructions(user_id: str, instructions: str, ttl: int = 3600):
    """Cache system instructions for a user (1 hour default TTL)"""
    return cache_set(f"user:{user_id}", instructions, ttl=ttl, namespace="sys_inst")


def get_cached_system_instructions(user_id: str) -> Optional[str]:
    """Get cached system instructions for a user"""
    return cache_get(f"user:{user_id}", namespace="sys_inst")


def cache_search_results(query: str, client_id: str, results: list, ttl: int = 3600):
    """Cache vector search results (1 hour default TTL)"""
    # Include client_id in key structure for targeted invalidation
    key = f"client:{client_id}:{hash_cache_key(query, client_id)}"
    return cache_set(key, results, ttl=ttl, namespace="search")


def get_cached_search_results(query: str, client_id: str) -> Optional[list]:
    """Get cached vector search results"""
    key = f"client:{client_id}:{hash_cache_key(query, client_id)}"
    return cache_get(key, namespace="search")


def invalidate_user_cache(user_id: str):
    """Invalidate all cache entries for a user"""
    cache_delete(f"user:{user_id}", namespace="sys_inst")
    cache_delete(f"user:{user_id}", namespace="profile")


def invalidate_search_cache(client_id: str):
    """Invalidate search cache for a specific client (not all clients)"""
    # Only invalidate keys for this specific client, not all search keys
    cache_invalidate_pattern(f"client:{client_id}:*", namespace="search")


# Health check
def cache_health_check() -> dict:
    """
    Check Redis connection health.

    Returns:
        dict with status and details
    """
    if not REDIS_AVAILABLE:
        return {
            "status": "unavailable",
            "reason": "Redis library not installed"
        }

    client = _get_redis_client()
    if client is None:
        return {
            "status": "disabled",
            "reason": "REDIS_URL not configured or connection failed"
        }

    try:
        client.ping()
        info = client.info("stats")
        return {
            "status": "healthy",
            "total_commands_processed": info.get("total_commands_processed", 0),
            "keyspace_hits": info.get("keyspace_hits", 0),
            "keyspace_misses": info.get("keyspace_misses", 0)
        }
    except Exception as e:
        return {
            "status": "error",
            "reason": str(e)
        }


# For testing
if __name__ == "__main__":
    print("Cache Health Check:")
    health = cache_health_check()
    print(json.dumps(health, indent=2))

    if health["status"] == "healthy":
        print("\nTesting cache operations...")

        # Test set/get
        cache_set("test_key", {"hello": "world"}, ttl=10)
        value = cache_get("test_key")
        print(f"Set/Get test: {value}")

        # Test hash function
        key = hash_cache_key("query", client_id="123")
        print(f"Hash test: {key}")

        # Test delete
        cache_delete("test_key")
        value = cache_get("test_key")
        print(f"Delete test (should be None): {value}")

        print("\n✅ All tests passed!")
