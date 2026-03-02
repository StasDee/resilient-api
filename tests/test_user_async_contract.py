import pytest

from mockapi_client.logger import get_logger

from core.normalizers import normalize_users
from core.validators import validate_users

logger = get_logger(__name__)


@pytest.mark.asyncio
@pytest.mark.contract
async def test_async_user_create_and_validate(
    async_api_client, user_factory, register_async_user
):
    """
    Async contract test:
    1. Create user asynchronously
    2. Normalize API response
    3. Validate contract rules
    """
    logger.info("Creating async user for contract test")

    payload = user_factory.create_user_payload(
        first_name="Async", last_name="User", email="async.user@test.com"
    )

    created_user = await async_api_client.create_user(payload)
    await register_async_user(created_user["id"])
    assert created_user is not None
    assert "id" in created_user

    normalized = normalize_users([created_user])
    validate_users(normalized)
