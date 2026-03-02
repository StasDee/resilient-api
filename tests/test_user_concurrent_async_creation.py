import asyncio
import pytest

from mockapi_client.logger import get_logger
from core.normalizers import normalize_users
from core.validators import validate_users

logger = get_logger(__name__)

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.contract,
    pytest.mark.concurrency,
]


@pytest.mark.asyncio
@pytest.mark.contract
@pytest.mark.parametrize("concurrent_users", [5, 10, 20])
async def test_concurrent_user_creation(
    async_api_client,
    user_factory,
    register_async_user,
    concurrent_users,
):
    """
    Verify that the Users API correctly handles concurrent user creation requests.

    Purpose:
    - Ensure the backend can process multiple CREATE requests in parallel
      without race conditions, partial failures, or corrupted responses.

    What this test validates:
    - Parallel execution of multiple `create_user` calls using asyncio
    - Each request completes successfully
    - Each created user has a unique ID
    - All created users are registered for cleanup
    - Each user response passes contract validation

    Design notes:
    - Uses async API client backed by httpx.AsyncClient
    - Reuses existing factory, logging, and cleanup mechanisms
    - Keeps validation lightweight to avoid flakiness
    """

    logger.info("-" * 60)
    logger.info(f"Starting concurrent user creation test with {concurrent_users} users")

    # Prepare payloads
    payloads = [user_factory.create_user_payload() for _ in range(concurrent_users)]
    logger.info(f"Prepared {concurrent_users} user payloads")

    # Create users concurrently
    tasks = [async_api_client.create_user(payload) for payload in payloads]
    results = await asyncio.gather(*tasks)

    logger.info("All concurrent create requests completed")

    # Normalize and validate responses
    normalized_users = normalize_users(results)
    validate_users(normalized_users)
    logger.info("All concurrent user responses passed contract validation")

    # Basic checks and cleanup
    assert len(results) == concurrent_users

    user_ids = set()
    for user in results:
        assert user is not None
        assert "id" in user
        user_ids.add(user["id"])
        await register_async_user(user["id"])
        logger.info(f"User created concurrently: {user}")

    # Ensure all IDs are unique
    assert len(user_ids) == concurrent_users, (
        "Duplicate user IDs detected during concurrent creation"
    )

    logger.info(
        f"Concurrent user creation test for {concurrent_users} users completed successfully"
    )
