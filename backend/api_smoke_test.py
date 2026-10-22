"""Stage 4 checkpoint: a short conversation through the running API, then read it back.

Start the server first (uvicorn app.main:app --port 8000), then run:  python api_smoke_test.py
"""
import sys

import httpx

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
QUESTIONS = ["איך מגישים תביעה על נזק לרכב שלי בתאונה?", "ואיפה אני מוצא מוסך הסדר?"]


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    with httpx.Client(base_url=BASE, timeout=120) as http:
        print("health:", http.get("/health").json())
        conv_id = None
        for q in QUESTIONS:
            r = http.post("/chat", json={"message": q, "conversation_id": conv_id})
            r.raise_for_status()
            d = r.json()
            conv_id = d["conversation_id"]
            print(f"\n👤 {q}\n🤖 [{d['status']}] {d['answer']}")
            for s in d["sources"]:
                print(f"   🔗 {s['title']} — {s['url']}")
        print("\n--- stored in Supabase:")
        for m in http.get(f"/conversations/{conv_id}").json():
            print(f"  {m['role']:9} {m['status'] or '':10} {m['content'][:70]}")
        print("conversations listed:", len(http.get("/conversations").json()))


if __name__ == "__main__":
    main()
