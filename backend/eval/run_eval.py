"""Stage 6: run the evaluation set through the full pipeline and score it.

Run from backend/:  python -m eval.run_eval [--only id1,id2]
Writes eval/results.md (table for the submission) and eval/results.jsonl (full traces).
"""
import argparse
import json
import sys
import time
from pathlib import Path

from app.agent import answer_question
from app.prompts import CONTACT_URL
from app.retrieval import _collection

HERE = Path(__file__).parent
PAUSE_SEC = 4  # stay under per-minute limits of the free tier

# What counts as correct behaviour for each question type.
REFUSAL = {"not_found", "refer", "off_topic"}
EXPECTED_STATUS = {
    "not_on_site": REFUSAL,
    "off_topic": {"off_topic"},
    "advice": {"advice", "off_topic", "refer"},
    "personal": {"personal", "refer"},
}


def indexed_urls() -> set[str]:
    metas = _collection().get(include=["metadatas"])["metadatas"]
    return {m["url"] for m in metas} | {CONTACT_URL}


def score(turn: dict, reply) -> tuple[bool, str]:
    kind = turn["type"]
    urls = [s["url"] for s in reply.sources]
    if kind == "site":
        if reply.status != "answered":
            return False, f"status {reply.status}"
        hit = any(exp in u for u in urls for exp in turn["urls"])
        return hit, "correct source" if hit else f"other source: {urls}"
    if kind == "site_or_refuse":
        # The site has related but not exact information: a grounded answer from the expected pages,
        # or an honest refusal, are both correct. An answer citing anything else is not.
        if reply.status in REFUSAL | {"advice", "personal"}:
            return True, f"refused ({reply.status})"
        hit = reply.status == "answered" and any(exp in u for u in urls for exp in turn["urls"])
        return hit, "grounded answer" if hit else f"status {reply.status}, sources {urls}"
    if kind == "mixed":
        leaked = [w for w in turn["forbidden"] if w in reply.answer]
        return not leaked, f"leaked general knowledge: {leaked}" if leaked else f"no leak ({reply.status})"
    ok = reply.status in EXPECTED_STATUS[kind]
    return ok, reply.status


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="", help="comma-separated conversation ids")
    args = ap.parse_args()
    only = {x for x in args.only.split(",") if x}

    convs = [json.loads(line) for line in (HERE / "questions.jsonl").read_text(encoding="utf-8").splitlines() if line]
    if only:
        convs = [c for c in convs if c["id"] in only]
    known = indexed_urls()
    rows, records = [], []

    for conv in convs:
        history: list[dict] = []
        for i, turn in enumerate(conv["turns"], start=1):
            started = time.perf_counter()
            reply = answer_question(turn["q"], history)
            seconds = time.perf_counter() - started
            ok, note = score(turn, reply)
            fabricated = [s["url"] for s in reply.sources if s["url"] not in known]
            rows.append({"id": f"{conv['id']}#{i}", "type": turn["type"], "q": turn["q"], "ok": ok, "note": note,
                         "status": reply.status, "fabricated": fabricated, "seconds": round(seconds, 1)})
            records.append({**rows[-1], "answer": reply.answer, "sources": reply.sources, "trace": reply.trace})
            print(f"{'✅' if ok else '❌'} {rows[-1]['id']:24} [{reply.status:9}] {seconds:4.1f}s  {turn['q'][:50]}"
                  + (f"   ⚠ {note}" if not ok else ""), flush=True)
            history += [{"role": "user", "content": turn["q"]}, {"role": "assistant", "content": reply.answer}]
            time.sleep(PAUSE_SEC)

    report(rows)
    with (HERE / "results.jsonl").open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def report(rows: list[dict]) -> None:
    def pct(xs):
        return f"{sum(r['ok'] for r in xs)}/{len(xs)} ({100 * sum(r['ok'] for r in xs) / max(len(xs), 1):.0f}%)"

    site = [r for r in rows if r["type"] == "site"]
    refuse = [r for r in rows if r["type"] in ("not_on_site", "off_topic", "advice", "personal", "mixed",
                                               "site_or_refuse")]
    errors = [r for r in rows if r["status"] == "error"]
    fabricated = sum(len(r["fabricated"]) for r in rows)
    secs = sorted(r["seconds"] for r in rows)
    summary = [
        f"- **Correct answer with the right source:** {pct(site)}",
        f"- **Correct refusal / referral / no invention (not on site, partial info, traps, personal, advice):** "
        f"{pct(refuse)}",
        f"- **Fabricated source URLs:** {fabricated}",
        f"- **Errors (quota / outage):** {len(errors)}",
        f"- **Median response time:** {secs[len(secs) // 2]:.1f}s",
    ]
    lines = ["# Evaluation results", "", *summary, "",
             "| # | Type | Question | Result | Status | Note | Time |", "|---|---|---|---|---|---|---|"]
    for r in rows:
        lines.append(f"| {r['id']} | {r['type']} | {r['q']} | {'✅' if r['ok'] else '❌'} | {r['status']} "
                     f"| {r['note'] if not r['ok'] else ''} | {r['seconds']}s |")
    (HERE / "results.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n" + "\n".join(summary))
    print(f"wrote {HERE / 'results.md'}")


if __name__ == "__main__":
    main()
