from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest

from mockapi_client.logger import get_logger

logger = get_logger(__name__)

# This test intentionally creates load -> rate limiting (429) is expected sometimes.
pytestmark = pytest.mark.concurrency


@pytest.mark.contract
def test_concurrent_user_creation(api_client, user_factory, register_sync_user):
    """
    Creates 10 users in parallel using threads and checks for unique IDs.
    """
    logger.info("-" * 60)
    logger.info("Starting thread-based concurrent user creation test")

    def create_user_task(index):
        payload = user_factory.create_user_payload()
        logger.info(f"[Thread {index}] Payload: {payload}")
        created = api_client.create_user(payload)
        register_sync_user(created["id"])
        return created

    results = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(create_user_task, i) for i in range(10)]
        for future in as_completed(futures):
            user = future.result()
            logger.info(f"User created: {user}")
            results.append(user)

    logger.info(f"All users created: {results}")

    # Check total count
    assert len(results) == 10, f"Expected 10 users, got {len(results)}"

    # Check all users have unique IDs
    ids = [u["id"] for u in results]
    duplicates = [id for id in ids if ids.count(id) > 1]
    if duplicates:
        logger.error(f"Duplicate user IDs detected: {duplicates}")
        pytest.fail(f"Duplicate user IDs detected: {duplicates}")
    else:
        logger.info("✓ All user IDs are unique")

    # Optional: sanity check that all have 'id' key
    assert all("id" in u for u in results)
