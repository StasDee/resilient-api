from __future__ import annotations

from time import sleep
from typing import Any, Dict, List, Optional, cast

import requests
from requests.exceptions import HTTPError

from mockapi_client.logger import get_logger
from .config import BASE_URL, DEFAULT_TIMEOUT, TOKEN
from .decorators import retry_on_failure

logger = get_logger(__name__)

_MAX_ELEMENTS_MSG = "Max number of elements reached for this resource!"


class UsersApiClient:
    def __init__(
        self,
        base_url: str = BASE_URL,
        timeout: int = DEFAULT_TIMEOUT,
        session: Optional[requests.Session] = None,
    ):
        if not base_url:
            raise ValueError(
                "BASE_URL is not set. Provide BASE_URL env var or .env file."
            )

        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = session or requests.Session()

        headers = {"Content-Type": "application/json"}
        if TOKEN:
            headers["Authorization"] = f"Bearer {TOKEN}"
        self.session.headers.update(headers)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.session.close()

    @staticmethod
    def _normalize_user_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
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

    def _request(self, method: str, endpoint: str = "", **kwargs) -> Optional[Any]:
        url = f"{self.base_url}/{endpoint}".rstrip("/")
        response = self.session.request(method, url, timeout=self.timeout, **kwargs)

        if response.status_code == 404:
            return None

        if response.status_code >= 400:
            body = (response.text or "").strip()
            snippet = body[:800]
            msg = f"{response.status_code} {response.reason} for url {url}. Body: {snippet}"
            logger.error(
                "HTTP error",
                extra={
                    "method": method,
                    "url": url,
                    "status": response.status_code,
                    "body": snippet,
                },
            )
            raise HTTPError(msg, response=response)

        if not response.content:
            return None

        return response.json()

    def _is_dataset_full_error(self, exc: HTTPError) -> bool:
        resp = getattr(exc, "response", None)
        if resp is None:
            return False
        if resp.status_code != 400:
            return False
        text = (resp.text or "").strip()
        return _MAX_ELEMENTS_MSG in text

    def _free_some_slots(self, max_delete: int = 15) -> None:
        try:
            users = self.list_users()
        except Exception as e:
            logger.warning("Could not list users for cleanup: %s", e)
            return

        if not users:
            logger.warning("No users returned from list_users; cannot free slots.")
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
                self.delete_user(uid)
                deleted += 1
            except Exception as e:
                logger.warning("Cleanup delete failed for id=%s: %s", uid, e)

        logger.warning("Cleanup completed. Deleted=%s/%s", deleted, len(to_delete))

    @retry_on_failure()
    def create_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        normalized = self._normalize_user_payload(user_data)

        try:
            res = self._request("POST", json=normalized)
        except HTTPError as e:
            if self._is_dataset_full_error(e):
                self._free_some_slots()
                res = self._request("POST", json=normalized)
            else:
                raise

        # POST must return a JSON object
        assert res is not None and isinstance(res, dict)
        return cast(Dict[str, Any], res)

    @retry_on_failure()
    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        res = self._request("GET", endpoint=user_id)
        if res is None:
            return None
        assert isinstance(res, dict)
        return cast(Dict[str, Any], res)

    @retry_on_failure()
    def patch_user(self, user_id: str, partial_data: Dict[str, Any]) -> Dict[str, Any]:
        normalized = self._normalize_user_payload(partial_data)
        res = self._request("PATCH", endpoint=user_id, json=normalized)
        assert res is not None and isinstance(res, dict)
        return cast(Dict[str, Any], res)

    @retry_on_failure()
    def delete_user(self, user_id: str) -> bool:
        self._request("DELETE", endpoint=user_id)
        return True

    @retry_on_failure()
    def list_users(self) -> List[Dict[str, Any]]:
        res = self._request("GET")
        if res is None:
            return []
        assert isinstance(res, list)
        return cast(List[Dict[str, Any]], res)

    def get_user_status(self, user_id: str) -> int:
        url = f"{self.base_url}/{user_id}"
        response = self.session.get(url, timeout=self.timeout)
        return response.status_code

    def wait_until_deleted(
        self, user_id: str, retries: int = 5, delay: int = 1
    ) -> bool:
        for attempt in range(1, retries + 1):
            status = self.get_user_status(user_id)
            if status == 404:
                return True
            logger.debug(
                f"Waiting for deletion of user {user_id} (attempt {attempt}/{retries})"
            )
            sleep(delay)
        return False
