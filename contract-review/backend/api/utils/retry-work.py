"""
Retry Logic with Exponential Backoff

Provides decorators and utilities for retrying failed operations with
configurable backoff strategies and error handling.
"""

import time
import functools
import asyncio
from typing import Callable, TypeVar, Optional, Tuple, Type
from logger_config import get_logger

logger = get_logger(__name__)

T = TypeVar('T')


def retry_with_backoff(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    retry_on: Tuple[Type[Exception], ...] = (Exception,),
    log_attempts: bool = True
):
    """
    Decorator for retrying functions with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts (default: 3)
        initial_delay: Initial delay in seconds (default: 1.0)
        max_delay: Maximum delay in seconds (default: 60.0)
        exponential_base: Base for exponential backoff (default: 2.0)
        retry_on: Tuple of exception types to retry on
        log_attempts: Whether to log retry attempts

    Example:
        @retry_with_backoff(max_retries=3, initial_delay=2.0)
        def call_external_api():
            response = requests.get("https://api.example.com/data")
            return response.json()
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    result = func(*args, **kwargs)

                    # Log successful retry
                    if attempt > 0 and log_attempts:
                        logger.info(
                            f"Retry successful for {func.__name__} on attempt {attempt + 1}",
                            extra={"function": func.__name__, "attempt": attempt + 1}
                        )

                    return result

                except retry_on as e:
                    last_exception = e

                    # Don't retry on last attempt
                    if attempt >= max_retries:
                        if log_attempts:
                            logger.error(
                                f"All {max_retries + 1} attempts failed for {func.__name__}",
                                extra={
                                    "function": func.__name__,
                                    "attempts": max_retries + 1,
                                    "error": str(e)
                                }
                            )
                        raise

                    # Calculate delay with exponential backoff
                    delay = min(
                        initial_delay * (exponential_base ** attempt),
                        max_delay
                    )

                    if log_attempts:
                        logger.warning(
                            f"Retry attempt {attempt + 1}/{max_retries} for {func.__name__} after {delay:.1f}s",
                            extra={
                                "function": func.__name__,
                                "attempt": attempt + 1,
                                "delay": delay,
                                "error": str(e)
                            }
                        )

                    time.sleep(delay)

            # Should never reach here, but just in case
            if last_exception:
                raise last_exception

        return wrapper
    return decorator


def async_retry_with_backoff(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    retry_on: Tuple[Type[Exception], ...] = (Exception,),
    log_attempts: bool = True
):
    """
    Async version of retry_with_backoff decorator.

    Args:
        max_retries: Maximum number of retry attempts (default: 3)
        initial_delay: Initial delay in seconds (default: 1.0)
        max_delay: Maximum delay in seconds (default: 60.0)
        exponential_base: Base for exponential backoff (default: 2.0)
        retry_on: Tuple of exception types to retry on
        log_attempts: Whether to log retry attempts

    Example:
        @async_retry_with_backoff(max_retries=3, initial_delay=2.0)
        async def call_external_api():
            async with httpx.AsyncClient() as client:
                response = await client.get("https://api.example.com/data")
                return response.json()
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    result = await func(*args, **kwargs)

                    # Log successful retry
                    if attempt > 0 and log_attempts:
                        logger.info(
                            f"Retry successful for {func.__name__} on attempt {attempt + 1}",
                            extra={"function": func.__name__, "attempt": attempt + 1}
                        )

                    return result

                except retry_on as e:
                    last_exception = e

                    # Don't retry on last attempt
                    if attempt >= max_retries:
                        if log_attempts:
                            logger.error(
                                f"All {max_retries + 1} attempts failed for {func.__name__}",
                                extra={
                                    "function": func.__name__,
                                    "attempts": max_retries + 1,
                                    "error": str(e)
                                }
                            )
                        raise

                    # Calculate delay with exponential backoff
                    delay = min(
                        initial_delay * (exponential_base ** attempt),
                        max_delay
                    )

                    if log_attempts:
                        logger.warning(
                            f"Retry attempt {attempt + 1}/{max_retries} for {func.__name__} after {delay:.1f}s",
                            extra={
                                "function": func.__name__,
                                "attempt": attempt + 1,
                                "delay": delay,
                                "error": str(e)
                            }
                        )

                    await asyncio.sleep(delay)

            # Should never reach here, but just in case
            if last_exception:
                raise last_exception

        return wrapper
    return decorator


class CircuitBreaker:
    """
    Circuit breaker pattern implementation.

    Prevents repeated calls to a failing service by "opening" the circuit
    after a threshold of failures. The circuit will "half-open" after a
    timeout period to test if the service has recovered.

    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Too many failures, requests fail immediately
    - HALF_OPEN: Testing if service has recovered

    Example:
        breaker = CircuitBreaker(failure_threshold=5, timeout=60)

        @breaker.call
        def call_external_service():
            return requests.get("https://api.example.com/data")
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        timeout: float = 60.0,
        expected_exception: Type[Exception] = Exception
    ):
        """
        Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit
            timeout: Seconds to wait before attempting to close circuit
            expected_exception: Exception type to track for failures
        """
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.expected_exception = expected_exception

        self._failure_count = 0
        self._last_failure_time: Optional[float] = None
        self._state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

    def call(self, func: Callable[..., T]) -> Callable[..., T]:
        """
        Decorator to wrap function calls with circuit breaker logic.

        Args:
            func: Function to wrap

        Returns:
            Wrapped function with circuit breaker protection
        """
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            if self._state == "OPEN":
                # Check if timeout has elapsed
                if time.time() - self._last_failure_time < self.timeout:
                    logger.warning(
                        f"Circuit breaker OPEN for {func.__name__}",
                        extra={
                            "function": func.__name__,
                            "failure_count": self._failure_count,
                            "state": self._state
                        }
                    )
                    raise Exception(f"Circuit breaker OPEN for {func.__name__}")
                else:
                    # Transition to HALF_OPEN to test service
                    self._state = "HALF_OPEN"
                    logger.info(
                        f"Circuit breaker transitioning to HALF_OPEN for {func.__name__}",
                        extra={"function": func.__name__, "state": "HALF_OPEN"}
                    )

            try:
                result = func(*args, **kwargs)

                # Success - reset circuit
                if self._state == "HALF_OPEN":
                    logger.info(
                        f"Circuit breaker closing after successful call to {func.__name__}",
                        extra={"function": func.__name__, "state": "CLOSED"}
                    )

                self._failure_count = 0
                self._state = "CLOSED"
                return result

            except self.expected_exception as e:
                self._failure_count += 1
                self._last_failure_time = time.time()

                if self._failure_count >= self.failure_threshold:
                    self._state = "OPEN"
                    logger.error(
                        f"Circuit breaker OPENING for {func.__name__} after {self._failure_count} failures",
                        extra={
                            "function": func.__name__,
                            "failure_count": self._failure_count,
                            "state": "OPEN",
                            "error": str(e)
                        }
                    )

                raise

        return wrapper

    def reset(self):
        """Manually reset the circuit breaker"""
        self._failure_count = 0
        self._last_failure_time = None
        self._state = "CLOSED"
        logger.info("Circuit breaker manually reset")


# Pre-configured retry strategies for common scenarios
def retry_on_rate_limit(max_retries: int = 5):
    """
    Retry strategy specifically for API rate limits (429 errors).

    Uses longer delays suitable for rate limit recovery.
    """
    return retry_with_backoff(
        max_retries=max_retries,
        initial_delay=5.0,  # Start with 5 seconds
        max_delay=300.0,    # Max 5 minutes
        exponential_base=2.0,
        log_attempts=True
    )


def retry_on_network_error(max_retries: int = 3):
    """
    Retry strategy for transient network errors.

    Uses shorter delays suitable for quick recovery.
    """
    return retry_with_backoff(
        max_retries=max_retries,
        initial_delay=1.0,  # Start with 1 second
        max_delay=10.0,     # Max 10 seconds
        exponential_base=2.0,
        log_attempts=True
    )


def retry_on_server_error(max_retries: int = 3):
    """
    Retry strategy for server errors (5xx).

    Uses moderate delays for server recovery.
    """
    return retry_with_backoff(
        max_retries=max_retries,
        initial_delay=2.0,  # Start with 2 seconds
        max_delay=30.0,     # Max 30 seconds
        exponential_base=2.0,
        log_attempts=True
    )


__all__ = [
    'retry_with_backoff',
    'async_retry_with_backoff',
    'CircuitBreaker',
    'retry_on_rate_limit',
    'retry_on_network_error',
    'retry_on_server_error',
]
