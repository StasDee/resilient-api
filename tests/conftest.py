import asyncio
import os

import pytest
import pytest_asyncio

from mockapi_client.async_client import AsyncUsersApiClient
from mockapi_client.client import UsersApiClient
from mockapi_client.config import BASE_URL, TOKEN
from mockapi_client.factory import UserFactory
from mockapi_client.logger import get_logger

logger = get_logger(__name__)


# =========================================================
# Marking: treat any test that uses an API client fixture as "external"
# (so PR CI can safely exclude them with `-m "not external"`)
# =========================================================


@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(config, items):
    for item in items:
        if {"api_client", "async_api_client"} & set(getattr(item, "fixturenames", [])):
            item.add_marker(pytest.mark.external)


def _missing_external_env() -> list[str]:
    missing = []
    if not os.getenv("BASE_URL"):
        missing.append("BASE_URL")
    if not os.getenv("API_TOKEN"):
        missing.append("API_TOKEN")
    return missing


# =========================================================
# Clients
# =========================================================


@pytest.fixture(scope="session")
def api_client():
    missing = _missing_external_env()
    if missing:
        pytest.skip(
            "External API tests require env vars: "
            + ", ".join(missing)
            + " (set them to run -m external)"
        )

    with UsersApiClient() as client:
        yield client


@pytest_asyncio.fixture(scope="function")
async def async_api_client():
    missing = _missing_external_env()
    if missing:
        pytest.skip(
            "External API tests require env vars: "
            + ", ".join(missing)
            + " (set them to run -m external)"
        )

    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json",
    }
    async with AsyncUsersApiClient(base_url=BASE_URL, headers=headers) as client:
        yield client


# =========================================================
# Factory
# =========================================================


@pytest.fixture
def user_factory():
    factory = UserFactory()
    yield factory
    factory.reset()
    logger.debug("UserFactory memory cleared")


# =========================================================
# Cleanup Registry (safe for sync + async)
# =========================================================


@pytest.fixture(scope="function")
def cleanup_registry():
    """Separate registries prevent cross-execution bugs."""
    return {"sync": set(), "async": set()}


# =========================================================
# Registry helpers (used by tests)
# =========================================================


@pytest.fixture
def register_sync_user(cleanup_registry):
    def _register(user_id: str):
        cleanup_registry["sync"].add(user_id)

    return _register


@pytest_asyncio.fixture
async def register_async_user(cleanup_registry):
    async def _register(user_id: str):
        cleanup_registry["async"].add(user_id)

    return _register


# =========================================================
# The One True Janitor™
# =========================================================


@pytest.fixture(scope="function", autouse=True)
def final_cleanup(cleanup_registry):
    """
    Runs exactly once per test.
    Cleans up created users (best-effort).
    """
    yield

    # -------------------
    # Sync cleanup
    # -------------------
    if cleanup_registry["sync"]:
        logger.info("--- Sync Cleanup: %s users ---", len(cleanup_registry["sync"]))
        with UsersApiClient() as client:
            for user_id in cleanup_registry["sync"]:
                try:
                    client.delete_user(user_id)
                    logger.debug("Successfully deleted user with id: %s", user_id)
                except Exception as e:
                    logger.warning("Failed to delete %s: %s", user_id, e)

    # -------------------
    # Async cleanup
    # -------------------
    if cleanup_registry["async"]:

        async def _async_cleanup():
            async with AsyncUsersApiClient(
                base_url=BASE_URL,
                headers={"Authorization": f"Bearer {TOKEN}"},
            ) as client:
                for user_id in cleanup_registry["async"]:
                    logger.debug("Deleting async user: %s", user_id)
                    try:
                        await client.delete_user(user_id)
                        await client.wait_until_deleted(user_id)
                    except Exception as e:
                        logger.warning("Failed to delete async user %s: %s", user_id, e)

        try:
            asyncio.run(_async_cleanup())
        except RuntimeError as e:
            # If we're already inside an event loop (rare in teardown), don't hard-fail the test suite.
            logger.warning("Skipping async cleanup due to event loop state: %s", e)


@pytest.fixture(autouse=True)
def separator():
    print("\n")
    yield
