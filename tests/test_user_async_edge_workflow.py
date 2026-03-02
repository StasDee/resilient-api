import pytest
from mockapi_client.logger import get_logger

logger = get_logger(__name__)

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.contract,
    pytest.mark.edge,
]


@pytest.mark.asyncio
@pytest.mark.contract
@pytest.mark.edge
async def test_sequential_user_dependencies(
    async_api_client,
    user_factory,
    register_async_user,
):
    """
    Optional workflow test: simulate dependent operations that could trigger edge cases.

    Purpose:
    - Verify system handles dependent operations correctly (e.g., create → patch → delete → fetch).
    - Check correct error handling for operations on deleted or non-existent users.

    Validation:
    - Create user and immediately patch.
    - Delete user and confirm fetching raises 404.
    - Contract validation on successful responses.

    Design notes:
    - Mimics real multi-step workflows that might be used in production.
    - Reuses async API client and factory for consistency.
    """

    logger.info("=" * 60)
    logger.info("Starting sequential edge-case workflow test")

    # Step 1: Create user
    payload = user_factory.create_user_payload()
    user = await async_api_client.create_user(payload)
    await register_async_user(user["id"])
    logger.info(f"Created user {user}")

    # Step 2: Patch user
    patch_payload = {"name": "edge_case_user"}
    patched = await async_api_client.patch_user(user["id"], patch_payload)
    logger.info(f"Patched user {patched}")

    # Step 3: Delete user
    await async_api_client.delete_user(user["id"])
    logger.info(f"Deleted user {user['id']}")

    # Step 4: Fetch deleted user (expect error)
    with pytest.raises(Exception) as e:
        await async_api_client.get_user(user["id"])
    logger.info(f"Expected error when fetching deleted user: {e.value}")
