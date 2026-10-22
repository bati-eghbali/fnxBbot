"""Gemini generate call that rotates through free-tier (key, model) slots.

Free tier allows ~20 requests/day per model per key. A slot whose daily quota is exhausted is
skipped until Google's reset time; overloaded (503) models are skipped for this call only.
"""
import time

import httpx
from google.genai import errors, types

from app import quota


class AllModelsUnavailable(RuntimeError):
    pass


def _for_model(model: str, cfg: types.GenerateContentConfig) -> types.GenerateContentConfig:
    # Lite models reject an explicit thinking budget; the others answer faster with thinking off.
    thinking = None if "lite" in model else types.ThinkingConfig(thinking_budget=0)
    return cfg.model_copy(update={"thinking_config": thinking})


TOTAL_BUDGET_SEC = 40  # a customer should not wait longer than this for one model call
COOLDOWN_SEC = 300     # an overloaded or hanging slot is skipped for a while instead of retried every call

_cooling: dict[tuple[int, str], float] = {}  # in-memory: overload is short-lived, unlike daily quota


def _cool(key_index: int, model: str) -> None:
    _cooling[(key_index, model)] = time.monotonic() + COOLDOWN_SEC


def generate(contents, cfg: types.GenerateContentConfig, pool: list[str]):
    """Returns (response, "model" or "model@keyN")."""
    errors_seen = []
    deadline = time.monotonic() + TOTAL_BUDGET_SEC
    now = time.monotonic()
    slots = quota.available_slots(pool)
    # Cooling slots go last rather than being dropped: better a slow answer than none.
    slots.sort(key=lambda s: _cooling.get(s, 0) > now)
    for key_index, model in slots:
        if time.monotonic() > deadline:
            errors_seen.append("time budget exceeded")
            break
        label = model if key_index == 0 else f"{model}@key{key_index}"
        for attempt in range(2):
            try:
                res = quota.client_for(key_index).models.generate_content(
                    model=model, contents=contents, config=_for_model(model, cfg))
                return res, label
            except errors.APIError as e:
                errors_seen.append(f"{label}: {e.code}")
                if quota.is_daily_quota_error(e):
                    quota.mark_exhausted(key_index, model, e)
                    break
                if e.code == 429 and attempt == 0:      # per-minute limit: brief pause, same slot
                    time.sleep(3)
                    continue
                if e.code == 429 or (e.code or 0) >= 500:  # overloaded: try the next slot
                    _cool(key_index, model)
                    break
                raise
            except httpx.TransportError as e:  # dropped connection or timeout: try the next slot
                errors_seen.append(f"{label}: {type(e).__name__}")
                _cool(key_index, model)
                break
    raise AllModelsUnavailable("; ".join(errors_seen[-6:]) or "all models out of daily quota")


def base_config(system: str, **kwargs) -> types.GenerateContentConfig:
    return types.GenerateContentConfig(system_instruction=system, temperature=0.0, **kwargs)
