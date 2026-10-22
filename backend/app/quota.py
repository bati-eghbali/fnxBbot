"""Shared bookkeeping of free-tier daily quotas, per (API key, model).

A quota that Google reports as exhausted is skipped until the reset time Google gives (retryDelay).
Keys are identified by their position in GEMINI_API_KEYS, so no secret is written to disk.
"""
import json
import re
import time
from functools import lru_cache

from google import genai
from google.genai import errors, types

import config

RETRY_DELAY_RE = re.compile(r"retryDelay': '(\d+)s'")
# Healthy calls take 1-3s; overloaded free-tier models hang for 20s+ before a 503/504, so fail fast
# and move to the next slot.
REQUEST_TIMEOUT_MS = 12_000


@lru_cache(maxsize=None)
def client_for(key_index: int) -> genai.Client:
    # The SDK's own retry loop backs off on 429/503 for minutes; rotation to another slot is faster,
    # so SDK retries are disabled and the callers handle errors.
    return genai.Client(api_key=config.GEMINI_API_KEYS[key_index], http_options=types.HttpOptions(
        timeout=REQUEST_TIMEOUT_MS, retry_options=types.HttpRetryOptions(attempts=1)))


def _slot(key_index: int, model: str) -> str:
    return f"key{key_index}:{model}"


def _load() -> dict[str, float]:
    try:
        state = json.loads(config.QUOTA_STATE_FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    now = time.time()
    return {slot: until for slot, until in state.items() if until > now}


def is_exhausted(key_index: int, model: str) -> bool:
    return _slot(key_index, model) in _load()


def mark_exhausted(key_index: int, model: str, error: errors.APIError) -> None:
    m = RETRY_DELAY_RE.search(str(error))
    state = _load()
    state[_slot(key_index, model)] = time.time() + (int(m.group(1)) if m else 3600)
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    config.QUOTA_STATE_FILE.write_text(json.dumps(state, indent=1), encoding="utf-8")


def is_daily_quota_error(error: errors.APIError) -> bool:
    return error.code == 429 and "PerDay" in str(error)


def available_slots(models: list[str]) -> list[tuple[int, str]]:
    """(key_index, model) pairs not known to be exhausted, model-major: the pool's first (fastest)
    model on every key before falling back to slower models."""
    exhausted = _load()
    return [(k, m) for m in models for k in range(len(config.GEMINI_API_KEYS))
            if _slot(k, m) not in exhausted]
