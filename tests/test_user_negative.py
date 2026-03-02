import pytest
from requests.exceptions import HTTPError

from core.validators import ValidationError, validate_user_email
from mockapi_client.logger import get_logger

logger = get_logger(__name__)

pytestmark = pytest.mark.external


@pytest.mark.parametrize(
    "payload",
    [
        {"email": "invalid_email"},  # no '@'
        {"first_name": "Alice"},  # missing email -> server may autofill junk
        {},  # missing everything -> server may autofill junk
    ],
)
def test_user_creation_negative(api_client, payload, register_sync_user):
    """
    External APIs differ: some reject invalid payloads, others accept and store junk.
    Portfolio-friendly expectation:
      - If API rejects -> OK (4xx)
      - If API accepts -> our local validator must detect invalid email
    """
    logger.info("-" * 60)
    logger.info("Testing negative user creation with payload: %s", payload)

    try:
        user = api_client.create_user(payload)

        # If creation succeeded, register cleanup
        user_id = user.get("id")
        if user_id:
            register_sync_user(user_id)
            logger.info("User %s registered for later cleanup.", user_id)

        # The external service accepted bad input — validate locally
        with pytest.raises(ValidationError):
            validate_user_email(user)

    except HTTPError as e:
        # Rejection is also acceptable. Keep assertion loose but meaningful.
        status = e.response.status_code if e.response is not None else None
        logger.info(
            "API rejected payload (expected acceptable outcome). status=%s", status
        )
        assert status is None or 400 <= status < 500


def test_fetch_nonexistent_user(api_client):
    """
    Client contract: GET on missing user returns None (404 mapped to None).
    """
    non_existent_id = "999999"
    logger.info("-" * 60)
    logger.info("Testing fetch of non-existent user ID: %s", non_existent_id)

    user = api_client.get_user(non_existent_id)
    assert user is None, (
        f"Expected None for non-existent user {non_existent_id}, got: {user}"
    )


def test_patch_user_invalid_data(api_client, user_factory, register_sync_user):
    """
    External APIs differ: some reject invalid patches, others accept.
    Portfolio-friendly expectation:
      - If API rejects -> OK (4xx)
      - If API accepts -> our local validator must detect invalid email
    """
    logger.info("-" * 60)
    logger.info("Creating valid user to test invalid patch")

    created = api_client.create_user(user_factory.create_user_payload())
    user_id = created["id"]
    register_sync_user(user_id)

    logger.info("User created for patch test: %s", created)

    invalid_patch = {"email": "invalid_email"}
    logger.info("Attempting invalid patch: %s on user %s", invalid_patch, user_id)

    try:
        updated = api_client.patch_user(user_id, invalid_patch)

        # If patch succeeded, email might now be invalid — validate locally
        with pytest.raises(ValidationError):
            validate_user_email(updated)

    except HTTPError as e:
        status = e.response.status_code if e.response is not None else None
        logger.info("API rejected invalid patch (acceptable). status=%s", status)
        assert status is None or 400 <= status < 500
