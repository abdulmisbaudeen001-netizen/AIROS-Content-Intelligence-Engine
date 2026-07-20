"""
AIROS Content Intelligence Engine
Retry utility — exponential backoff decorator.
"""

import time
import functools
from logger import get_logger

logger = get_logger("retry")


def with_retry(max_attempts: int = 3, delay: float = 2.0, backoff: float = 2.0, exceptions=(Exception,)):
    """
    Decorator: retry a function on failure with exponential backoff.

    Args:
        max_attempts: Total attempts (including first).
        delay:        Initial wait in seconds.
        backoff:      Multiplier applied to delay after each failure.
        exceptions:   Exception types to catch and retry on.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            wait = delay
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_attempts:
                        logger.error(f"{func.__name__} failed after {max_attempts} attempts | {e}")
                        raise
                    logger.warning(f"{func.__name__} attempt {attempt} failed | retrying in {wait}s | {e}")
                    time.sleep(wait)
                    wait *= backoff
        return wrapper
    return decorator
