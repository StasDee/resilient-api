[![quality](https://github.com/StasDee/resilient-api/actions/workflows/quality.yml/badge.svg)](https://github.com/StasDee/resilient-api/actions/workflows/quality.yml)

# ResilientAPI

A small Python/pytest project that demonstrates **resilient API testing patterns** and a **tiered CI strategy**:

- **Stable (always green)**: formatting/linting + deterministic tests that **do not** call a flaky external API.
- **External signal (scheduled)**: tests that call the real API but **exclude stress/concurrency**.
- **Concurrency / stress (manual)**: rate-limit prone tests that are intentionally non-deterministic.

This split keeps PR checks reliable while still providing real-world signal from end-to-end tests.

---

## Requirements

- Python **3.12**
- [`uv`](https://docs.astral.sh/uv/) for env + dependency management

---

## Install (uv)

```bash
uv sync --extra test
```

This installs the project and the test/tooling dependencies (pytest, ruff, mypy).

---

## Running tests

### Stable tests (no external API)

Runs tests that do **not** hit the real API (default for PR CI):

```bash
uv run pytest -m "not external"
```

### External tests (real API)

External tests require two environment variables:

- `BASE_URL`
- `API_TOKEN`

Recommended: create a `.env` file in the repo root (do **not** commit it):

```env
BASE_URL=https://example.com/api
API_TOKEN=your_token_here
```

Run one of:

```bash
# External signal tier (recommended; used by scheduled workflow)
uv run pytest -m "external and not concurrency"

# Full external suite (includes stress tests; may hit rate limits)
uv run pytest -m external
```

If `BASE_URL` / `API_TOKEN` are missing, external tests will be **skipped** (so stable CI stays green).

---

## Code quality

### Format

```bash
uv run ruff format .
```

### Lint

```bash
uv run ruff check .
```

### Type-check

```bash
uv run mypy .
```

> `mypy` is configured as **non-blocking** in CI (it won’t fail the `quality` workflow).

---

## Test markers & tiers

This repository uses pytest markers to separate test intent:

- `external`: hits the real external API (**excluded from stable tier**)
- `concurrency`: stress/rate-limit prone tests (excluded from scheduled external runs)
- `contract`: validates normalization/validation rules (stable)
- `scenario`, `edge`, `asyncio`: additional categorization

Common runs:

```bash
# stable tier
uv run pytest -m "not external"

# external signal tier (recommended for CI schedules)
uv run pytest -m "external and not concurrency"

# full external including stress
uv run pytest -m external

# concurrency only
uv run pytest -m concurrency

# contract only
uv run pytest -m contract
```

---

## CI workflows (GitHub Actions)

### 1) `quality` (always green)

- **Triggers:** `pull_request`, `push` to `main`
- **Runs:**
  - Ruff format + lint
  - (Optional) mypy (non-blocking)
  - Pytest **excluding external** tests: `pytest -m "not external"`

Badge at the top of this README reflects this workflow.

### 2) `external-integration` (allowed to fail)

- **Triggers:** `workflow_dispatch` (manual) and nightly schedule
- **Runs:**
  - **Scheduled:** `pytest -m "external and not concurrency"` (signal tests)
  - **Manual:** optional input to include `concurrency` tests
- **Allowed to fail:** yes — external APIs can be flaky by nature.

#### Secrets needed for external workflow

Set these repository secrets:

- `BASE_URL`
- `API_TOKEN`

---

## Project layout (high level)

- `mockapi_client/` — API client code (sync + async, config, logging)
- `core/` — normalization + validation logic (stable, deterministic)
- `tests/` — stable + external + concurrency tests

---

## Notes on stability

External APIs can fail for reasons unrelated to your code (timeouts, rate limits, transient 5xx, eventual consistency).
That’s why:
- external tests are isolated into a separate workflow and excluded from PR checks, and
- stress tests are marked `concurrency` and excluded from scheduled runs.

---

## License

MIT
