import pytest

from mockapi_client.logger import get_logger

logger = get_logger(__name__)

pytestmark = pytest.mark.concurrency


@pytest.mark.external
@pytest.mark.asyncio
async def test_user_burst_unique_ids(
    async_api_client, user_factory, register_async_user
):
    """
    Fire a burst of create requests and ensure created users have unique IDs.
    This test is intentionally rate-limit prone and belongs to the concurrency tier.
    """
    burst_size = 20

    coros = []
    for _ in range(burst_size):
        payload = user_factory.create_user_payload()
        coros.append(async_api_client.create_user(payload))

    results = []
    failures = []

    for coro in coros:
        try:
            user = await coro
            results.append(user)
            await register_async_user(user["id"])
        except Exception as e:
            failures.append(str(e))

    logger.info("\nCreated users (%s):", len(results))
    for u in results:
        logger.info("  id=%s email=%s", u.get("id"), u.get("email"))

    logger.warning("\nFailures (%s):", len(failures))
    for f in failures:
        logger.warning("%s", f)

    assert results, "All user creation requests failed!"

    ids = [u["id"] for u in results if "id" in u]
    assert len(ids) == len(set(ids)), "Duplicate user IDs detected!"
