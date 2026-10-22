"""Terminal chat for testing the pipeline without the API or UI.

Run from backend/:
    python -m app.cli                         # interactive
    python -m app.cli "שאלה 1" "שאלה 2" ...   # scripted conversation
"""
import json
import sys

from app.agent import answer_question


def turn(message: str, history: list[dict], show_trace: bool = True) -> None:
    reply = answer_question(message, history)
    print(f"\n👤 {message}\n🤖 [{reply.status}] {reply.answer}")
    for s in reply.sources:
        print(f"   🔗 {s['title']} — {s['url']}")
    if show_trace:
        for t in reply.trace:
            print("   ·", json.dumps({k: v for k, v in t.items() if k != "args" or t.get("tool") != "final_answer"},
                                    ensure_ascii=False)[:300])
    history += [{"role": "user", "content": message}, {"role": "assistant", "content": reply.answer}]


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    history: list[dict] = []
    if len(sys.argv) > 1:
        for msg in sys.argv[1:]:
            turn(msg, history)
        return
    while True:
        try:
            msg = input("\nשאלה> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if msg:
            turn(msg, history)


if __name__ == "__main__":
    main()
