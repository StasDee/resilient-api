import pytest
from mockapi_client.logger import get_logger
from core.normalizers import normalize_users
from core.validators import validate_users

logger = get_logger(__name__)

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.contract,
    pytest.mark.edge,
]


@pytest.mark.asyncio
@pytest.mark.contract
@pytest.mark.edge
async def test_patch_before_fetch(async_api_client, user_factory, register_async_user):
    """
    Edge-case workflow test: patch a user immediately after creation
    without fetching it first.

    Purpose:
    - Simulate uncommon user behavior
    - Verify API handles multi-step dependencies gracefully

    Validation:
    - Patch succeeds without errors
    - Response conforms to contract
    - User is tracked for cleanup
    """
    logger.info("-" * 60)
    logger.info("Starting edge-case test: patch before fetch")

    payload = user_factory.create_user_payload()
    created = await async_api_client.create_user(payload)
    user_id = created["id"]
    await register_async_user(user_id)
    logger.info(f"User created: {payload}")

    # Patch immediately
    patch_payload = {"name": "EdgeCaseUser"}
    patched = await async_api_client.patch_user(user_id, patch_payload)
    logger.info(f"User patched immediately: {patched}")

    normalized_users = normalize_users([patched])
    validate_users(normalized_users)
    logger.info("Edge-case workflow test completed successfully")
