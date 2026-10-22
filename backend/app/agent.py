"""The restrained agent: at most AGENT_MAX_STEPS model calls, every step is a tool call.

Defense layers enforced in code here:
  3. Search is mandatory - the code itself runs the step-1 search, and an answer without a search is rejected.
  4. Citations are verified - only chunk ids that tools actually returned count, and source URLs are
     built from chunk metadata, never from model text.
"""
import json
import time
from dataclasses import dataclass, field

from google.genai import types

import config
from app import prompts
from app.gate import Intent, run_gate
from app.llm import AllModelsUnavailable, base_config, generate
from app.tools import DECLARATIONS, ToolState, get_full_page, search_knowledge_base

TOOLS = [types.Tool(function_declarations=DECLARATIONS)]
LAST_STEP = ["final_answer", "refer_to_customer_service"]
ALL_TOOLS = [d.name for d in DECLARATIONS]
CONTACT_SOURCE = {"url": prompts.CONTACT_URL, "title": prompts.CONTACT_TITLE}


@dataclass
class BotReply:
    answer: str
    status: str                       # answered | not_found | refer | personal | advice | off_topic | greeting | error
    sources: list[dict] = field(default_factory=list)
    trace: list[dict] = field(default_factory=list)


def _forced(names: list[str]) -> types.ToolConfig:
    return types.ToolConfig(function_calling_config=types.FunctionCallingConfig(
        mode=types.FunctionCallingConfigMode.ANY, allowed_function_names=names))


def _sources(chunk_ids: list[str], state: ToolState) -> list[dict]:
    """Unique source pages for the cited chunks, in citation order."""
    seen, out = set(), []
    for cid in chunk_ids:
        c = state.retrieved[cid]
        if c.url not in seen:
            seen.add(c.url)
            out.append({"url": c.url, "title": c.title})
    return out


def run_agent(query: str, trace: list[dict]) -> BotReply:
    state = ToolState()
    # Step 1 is always a search, so the code runs it directly (saves a model call) - layer 3 by construction.
    started = time.perf_counter()
    first = search_knowledge_base(state, query)
    trace.append({"step": 1, "tool": "search_knowledge_base", "args": {"query": query}, "result": first["status"],
                  "mode": state.search_modes[-1],
                  "chunk_ids": [r["chunk_id"] for r in first.get("results", [])],
                  "ms": int((time.perf_counter() - started) * 1000)})
    if first["status"] == "not_found":  # layer 2 already decided: nothing relevant on the site
        return BotReply(prompts.NOT_FOUND, "not_found", [CONTACT_SOURCE], trace)
    # Gemini 3 rejects synthetic function-call turns (no thought signature), so the first
    # results go in as plain context.
    contents: list[types.Content] = [types.Content(role="user", parts=[types.Part(text=(
        f"שאלת הלקוח: {query}\n\n"
        f"תוצאות החיפוש הראשון (search_knowledge_base):\n{json.dumps(first, ensure_ascii=False)}"
    ))])]

    for step in range(2, config.AGENT_MAX_STEPS + 1):
        allowed = LAST_STEP if step == config.AGENT_MAX_STEPS else ALL_TOOLS
        cfg = base_config(prompts.AGENT_SYSTEM, tools=TOOLS, tool_config=_forced(allowed))
        started = time.perf_counter()
        res, model = generate(contents, cfg, config.AGENT_MODELS)
        calls = res.function_calls or []
        if not calls:
            trace.append({"step": step, "model": model, "error": "no tool call"})
            break
        call = calls[0]  # one action per step keeps the loop bounded and auditable
        args = dict(call.args or {})
        entry = {"step": step, "tool": call.name, "model": model, "args": args,
                 "ms": int((time.perf_counter() - started) * 1000)}
        trace.append(entry)

        if call.name == "final_answer":
            return _finalize(args, state, entry)
        if call.name == "refer_to_customer_service":
            return BotReply(prompts.REFER, "refer", [CONTACT_SOURCE], trace)

        if call.name == "search_knowledge_base":
            result = search_knowledge_base(state, str(args.get("query", query)))
        else:
            result = get_full_page(state, str(args.get("url", "")))
        entry["result"] = result.get("status")
        entry["chunk_ids"] = [r["chunk_id"] for r in result.get("results", [])]

        contents.append(res.candidates[0].content)
        contents.append(types.Content(role="user", parts=[
            types.Part.from_function_response(name=call.name, response=result)]))

    return BotReply(prompts.NOT_FOUND, "not_found", [CONTACT_SOURCE], trace)


def _finalize(args: dict, state: ToolState, entry: dict) -> BotReply:
    trace_ref = entry  # annotate the final step with the verification outcome
    if not state.searched:                                      # layer 3
        trace_ref["rejected"] = "answer without search"
        return BotReply(prompts.NOT_FOUND, "not_found", [CONTACT_SOURCE])
    cited = [cid for cid in args.get("used_chunk_ids") or [] if cid in state.retrieved]   # layer 4
    trace_ref["verified_chunk_ids"] = cited
    answer = str(args.get("answer", "")).strip()
    if not args.get("found") or not cited or not answer:
        trace_ref["rejected"] = "not found or no verified citation"
        return BotReply(prompts.NOT_FOUND, "not_found", [CONTACT_SOURCE])
    return BotReply(answer, "answered", _sources(cited, state))


def answer_question(message: str, history: list[dict]) -> BotReply:
    """Full pipeline for one user message. history: recent turns, oldest first."""
    trace: list[dict] = []
    try:
        started = time.perf_counter()
        gate, gate_model = run_gate(message, history[-config.HISTORY_TURNS:])
        trace.append({"step": 0, "tool": "gate", "model": gate_model, "intent": gate.intent.value,
                      "standalone_query": gate.standalone_query, "ms": int((time.perf_counter() - started) * 1000)})

        if gate.intent == Intent.off_topic:
            return BotReply(prompts.OFF_TOPIC, "off_topic", [], trace)
        if gate.intent == Intent.greeting:
            return BotReply(prompts.GREETING, "greeting", [], trace)
        if gate.intent == Intent.advice:
            return BotReply(prompts.ADVICE, "advice", [CONTACT_SOURCE], trace)

        reply = run_agent(gate.standalone_query, trace)
        reply.trace = trace
        if gate.intent == Intent.personal_policy:
            if reply.status == "answered":
                reply.answer = f"{reply.answer}\n\n{prompts.PERSONAL_NOTE}"
                reply.sources.append(CONTACT_SOURCE)
            else:
                reply.answer = prompts.PERSONAL_ONLY
            reply.status = "personal"
        return reply
    except AllModelsUnavailable as e:
        trace.append({"error": str(e)})
        return BotReply(prompts.BUSY, "error", [CONTACT_SOURCE], trace)
    except Exception as e:  # noqa: BLE001 - never surface a stack trace to the customer
        trace.append({"error": repr(e)})
        return BotReply(prompts.ERROR, "error", [], trace)
