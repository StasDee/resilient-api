from mockapi_client.logger import get_logger

logger = get_logger(__name__)


class ValidationError(Exception):
    """Custom exception for validation failures."""


def validate_user_id(user: dict) -> None:
    """Validate that the user dictionary contains a valid unique identifier."""
    user_id = user.get("id")
    logger.debug("Validating user_id: %s", user_id)

    if not isinstance(user_id, str) or not user_id.strip():
        raise ValidationError("User id must be a non-empty string")


def validate_user_name(user: dict) -> None:
    """Validate the user's name (optional, but must be a non-empty string if present)."""
    name = user.get("name")
    logger.debug("Validating user_name: %s", name)

    if name is None:
        return

    if not isinstance(name, str) or not name.strip():
        raise ValidationError("Name must be a non-empty string if provided")


def validate_user_email(user: dict) -> None:
    """Validate presence + basic format of the user's email."""
    user_id = user.get("id", "Unknown ID")
    email = user.get("email")
    logger.debug("Validating user_email: %s", email)

    if not isinstance(email, str) or not email.strip():
        raise ValidationError(f"User [{user_id}]: Email is missing or not a string.")

    if "@" not in email or "." not in email.split("@")[-1]:
        raise ValidationError(f"User [{user_id}]: Invalid email format '{email}'.")


def validate_users(users: list[dict]) -> None:
    """Validate a list of users (batch entry point)."""
    if not isinstance(users, list):
        raise ValidationError("Users payload must be a list")

    for user in users:
        if not isinstance(user, dict):
            raise ValidationError("Each user must be a dict")

        logger.debug("Validating user: %s", user)
        validate_user_id(user)
        validate_user_email(user)
        validate_user_name(user)
