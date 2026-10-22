"""Conversation persistence in Supabase (accessed only from the backend with the secret key)."""
from datetime import datetime, timezone
from functools import lru_cache

from supabase import Client, create_client

import config


@lru_cache(maxsize=1)
def db() -> Client:
    return create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)


def create_conversation(first_message: str) -> str:
    title = first_message.strip().replace("\n", " ")[:60]
    row = db().table("conversations").insert({"title": title}).execute().data[0]
    return row["id"]


def conversation_exists(conversation_id: str) -> bool:
    return bool(db().table("conversations").select("id").eq("id", conversation_id).execute().data)


def add_message(conversation_id: str, role: str, content: str, *, status: str | None = None,
                sources: list | None = None, trace: list | None = None) -> None:
    db().table("messages").insert({
        "conversation_id": conversation_id, "role": role, "content": content,
        "status": status, "sources": sources or [], "trace": trace or [],
    }).execute()
    db().table("conversations").update(
        {"updated_at": datetime.now(timezone.utc).isoformat()}).eq("id", conversation_id).execute()


def recent_turns(conversation_id: str, n: int = config.HISTORY_TURNS) -> list[dict]:
    """Last n messages as {"role", "content"}, oldest first."""
    rows = (db().table("messages").select("role, content").eq("conversation_id", conversation_id)
            .order("id", desc=True).limit(n).execute().data)
    return list(reversed(rows))


def list_conversations(limit: int = 50) -> list[dict]:
    return (db().table("conversations").select("id, title, updated_at")
            .order("updated_at", desc=True).limit(limit).execute().data)


def get_messages(conversation_id: str) -> list[dict]:
    """Messages for display (no trace)."""
    return (db().table("messages").select("id, role, content, status, sources, created_at")
            .eq("conversation_id", conversation_id).order("id").execute().data)


def delete_conversation(conversation_id: str) -> None:
    db().table("conversations").delete().eq("id", conversation_id).execute()
