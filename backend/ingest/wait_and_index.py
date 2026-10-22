"""Wait until the free daily embedding quota resets, then continue building the index.

Run from backend/:  python -m ingest.wait_and_index
Probes with a single cached-free query every 15 minutes (a failed probe costs no quota).
"""
import time
from datetime import datetime

from ingest import index
from ingest.embed import DailyQuotaExhausted, _embed_batch

PROBE_EVERY_SEC = 15 * 60


def quota_available() -> bool:
    try:
        _embed_batch(["בדיקה"], "RETRIEVAL_QUERY")
        return True
    except DailyQuotaExhausted:
        return False


if __name__ == "__main__":
    while not quota_available():
        print(f"{datetime.now():%H:%M} quota still exhausted, next check in 15 min", flush=True)
        time.sleep(PROBE_EVERY_SEC)
    print(f"{datetime.now():%H:%M} quota available - indexing", flush=True)
    index.main()
