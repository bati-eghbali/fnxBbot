"""Stage 2 checkpoint: eyeball retrieval quality and calibrate the similarity floor.

Run from backend/:  python -m ingest.probe ["optional custom query" ...]
"""
import sys

from app.retrieval import search

IN_SCOPE = [
    "יש לי נזילה בבית, איך מגישים תביעה?",
    "תוך כמה זמן מטפלים בתביעה?",
    "איך מגישים תביעה על נזקי מים בביטוח דירה",
    "מה עושים אחרי תאונת דרכים",
    "תביעת צד ג' רכב",
    "ביטוח נסיעות לחו\"ל הטסה רפואית",
    "איך מבטלים ביטוח נסיעות",
    "תביעת מחלות קשות אילו מסמכים צריך",
    "קרן השתלמות הפקדה עצמאית",
    "חיסכון לכל ילד מענק",
    "איך יוצרים קשר עם שירות הלקוחות",
    "העתק פוליסה ביטוח דירה",
    "טיפול שיניים בחו\"ל",
    "משיכת כספים מפנסיה לאחר פטירה",
    "אפליקציית הפניקס",
]
OUT_OF_SCOPE = [
    "מה בירת צרפת?",
    "תכתוב לי שיר על הים",
    "מי ניצח במונדיאל 2022",
    "איך מכינים פסטה ברוטב עגבניות",
    "כמה עולה ביטוח רכב בהראל",
]


def show(query: str, n: int = 5) -> float:
    res = search(query, min_similarity=0.0)
    print(f"\n### {query}   (best cosine {res.best_similarity:.3f})")
    for c in res.chunks[:n]:
        print(f"  {c.similarity:.3f}  {c.title[:45]:45}  {c.section[:40]:40}  {c.url[-55:]}")
    return res.best_similarity


def main() -> None:
    if len(sys.argv) > 1:
        for q in sys.argv[1:]:
            show(q)
        return
    ins = [show(q) for q in IN_SCOPE]
    outs = [show(q) for q in OUT_OF_SCOPE]
    print("\n=== similarity calibration ===")
    print(f"in-scope best cosine:     min {min(ins):.3f}  median {sorted(ins)[len(ins) // 2]:.3f}")
    print(f"out-of-scope best cosine: max {max(outs):.3f}")
    print("choose MIN_COSINE_SIM between those values (config.py)")


if __name__ == "__main__":
    main()
