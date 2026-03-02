def normalize_user(raw_user: dict) -> dict:
    user_id = raw_user.get("id")
    email = raw_user.get("email")

    def is_junk(key: str, value: object) -> bool:
        """Detect MockAPI auto-fill junk values like 'name 14'."""
        if not isinstance(value, str):
            return False
        return value == f"{key} {user_id}"

    name = raw_user.get("name")
    if is_junk("name", name):
        name = None

    if not name:
        first_name = raw_user.get("first_name")
        last_name = raw_user.get("last_name")

        if is_junk("first_name", first_name):
            first_name = None
        if is_junk("last_name", last_name):
            last_name = None

        if first_name and last_name:
            name = f"{first_name} {last_name}"
        else:
            name = first_name or last_name

    return {
        "id": str(user_id) if user_id is not None else None,
        "email": email.lower() if isinstance(email, str) else None,
        "name": name,
    }


def normalize_users(raw_users: list) -> list[dict]:
    if not isinstance(raw_users, list):
        return []

    return [normalize_user(user) for user in raw_users if isinstance(user, dict)]
