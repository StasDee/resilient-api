import asyncio

import pytest

from mockapi_client.logger import get_logger

logger = get_logger(__name__)

# Burst workflow = stress / rate-limit prone.
pytestmark = pytest.mark.concurrency


@pytest.mark.external
@pytest.mark.asyncio
@pytest.mark.parametrize("users_count", [10])
async def test_burst_user_workflow(
    async_api_client, user_factory, register_async_user, users_count
):
    """
    Burst workflow test: create many users concurrently.
    This is intentionally stressy and belongs to the concurrency tier.
    """
    logger.info("-" * 60)
    logger.info("Starting burst workflow with %s users", users_count)

    async def workflow_task(i: int):
        payload = user_factory.create_user_payload()
        logger.info("[Task %s] Creating user", i)
        user = await async_api_client.create_user(payload)

        # Register for teardown cleanup (best-effort)
        try:
            await register_async_user(user["id"])
        except Exception:
            pass

        return user

    tasks = [workflow_task(i) for i in range(users_count)]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    successes = [r for r in results if not isinstance(r, Exception)]
    failures = [r for r in results if isinstance(r, Exception)]

    logger.info("Successes: %s / %s", len(successes), users_count)
    if failures:
        logger.warning("Failures: %s", len(failures))
        for f in failures[:5]:
            logger.warning("  %s", f)

    # For stress tests we only require that at least one succeeded
    assert successes, "All burst workflow tasks failed!"
