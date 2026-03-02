from uuid import uuid4


class UserFactory:
    """
    Generates guaranteed unique user data for testing.
    """

    def __init__(self):
        # Tracking used names to ensure uniqueness during a single test run
        self._used_names = set()

    def _generate_unique_name(self) -> str:
        while True:
            # Generate a short unique identifier
            name = f"user_{uuid4().hex[:8]}"
            if name not in self._used_names:
                self._used_names.add(name)
                return name

    def create_user_payload(self, **overrides) -> dict:
        """
        Generate a user payload with unique defaults.
        Fields passed in `overrides` will replace the defaults.
        """
        username = self._generate_unique_name()
        base_payload = {"name": username, "email": f"{username}@example.com"}
        return base_payload | overrides

    def reset(self):
        """
        Clear the history of used names.
        """
        self._used_names.clear()
