"""Stage 0 checkpoint: verify .env values and connectivity to Gemini and Supabase.

Run from backend/:  python check_setup.py
"""
import sys

import config

OK, FAIL = "[OK]  ", "[FAIL]"


def check_env() -> bool:
    missing = [name for name in ("GEMINI_API_KEY", "SUPABASE_URL", "SUPABASE_SERVICE_KEY", "SUPABASE_DB_URL")
               if not getattr(config, name)]
    if missing:
        print(f"{FAIL} missing in .env: {', '.join(missing)}")
        return False
    if "[YOUR-PASSWORD]" in config.SUPABASE_DB_URL:
        print(f"{FAIL} SUPABASE_DB_URL still contains [YOUR-PASSWORD] - replace it with the DB password")
        return False
    print(f"{OK} .env has all 4 values")
    return True


def check_gemini() -> bool:
    from google import genai
    from google.genai import types

    try:
        client = genai.Client(api_key=config.GEMINI_API_KEY)
        res = client.models.embed_content(
            model=config.EMBED_MODEL,
            contents=["בדיקה"],
            config=types.EmbedContentConfig(output_dimensionality=config.EMBED_DIM),
        )
        print(f"{OK} Gemini embeddings ({len(res.embeddings[0].values)} dims)")
        return True
    except Exception as e:  # noqa: BLE001 - report any failure to the user
        print(f"{FAIL} Gemini: {e}")
        return False


def check_supabase_db() -> bool:
    import psycopg

    try:
        with psycopg.connect(config.SUPABASE_DB_URL, connect_timeout=10) as conn:
            conn.execute("select 1")
        print(f"{OK} Supabase database connection")
        return True
    except Exception as e:  # noqa: BLE001
        print(f"{FAIL} Supabase DB: {e}")
        return False


def check_supabase_api() -> bool:
    from supabase import create_client

    try:
        create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)
        print(f"{OK} Supabase API client")
        return True
    except Exception as e:  # noqa: BLE001
        print(f"{FAIL} Supabase API: {e}")
        return False


if __name__ == "__main__":
    if not check_env():
        sys.exit(1)
    results = [check_gemini(), check_supabase_db(), check_supabase_api()]
    sys.exit(0 if all(results) else 1)
