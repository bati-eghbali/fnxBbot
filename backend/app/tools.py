"""The agent's tools. Every chunk a tool returns is recorded, so citations can be verified later."""
from dataclasses import dataclass, field

from google.genai import types

from app.retrieval import Chunk, page_chunks, search

MAX_PAGE_CHUNKS = 12

DECLARATIONS = [
    types.FunctionDeclaration(
        name="search_knowledge_base",
        description="חיפוש קטעים רלוונטיים בתוכן אתר הפניקס. מחזיר קטעים עם chunk_id, כותרת וטקסט.",
        parameters_json_schema={
            "type": "object",
            "properties": {"query": {"type": "string", "description": "שאילתת חיפוש בעברית"}},
            "required": ["query"],
        },
    ),
    types.FunctionDeclaration(
        name="get_full_page",
        description="מחזיר את כל הקטעים של עמוד שכבר הופיע בתוצאות החיפוש, כשקטע אחד לא מספיק.",
        parameters_json_schema={
            "type": "object",
            "properties": {"url": {"type": "string", "description": "כתובת עמוד מתוך תוצאות החיפוש"}},
            "required": ["url"],
        },
    ),
    types.FunctionDeclaration(
        name="refer_to_customer_service",
        description="מסיים בהפניה לשירות הלקוחות, כשהשאלה דורשת מידע אישי או טיפול במקרה ספציפי.",
        parameters_json_schema={
            "type": "object",
            "properties": {"reason": {"type": "string"}},
            "required": ["reason"],
        },
    ),
    types.FunctionDeclaration(
        name="final_answer",
        description="התשובה הסופית ללקוח. חובה לסיים בה.",
        parameters_json_schema={
            "type": "object",
            "properties": {
                "found": {"type": "boolean", "description": "האם התשובה כתובה במפורש בקטעים"},
                "answer": {"type": "string", "description": "תשובה בעברית, 2-4 משפטים"},
                "used_chunk_ids": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["found", "answer", "used_chunk_ids"],
        },
    ),
]


@dataclass
class ToolState:
    """What the agent has actually seen in this turn."""
    retrieved: dict[str, Chunk] = field(default_factory=dict)
    searched: bool = False
    search_modes: list[str] = field(default_factory=list)  # "hybrid" / "lexical", recorded in the trace


def _format(chunks: list[Chunk]) -> list[dict]:
    return [{"chunk_id": c.chunk_id, "url": c.url, "title": c.title, "text": c.text} for c in chunks]


def search_knowledge_base(state: ToolState, query: str) -> dict:
    state.searched = True
    res = search(query)
    state.search_modes.append(res.mode)
    if not res.found:
        return {"status": "not_found", "message": "לא נמצא באתר תוכן רלוונטי מספיק לשאילתה הזו."}
    for c in res.chunks:
        state.retrieved[c.chunk_id] = c
    return {"status": "ok", "results": _format(res.chunks)}


def get_full_page(state: ToolState, url: str) -> dict:
    if url not in {c.url for c in state.retrieved.values()}:
        return {"status": "error", "message": "אפשר להביא רק עמוד שהופיע בתוצאות החיפוש."}
    chunks = page_chunks(url)[:MAX_PAGE_CHUNKS]
    for c in chunks:
        state.retrieved[c.chunk_id] = c
    return {"status": "ok", "results": _format(chunks)}
