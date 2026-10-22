"""Stage 2a: split crawled pages into retrieval chunks.

data/raw/*.json -> data/chunks.jsonl
Run from backend/:  python -m ingest.chunk
"""
import hashlib
import html
import json
import re
from collections import Counter
from urllib.parse import urlparse

import config

MAX_CHARS = 2400          # ~600 tokens of Hebrew
MIN_CHARS = 250           # smaller sections are merged into their neighbour
OVERLAP_CHARS = 200
BOILERPLATE_RATIO = 0.12  # a line on more than 12% of pages is site chrome, not content

HEADING_RE = re.compile(r"^(#{1,4})\s+(.*\S)\s*$")
PDF_PAGE_RE = re.compile(r"^עמוד \d+$")  # page markers added by crawler/pdfs.py
# Lone CTA / UI lines that carry no information on their own.
NOISE_LINE_RE = re.compile(
    r"^(\d{1,2}|להגשת תביעה|טופס תביעה|התחלת שיחה|הזמנת שיחה|מידע נוסף|לפרטים נוספים|קרא עוד|לחצו כאן|סגירה|\*|-)$"
)


def clean_title(title: str) -> str:
    return re.sub(r"\s*\|\s*הפניקס\s*$", "", title).strip()


# PDF metadata titles are often authoring leftovers ("Microsoft Word - 2007-1-08.doc", "dira hoveret").
JUNK_PDF_TITLE_RE = re.compile(r"Microsoft|\.docx?$|^[\x00-\x7F]*$")


def display_title(page: dict, title: str) -> str:
    """Title shown on source cards. Kept separate from the chunk text so fixing it needs no re-embedding."""
    if page["source_type"] == "pdf" and JUNK_PDF_TITLE_RE.search(title):
        linked = clean_title(page.get("linked_from_title", ""))
        return f"{linked} (מסמך PDF)" if linked else "מסמך PDF באתר הפניקס"
    return title


def find_boilerplate(pages: list[dict]) -> set[str]:
    counts: Counter[str] = Counter()
    html_pages = [p for p in pages if p["source_type"] == "html"]
    for p in html_pages:
        counts.update({line.strip() for line in p["markdown"].splitlines() if line.strip()})
    limit = max(5, int(len(html_pages) * BOILERPLATE_RATIO))
    return {line for line, n in counts.items() if n > limit}


def is_faq_question(line: str) -> bool:
    s = line.strip().strip("*").strip()
    return s.endswith("?") and 8 < len(s) < 160


def sections(markdown: str, faq_mode: bool) -> list[tuple[list[str], str]]:
    """Split into (heading_path, body) pairs. In FAQ mode a bold/short question line starts a section."""
    path: list[str] = []
    question: list[str] = []  # current FAQ question; replaced, never stacked
    out: list[tuple[list[str], str]] = []
    body: list[str] = []

    def flush() -> None:
        text = "\n".join(body).strip()
        if text:
            out.append((path + question, text))
        body.clear()

    for line in markdown.splitlines():
        m = HEADING_RE.match(line)
        if m:
            flush()
            heading = m.group(2).strip("* ")
            if faq_mode and is_faq_question(heading):
                question[:] = [heading]
                continue
            level = len(m.group(1))
            path[:] = path[: level - 1] + [heading]
            question.clear()
            continue
        if faq_mode and is_faq_question(line):
            flush()
            question[:] = [line.strip().strip("* ")]
            continue
        body.append(line)
    flush()
    return out


def split_long(text: str) -> list[str]:
    if len(text) <= MAX_CHARS:
        return [text]
    parts, current = [], ""
    for para in re.split(r"\n\s*\n|\n(?=\s*[*\-•]\s)", text):
        if current and len(current) + len(para) > MAX_CHARS:
            parts.append(current.strip())
            current = current[-OVERLAP_CHARS:] + "\n"
        while len(para) > MAX_CHARS:  # a single huge paragraph (common in PDFs)
            parts.append((current + para[:MAX_CHARS]).strip())
            current, para = "", para[MAX_CHARS - OVERLAP_CHARS:]
        current += para + "\n\n"
    if current.strip():
        parts.append(current.strip())
    return parts


def merge_small(secs: list[tuple[list[str], str]]) -> list[tuple[list[str], str]]:
    merged: list[tuple[list[str], str]] = []
    for path, text in secs:
        if merged and (len(merged[-1][1]) < MIN_CHARS or len(text) < MIN_CHARS) \
                and len(merged[-1][1]) + len(text) <= MAX_CHARS:
            prev_path, prev_text = merged[-1]
            heading = f"### {path[-1]}\n" if path and path != prev_path else ""
            merged[-1] = (prev_path or path, f"{prev_text}\n\n{heading}{text}")
        else:
            merged.append((path, text))
    return merged


def ancestor_titles(url: str, titles: dict[str, str], depth: int = 2) -> list[str]:
    """Titles of the nearest parent pages by URL path, e.g. ['ביטוח בריאות', 'מחלות קשות']."""
    parts = urlparse(url).path.strip("/").split("/")
    found = []
    for i in range(len(parts) - 1, 0, -1):
        parent = f"https://www.fnx.co.il/{'/'.join(parts[:i])}/"
        if parent in titles:
            found.insert(0, titles[parent])
            if len(found) == depth:
                break
    return found


def chunk_page(page: dict, boilerplate: set[str], titles: dict[str, str]) -> list[dict]:
    lines = [
        line for line in page["markdown"].splitlines()
        if line.strip() not in boilerplate and not NOISE_LINE_RE.match(line.strip())
    ]
    markdown = re.sub(r"\n{3,}", "\n\n", html.unescape("\n".join(lines)))
    title = clean_title(page["title"])
    faq_mode = "faq" in page["url"].lower() or "שאלות" in title
    breadcrumb = [t for t in ancestor_titles(page["url"], titles) if t != title]
    chunks = []
    for path, text in merge_small(sections(markdown, faq_mode)):
        # Drop the page title from the path when it is just the H1.
        crumbs = [h for h in path if h and h != title and not PDF_PAGE_RE.match(h)]
        for piece in split_long(text):
            if len(piece) < 40:
                continue
            header = " › ".join([*breadcrumb, title, *crumbs])
            content = f"{header}\n\n{piece}"
            chunks.append({
                "url": page["url"],
                "title": title,
                "display_title": display_title(page, title),
                "section": " › ".join(crumbs),
                "source_type": page["source_type"],
                "category": page.get("category", ""),
                "crawled_at": page["crawled_at"],
                "text": content,
                "content_hash": hashlib.sha1(content.encode()).hexdigest(),
            })
    url_key = hashlib.sha1(page["url"].encode()).hexdigest()[:10]
    for i, c in enumerate(chunks):
        c["chunk_id"] = f"{url_key}-{i:03d}"
    return chunks


def main() -> None:
    pages = [json.loads(f.read_text(encoding="utf-8")) for f in config.RAW_DIR.glob("*.json")]
    boilerplate = find_boilerplate(pages)
    titles = {p["url"]: clean_title(p["title"]) for p in pages if p["source_type"] == "html"}
    print(f"{len(pages)} pages, {len(boilerplate)} boilerplate lines removed")
    all_chunks = [c for p in pages for c in chunk_page(p, boilerplate, titles)]

    # Identical chunks on different URLs (shared sections) - keep the first.
    seen, unique = set(), []
    for c in all_chunks:
        body = c["text"].split("\n\n", 1)[-1]
        if body in seen:
            continue
        seen.add(body)
        unique.append(c)

    with config.CHUNKS_FILE.open("w", encoding="utf-8") as f:
        for c in unique:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    sizes = sorted(len(c["text"]) for c in unique)
    print(f"{len(unique)} chunks (dropped {len(all_chunks) - len(unique)} duplicates); "
          f"median {sizes[len(sizes) // 2]} chars, max {sizes[-1]}")
    print(f"wrote {config.CHUNKS_FILE}")


if __name__ == "__main__":
    main()
