import asyncio
from typing import Any, Dict, Optional, cast

import httpx

from .async_decorators import async_retry
from mockapi_client.logger import get_logger

logger = get_logger(__name__)

_MAX_ELEMENTS_MSG = "Max number of elements reached for this resource!"


class AsyncUsersApiClient:
    """
    Async client where `base_url` is the full collection endpoint,
    e.g. https://.../api/v1/users
    """

    def __init__(self, base_url: str, headers: dict):
        if not base_url:
            raise ValueError(
                "BASE_URL is not set. Provide BASE_URL env var or .env file."
            )
        self.base_url = base_url.rstrip("/")
        self.headers = headers or {}
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        self._client = httpx.AsyncClient(headers=self.headers, timeout=5)
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if self._client:
            await self._client.aclose()

    def _client_or_raise(self) -> httpx.AsyncClient:
        assert self._client is not None, (
            "AsyncUsersApiClient not initialized; use 'async with'."
        )
        return self._client

    # -----------------------------
    # Payload normalization (match sync behavior)
    # -----------------------------
    @staticmethod
    def _normalize_user_payload(payload: dict) -> dict:
        data = dict(payload or {})

        if not data.get("name"):
            first = data.get("first_name")
            last = data.get("last_name")
            parts = [
                p.strip() for p in [first, last] if isinstance(p, str) and p.strip()
            ]
            if parts:
                data["name"] = " ".join(parts)

        data.pop("first_name", None)
        data.pop("last_name", None)
        return data

    def _is_dataset_full(self, exc: httpx.HTTPStatusError) -> bool:
        try:
            return exc.response.status_code == 400 and _MAX_ELEMENTS_MSG in (
                exc.response.text or ""
            )
        except Exception:
            return False

    async def _list_users_raw(self) -> list[dict]:
        client = self._client_or_raise()
        resp = await client.get(self.base_url)
        resp.raise_for_status()
        data = resp.json()
        return cast(list[dict], data) if isinstance(data, list) else []

    async def _free_some_slots(self, max_delete: int = 15) -> None:
        """
        Best-effort cleanup: delete a few existing users to free slots.
        """
        try:
            users = await self._list_users_raw()
        except Exception as e:
            logger.warning("Could not list users for cleanup: %s", e)
            return

        if not users:
            logger.warning("No users returned from list; cannot free slots.")
            return

        to_delete: list[str] = []
        for u in users:
            uid = u.get("id")
            if uid:
                to_delete.append(str(uid))
            if len(to_delete) >= max_delete:
                break

        if not to_delete:
            logger.warning("No deletable user ids found; cannot free slots.")
            return

        logger.warning(
            "Dataset full -> deleting %s existing users to free slots...",
            len(to_delete),
        )
        deleted = 0
        for uid in to_delete:
            try:
                await self.delete_user(uid)
                deleted += 1
            except Exception as e:
                logger.warning("Cleanup delete failed for id=%s: %s", uid, e)

        logger.warning("Cleanup completed. Deleted=%s/%s", deleted, len(to_delete))

    # -----------------------------
    # API methods
    # -----------------------------
    @async_retry()
    async def create_user(self, payload: dict) -> Dict[str, Any]:
        client = self._client_or_raise()
        normalized = self._normalize_user_payload(payload)

        try:
            resp = await client.post(self.base_url, json=normalized)
            resp.raise_for_status()
            return cast(Dict[str, Any], resp.json())
        except httpx.HTTPStatusError as e:
            if self._is_dataset_full(e):
                await self._free_some_slots()
                resp2 = await client.post(self.base_url, json=normalized)
                resp2.raise_for_status()
                return cast(Dict[str, Any], resp2.json())
            raise

    @async_retry()
    async def delete_user(self, user_id: str) -> None:
        client = self._client_or_raise()
        resp = await client.delete(f"{self.base_url}/{user_id}")
        if resp.status_code == 404:
            return
        resp.raise_for_status()

    @async_retry()
    async def get_user(self, user_id: str) -> Dict[str, Any]:
        client = self._client_or_raise()
        resp = await client.get(f"{self.base_url}/{user_id}")
        resp.raise_for_status()
        return cast(Dict[str, Any], resp.json())

    @async_retry()
    async def patch_user(
        self, user_id: str, partial_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        client = self._client_or_raise()
        normalized = self._normalize_user_payload(partial_data)
        resp = await client.patch(f"{self.base_url}/{user_id}", json=normalized)
        resp.raise_for_status()
        return cast(Dict[str, Any], resp.json())

    async def list_users(self) -> list[dict]:
        return await self._list_users_raw()

    async def wait_until_deleted(
        self, user_id: str, retries: int = 5, delay: float = 1.0
    ) -> bool:
        """
        Polls until the user with the given ID is no longer found.
        Returns True if deletion is confirmed (404) or we give up after retries.
        """
        client = self._client_or_raise()

        for attempt in range(1, retries + 1):
            try:
                resp = await client.get(f"{self.base_url}/{user_id}")
                status = resp.status_code
                logger.debug(
                    "Attempt %s - user %s status: %s", attempt, user_id, status
                )

                if status == 404:
                    return True

            except httpx.RequestError:
                logger.debug("Network error for user %s, retrying...", user_id)

            await asyncio.sleep(delay)

        logger.warning(
            "User %s may still exist; giving up after %s retries", user_id, retries
        )
        return False
