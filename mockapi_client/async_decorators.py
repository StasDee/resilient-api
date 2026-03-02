import asyncio
import functools
import random
import httpx

from mockapi_client.logger import get_logger

logger = get_logger(__name__)


def _parse_retry_after(value: str) -> float | None:
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def async_retry(attempts: int = 4, base_delay: float = 1.0):
    """
    Retry on:
      - httpx.RequestError (network)
      - HTTP 5xx
      - HTTP 429

    Do NOT retry on other 4xx.
    Uses exponential backoff + jitter and best-effort Retry-After support.
    """

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            delay = float(base_delay)

            for attempt in range(attempts):
                try:
                    return await func(*args, **kwargs)

                except httpx.HTTPStatusError as e:
                    status = e.response.status_code
                    # Don't retry normal 4xx (except 429)
                    if status < 500 and status != 429:
                        raise

                    if attempt == attempts - 1:
                        raise

                    retry_after = _parse_retry_after(
                        e.response.headers.get("Retry-After", "")
                    )
                    sleep_for = retry_after if retry_after is not None else delay
                    sleep_for = min(sleep_for + random.uniform(0, 0.2), 15.0)

                    logger.warning(
                        f"[Attempt {attempt + 1}/{attempts}] HTTP {status}. Retrying in {sleep_for:.2f}s..."
                    )
                    await asyncio.sleep(sleep_for)
                    delay = min(delay * 2, 10.0)

                except httpx.RequestError as e:
                    if attempt == attempts - 1:
                        raise
                    sleep_for = min(delay + random.uniform(0, 0.2), 15.0)
                    logger.warning(
                        f"[Attempt {attempt + 1}/{attempts}] Network error: {e}. Retrying in {sleep_for:.2f}s..."
                    )
                    await asyncio.sleep(sleep_for)
                    delay = min(delay * 2, 10.0)

        return wrapper

    return decorator
