"""Gemini embeddings with batching, retry/backoff and an on-disk cache keyed by content hash.

The free tier allows 1,000 embedded texts per day per key, so indexing may span several days or
keys: embed_documents moves to the next key when one is used up, and stops cleanly when all are.
"""
import hashlib
import json
import time

from google import genai
from google.genai import errors, types

import config
from app import quota

# Free tier limits tokens per minute; ~20 chunks (~10k tokens) per call with a short pause stays under it.
BATCH_SIZE = 20
PAUSE_SEC = 4
CACHE_FILE = config.EMBED_CACHE_DIR / f"{config.EMBED_MODEL}-{config.EMBED_DIM}.jsonl"
QUERY_CACHE_FILE = config.EMBED_CACHE_DIR / f"{config.EMBED_MODEL}-{config.EMBED_DIM}-queries.jsonl"

_query_cache: dict[str, list[float]] | None = None


class DailyQuotaExhausted(RuntimeError):
    """Every configured key has used up today's embedding quota."""


def client() -> genai.Client:
    return quota.client_for(0)


def _embed_with_key(key_index: int, texts: list[str], task_type: str) -> list[list[float]]:
    delay = 10.0
    for attempt in range(8):
        try:
            res = quota.client_for(key_index).models.embed_content(
                model=config.EMBED_MODEL,
                contents=texts,
                config=types.EmbedContentConfig(task_type=task_type, output_dimensionality=config.EMBED_DIM),
            )
            return [e.values for e in res.embeddings]
        except errors.APIError as e:
            if quota.is_daily_quota_error(e):
                raise
            # 429 = per-minute rate limit, 5xx = transient; anything else is a real error.
            if e.code != 429 and (e.code or 0) < 500 or attempt == 7:
                raise
            print(f"    Gemini {e.code}, retrying in {delay:.0f}s", flush=True)
            time.sleep(delay)
            delay = min(delay * 2, 120)
    raise RuntimeError("unreachable")


def _embed_batch(texts: list[str], task_type: str) -> list[list[float]]:
    """Embed with the first key that still has quota today (all keys produce compatible vectors)."""
    for key_index, _ in quota.available_slots([config.EMBED_MODEL]):
        try:
            return _embed_with_key(key_index, texts, task_type)
        except errors.APIError as e:
            quota.mark_exhausted(key_index, config.EMBED_MODEL, e)
            print(f"    key{key_index}: daily embedding quota used up", flush=True)
    raise DailyQuotaExhausted("all keys used today's embedding quota")


def _load_cache(path) -> dict[str, list[float]]:
    if not path.exists():
        return {}
    cache = {}
    with path.open(encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            cache[row["h"]] = row["v"]
    return cache


def _hash(text: str) -> str:
    return hashlib.sha1(text.encode()).hexdigest()


def embed_documents(texts: list[str], budget: int | None = None) -> list[list[float] | None]:
    """Embed chunk texts in the given order (callers pass the most important first), reusing cached
    vectors. At most `budget` new texts are embedded; if the budget or the daily quota runs out,
    the remaining entries are None."""
    config.EMBED_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache = _load_cache(CACHE_FILE)
    hashes = [_hash(t) for t in texts]
    missing = list({h: t for h, t in zip(hashes, texts) if h not in cache}.items())  # keeps priority order
    print(f"embeddings: {len(texts) - len(missing)} cached, {len(missing)} to compute"
          + (f" (today's budget: {budget})" if budget is not None else ""), flush=True)
    if budget is not None:
        missing = missing[:budget]
    try:
        with CACHE_FILE.open("a", encoding="utf-8") as f:
            for i in range(0, len(missing), BATCH_SIZE):
                batch = missing[i:i + BATCH_SIZE]
                vectors = _embed_batch([t for _, t in batch], "RETRIEVAL_DOCUMENT")
                for (h, _), v in zip(batch, vectors):
                    cache[h] = v
                    f.write(json.dumps({"h": h, "v": v}) + "\n")
                f.flush()
                print(f"  {min(i + BATCH_SIZE, len(missing))}/{len(missing)}", flush=True)
                time.sleep(PAUSE_SEC)
    except DailyQuotaExhausted:
        done = sum(h in cache for h in hashes)
        print(f"daily embedding quota reached: {done}/{len(texts)} chunks embedded; rerun tomorrow to continue",
              flush=True)
    return [cache.get(h) for h in hashes]


def embed_query(text: str) -> list[float]:
    """Query embedding with a persistent cache, so repeated questions (evaluation, demo) cost no quota."""
    global _query_cache
    if _query_cache is None:
        _query_cache = _load_cache(QUERY_CACHE_FILE)
    key = _hash(text)
    if key not in _query_cache:
        vec = _embed_batch([text], "RETRIEVAL_QUERY")[0]
        _query_cache[key] = vec
        config.EMBED_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        with QUERY_CACHE_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"h": key, "v": vec}) + "\n")
    return _query_cache[key]
