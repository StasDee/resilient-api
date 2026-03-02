from __future__ import annotations

import os

from dotenv import load_dotenv

# Load .env once at import time (safe for local dev and CI)
load_dotenv()

# Keep these as *str* (not Optional) for clean typing.
# Missing values become empty string; runtime code checks for emptiness where needed.
BASE_URL: str = os.getenv("BASE_URL", "").strip()
TOKEN: str = os.getenv("API_TOKEN", "").strip()

# Timeouts should be int; keep a sane default.
DEFAULT_TIMEOUT: int = int(os.getenv("DEFAULT_TIMEOUT", "10"))
