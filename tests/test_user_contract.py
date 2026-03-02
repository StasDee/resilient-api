from mockapi_client.logger import get_logger
import pytest

logger = get_logger(__name__)


# -------------------------
# Positive CRUD Tests
# -------------------------


@pytest.mark.contract
@pytest.mark.parametrize("index", range(5))
def test_user_crud_lifecycle(api_client, user_factory, register_sync_user, index):
    """
    Verifies full CRUD lifecycle. Users are registered in register_sync_user
    and will be deleted at the end of the module.
    """
    logger.info("-" * 60)
    logger.info(f"--- User {index} ---")

    # Create payload
    payload = user_factory.create_user_payload()
    logger.info(f"Payload created: {payload}")

    # Create user
    created = api_client.create_user(payload)
    user_id = created["id"]
    logger.info(f"User {user_id} created: {created}")

    # Register for cleanup
    register_sync_user(user_id)
    logger.info(f"User {user_id} registered for later cleanup.")

    # Fetch user
    fetched = api_client.get_user(user_id)
    logger.info(f"User {user_id} fetched: {fetched}")
    assert fetched["name"] == payload["name"]

    # Patch user
    patched = api_client.patch_user(user_id, {"name": f"renamed_{index}"})
    logger.info(f"User {user_id} patched: {patched}")
    assert patched["name"] == f"renamed_{index}", (
        f"Expected name to be renamed_{index}, but got {patched['name']}"
    )
