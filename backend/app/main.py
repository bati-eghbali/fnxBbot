"""FastAPI backend.

Run from backend/:  uvicorn app.main:app --reload --port 8000
"""
from fastapi import FastAPI, HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

import config
from app import history
from app.agent import answer_question

app = FastAPI(title="Phoenix Site Bot")
app.add_middleware(CORSMiddleware, allow_origins=config.CORS_ORIGINS, allow_methods=["*"], allow_headers=["*"])


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)
    conversation_id: str | None = None


class Source(BaseModel):
    url: str
    title: str


class ChatResponse(BaseModel):
    conversation_id: str
    answer: str
    status: str
    sources: list[Source]


@app.get("/health")
def health() -> dict:
    return {"ok": True}


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    message = req.message.strip()
    if req.conversation_id and not await run_in_threadpool(history.conversation_exists, req.conversation_id):
        raise HTTPException(404, "conversation not found")
    conv_id = req.conversation_id or await run_in_threadpool(history.create_conversation, message)

    past = await run_in_threadpool(history.recent_turns, conv_id)
    reply = await run_in_threadpool(answer_question, message, past)

    await run_in_threadpool(history.add_message, conv_id, "user", message)
    await run_in_threadpool(lambda: history.add_message(
        conv_id, "assistant", reply.answer, status=reply.status, sources=reply.sources, trace=reply.trace))
    return ChatResponse(conversation_id=conv_id, answer=reply.answer, status=reply.status,
                        sources=[Source(**s) for s in reply.sources])


@app.get("/conversations")
async def conversations() -> list[dict]:
    return await run_in_threadpool(history.list_conversations)


@app.get("/conversations/{conversation_id}")
async def conversation(conversation_id: str) -> list[dict]:
    return await run_in_threadpool(history.get_messages, conversation_id)


@app.delete("/conversations/{conversation_id}")
async def delete(conversation_id: str) -> dict:
    await run_in_threadpool(history.delete_conversation, conversation_id)
    return {"ok": True}
