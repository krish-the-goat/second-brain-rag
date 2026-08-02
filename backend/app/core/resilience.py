"""
Resilience utilities: retry decorators and circuit-breaker patterns
for external service calls (Neo4j, ChromaDB, Redis).
"""

import os
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)
from app.core.logging import get_logger

logger = get_logger(__name__)

# --- Configuration ---
MAX_RETRIES = int(os.getenv("DB_MAX_RETRIES", "3"))
MIN_WAIT = float(os.getenv("DB_RETRY_MIN_WAIT", "0.5"))
MAX_WAIT = float(os.getenv("DB_RETRY_MAX_WAIT", "5.0"))


def db_retry(operation_name: str = "database"):
    """
    Retry decorator for synchronous database operations (Neo4j, ChromaDB).

    Retries on any Exception with exponential backoff.
    Logs each retry attempt at warning level.
    """
    return retry(
        stop=stop_after_attempt(MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=MIN_WAIT, max=MAX_WAIT),
        retry=retry_if_exception_type(Exception),
        before_sleep=before_sleep_log(logger, "warning"),
        reraise=True,
    )


def async_db_retry(operation_name: str = "database"):
    """
    Retry decorator for async database operations.

    Same semantics as db_retry but works with async functions.
    """
    return retry(
        stop=stop_after_attempt(MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=MIN_WAIT, max=MAX_WAIT),
        retry=retry_if_exception_type(Exception),
        before_sleep=before_sleep_log(logger, "warning"),
        reraise=True,
    )
