from mockapi_client.logger import get_logger
from mockapi_client.client import UsersApiClient
from mockapi_client.factory import UserFactory

logger = get_logger(__name__)


def user_scenario(api: UsersApiClient, factory: UserFactory, count: int = 5):
    """
    Orchestrates the lifecycle for multiple users.
    """
    created_ids = []

    # 1. CREATE & VERIFY (GET)
    logger.info("-" * 60)
    logger.info(f"--- Step 1: Creating and verifying {count} users ---")
    for _ in range(count):
        logger.info("-" * 60)
        payload = factory.create_user_payload()
        logger.info(f"Generated payload for user: {payload}")

        # POST
        created = api.create_user(payload)
        user_id = created["id"]
        created_ids.append(user_id)
        logger.info(f"Created user: {payload['name']} (ID: {user_id})")

        # GET
        fetched = api.get_user(user_id)
        logger.info(f"Fetched user: {fetched}")
        assert fetched and fetched["name"] == payload["name"], (
            f"Verification failed for {user_id}"
        )
        logger.info("Creation - Fetching success")
    logger.info("-" * 60)
    logger.info("All users successfully created and verified.")
    logger.info("-" * 60)

    # 2. PATCH (Partial Update)
    if created_ids:
        target_id = created_ids[0]
        logger.info(f"--- Step 2: Patching user {target_id} ---")
        patch_data = {"name": "renamed_user"}
        patched = api.patch_user(target_id, patch_data)
        assert patched["name"] == "renamed_user", (
            f"Rename user: {created_ids[0]} to renamed_user failed"
        )
        logger.info(f"Patched user: {patched}")
        logger.info(f"User {target_id} successfully renamed to name: renamed_user")

    # 3. DELETE (Cleanup)
    logger.info("-" * 60)
    logger.info("--- Step 3: Deleting all users ---")

    failed_deletions = []

    for user_id in created_ids:
        logger.debug(f"Deleting user {user_id}...")
        api.delete_user(user_id)

        # Verify
        if api.wait_until_deleted(user_id):
            logger.debug(f"Successfully verified deletion of user {user_id}")
        else:
            logger.error(f"Timeout deleting for user: {user_id}")
            failed_deletions.append(user_id)

    if failed_deletions:
        raise Exception(f"Cleanup failed for: {failed_deletions}")

    logger.info("-" * 60)
    logger.info("Cleanup completed successfully")


def main():
    factory = UserFactory()

    with UsersApiClient() as api:
        try:
            user_scenario(api, factory, count=5)
            logger.info("Task completed successfully!")
        except Exception as e:
            logger.error(f"Scenario failed: {e}")
        finally:
            # This runs even if an exception was raised
            factory.reset()
            logger.debug("UserFactory memory cleared")


if __name__ == "__main__":
    main()
