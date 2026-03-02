from mockapi_client.logger import get_logger
import pytest

logger = get_logger(__name__)


@pytest.mark.scenario
def test_users_end_to_end_scenario(api_client, user_factory, register_sync_user):
    logger.info("Starting end-to-end scenario test")
    count = 5

    for index in range(count):
        logger.info("-" * 60)
        logger.info(f"\n--- User {index} ---")

        # Create payload
        payload = user_factory.create_user_payload()
        logger.info(f"Payload created: {payload}")

        # Create user
        created = api_client.create_user(payload)
        user_id = created["id"]
        logger.info(f"User: {user_id} created: {created}")

        # Register user ID in the cleanup registry
        register_sync_user(user_id)

        logger.info(f"User: {user_id} registered for later cleanup.")

        # Verify user
        fetched = api_client.get_user(user_id)
        logger.info(f"User: {user_id} fetched: {fetched}")
        assert fetched["name"] == payload["name"]

        # Patch user
        patched = api_client.patch_user(user_id, {"name": f"renamed_{index}"})
        logger.info(f"User: {user_id} patched: {patched}")
        assert patched["name"] == f"renamed_{index}", (
            f"Expected name to be renamed_{index} but got {patched['name']}"
        )
