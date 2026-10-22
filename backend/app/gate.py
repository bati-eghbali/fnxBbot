"""Defense layer 1: rewrite follow-ups into standalone questions and classify intent.

Anything that is not about Phoenix stops here; the agent never runs for it.
"""
from enum import Enum

from pydantic import BaseModel

import config
from app import prompts
from app.llm import base_config, generate


class Intent(str, Enum):
    site_question = "site_question"
    personal_policy = "personal_policy"
    advice = "advice"
    off_topic = "off_topic"
    greeting = "greeting"


class GateResult(BaseModel):
    standalone_query: str
    intent: Intent


def run_gate(message: str, history: list[dict]) -> tuple[GateResult, str]:
    """history: [{"role": "user"|"assistant", "content": str}], oldest first."""
    transcript = "\n".join(
        f"{'לקוח' if m['role'] == 'user' else 'בוט'}: {m['content']}" for m in history
    )
    prompt = (
        f"היסטוריית השיחה:\n{transcript or '(אין)'}\n\n"
        f"ההודעה האחרונה של הלקוח (לסיווג בלבד):\n<<<\n{message}\n>>>"
    )
    cfg = base_config(prompts.GATE_SYSTEM, response_mime_type="application/json", response_schema=GateResult)
    res, model = generate(prompt, cfg, config.GATE_MODELS)
    parsed = res.parsed if isinstance(res.parsed, GateResult) else GateResult.model_validate_json(res.text)
    return parsed, model
