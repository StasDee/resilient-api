from functools import wraps
from requests.exceptions import HTTPError, Timeout, ConnectionError
import time
import random
from .logger import get_logger

logger = get_logger(__name__)


def _parse_retry_after(value: str) -> float | None:
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def retry_on_failure(num_retries: int = 4, wait_seconds: float = 1.0):
    """
    Retry on:
      - network errors
      - 5xx
      - 429 (rate limit)

    Uses exponential backoff with jitter.
    Respects Retry-After header if present (best-effort).
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            wait = float(wait_seconds)

            for attempt in range(num_retries + 1):
                try:
                    res = func(*args, **kwargs)
                    if attempt > 0:
                        logger.info(f"Recovered on attempt {attempt + 1}")
                    return res

                except (Timeout, ConnectionError, HTTPError) as e:
                    status = None
                    retry_after = None

                    if isinstance(e, HTTPError) and e.response is not None:
                        status = e.response.status_code
                        retry_after = _parse_retry_after(
                            e.response.headers.get("Retry-After", "")
                        )

                        # Non-retryable client errors (except 429)
                        if status < 500 and status != 429:
                            raise

                    if attempt == num_retries:
                        logger.error(
                            f"All {num_retries + 1} attempts failed. Last error: {e}"
                        )
                        raise

                    # Use Retry-After when rate limited, otherwise exponential backoff
                    sleep_for = retry_after if retry_after is not None else wait
                    # Add small jitter to avoid thundering herd
                    sleep_for = min(sleep_for + random.uniform(0, 0.2), 15.0)

                    logger.warning(
                        f"[Attempt {attempt + 1}/{num_retries + 1}] "
                        f"Caught {type(e).__name__} (status={status}). Retrying in {sleep_for:.2f}s..."
                    )
                    time.sleep(sleep_for)

                    # exponential backoff capped
                    wait = min(wait * 2, 10.0)

        return wrapper

    return decorator
