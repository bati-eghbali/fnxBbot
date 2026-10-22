"""Create the Supabase tables (safe to run repeatedly).

Run from backend/:  python apply_schema.py
"""
import psycopg

import config

SCHEMA = config.ROOT_DIR / "supabase" / "schema.sql"

if __name__ == "__main__":
    with psycopg.connect(config.SUPABASE_DB_URL) as conn:
        conn.execute(SCHEMA.read_text(encoding="utf-8"))
        tables = conn.execute(
            "select table_name from information_schema.tables "
            "where table_schema = 'public' and table_name in ('conversations', 'messages')"
        ).fetchall()
    print("tables ready:", sorted(t[0] for t in tables))
