from core.normalizers import normalize_users
from core.validators import validate_users
from mockapi_client.logger import get_logger

logger = get_logger(__name__)


def test_create_and_fetch_user_scenario(api_client, register_sync_user):
    """
    End-to-end user lifecycle scenario:

    1. Create user
    2. Fetch user
    3. Normalize response
    4. Validate contract
    """

    user_data = {
        "first_name": "John",
        "last_name": "Doe",
        "email": "John.Doe@Example.com",
    }

    logger.debug(f"User data: {user_data}")

    # Step 1: create user
    created_user = api_client.create_user(user_data)

    logger.debug(f"Created user: {created_user}")

    # Register for cleanup
    user_id = created_user["id"]
    register_sync_user(user_id)
    logger.info(f"User {user_id} registered for later cleanup.")

    assert created_user is not None
    assert "id" in created_user

    # Step 2: fetch user
    fetched_user = api_client.get_user(created_user["id"])
    logger.debug(f"Fetched user: {fetched_user}")
    assert fetched_user is not None

    # Step 3: normalize
    normalized_users = normalize_users([fetched_user])
    logger.debug(f"Normalized users: {normalized_users}")

    # Step 4: validate
    validate_users(normalized_users)
