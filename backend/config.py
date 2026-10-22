"""Central configuration. All tunables live here; secrets come from the root .env."""
import os
import re
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent
ROOT_DIR = BACKEND_DIR.parent
load_dotenv(ROOT_DIR / ".env")

# --- secrets ---
# One or more keys (GEMINI_API_KEYS=k1,k2,...); calls move to the next key when one's daily quota is used up.
GEMINI_API_KEYS = [k.strip() for k in (os.getenv("GEMINI_API_KEYS") or os.getenv("GEMINI_API_KEY", "")).split(",")
                   if k.strip()]
GEMINI_API_KEY = GEMINI_API_KEYS[0] if GEMINI_API_KEYS else ""
# The dashboard shows the REST endpoint (".../rest/v1/"); the client wants just the project origin.
SUPABASE_URL = re.sub(r"(\.supabase\.co).*$", r"\1", os.getenv("SUPABASE_URL", "").strip())
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "").strip()
SUPABASE_DB_URL = os.getenv("SUPABASE_DB_URL", "").strip()

# --- models ---
EMBED_MODEL = os.getenv("EMBED_MODEL", "gemini-embedding-001")
EMBED_DIM = 768
# Free tier: 1,000 embedded texts/day per key, shared by indexing and live questions. Indexing
# leaves the last 250 of the combined daily quota for questions.
INDEX_DAILY_EMBED_BUDGET = max(0, 1000 * len(GEMINI_API_KEYS) - 250)
# Free tier = 20 requests/day per model, so calls rotate through pools; a model that is out of
# quota is skipped until its quota resets. gemini-2.5-* is closed to new API keys.
# The gate is a simple classification, so it uses the lite models first and saves the stronger ones for the agent.
# Ordered by measured latency (fastest first); flash-latest took 50s on one evaluation step.
_STRONG = ["gemini-3.5-flash", "gemini-3-flash-preview", "gemini-3.6-flash", "gemini-3.8-flash",
           "gemini-3.7-flash", "gemini-flash-latest"]
_LITE = ["gemini-3.5-flash-lite", "gemini-flash-lite-latest", "gemini-3.1-flash-lite", "gemini-3.1-flash-lite-preview"]
AGENT_MODELS = [m.strip() for m in os.getenv("AGENT_MODELS", ",".join(_STRONG + _LITE)).split(",") if m.strip()]
# Measured 22/10: the lite models were overloaded (503/504 after ~20s) while the strong ones answered
# in under a second, so the gate tries the two fastest strong models first.
GATE_MODELS = [m.strip() for m in os.getenv("GATE_MODELS", ",".join(_STRONG[:2] + _LITE + _STRONG[2:])).split(",")
               if m.strip()]

# --- paths ---
DATA_DIR = BACKEND_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PDF_DIR = DATA_DIR / "pdf"
URLS_FILE = DATA_DIR / "urls.json"
CHUNKS_FILE = DATA_DIR / "chunks.jsonl"
CHROMA_DIR = DATA_DIR / "chroma"
BM25_FILE = DATA_DIR / "bm25.pkl"
EMBED_CACHE_DIR = DATA_DIR / "embed_cache"
ERRORS_LOG = DATA_DIR / "errors.log"
NOT_FOUND_FILE = DATA_DIR / "not_found.json"
QUOTA_STATE_FILE = DATA_DIR / "quota_state.json"

# --- crawling ---
SITE_ROOT = "https://www.fnx.co.il"
SITEMAP_URL = f"{SITE_ROOT}/sitemap.xml"
ROBOTS_URL = f"{SITE_ROOT}/robots.txt"
CRAWL_CONCURRENCY = 2
CRAWL_DELAY_SEC = 1.5
BLOCK_BACKOFF_SEC = 20
MAX_PDFS = 80
MAX_PDF_PAGES = 40       # long policy documents: coverage and claim terms come first

# --- retrieval / agent ---
TOP_K_EACH = 20          # candidates from vector and from BM25
TOP_K_FINAL = 8          # after RRF fusion
MIN_COSINE_SIM = 0.62    # absolute relevance floor; probe (1.8k chunks): off-topic <= 0.59, in-scope >= 0.71
# Fallback when the query cannot be embedded (daily quota): share of the query's words the best
# BM25 chunk must contain.
MIN_LEXICAL_COVERAGE = 0.6
AGENT_MAX_STEPS = 3
HISTORY_TURNS = 6

CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if o.strip()]
