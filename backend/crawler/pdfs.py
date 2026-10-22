"""Stage 1d: download PDFs linked from crawled pages and extract their text.

Run from backend/ after the HTML crawl:  python -m crawler.pdfs
"""
import hashlib
import json
import re
import time
from collections import defaultdict
from datetime import datetime, timezone
from urllib.parse import unquote, urlparse

import pymupdf as fitz
import httpx

import config
from crawler.crawl import log_error, page_path
from crawler.sitemap import USER_AGENT, load_robots

# PDFs linked from these page categories are what customers ask about (claim forms, policy terms).
CATEGORY_WEIGHT = {"claims": 3, "service": 2, "faq": 2, "product": 1, "corporate": 0}
# Archives of old policies, superseded fund statutes, change summaries and financial reports are
# numerous and rarely what a customer asks about.
SKIP_PATTERNS = [
    r"/polarchive/.*_\d{4}\.pdf$",
    r"financial|report|presentation|dohot|מצגת|דוח",
    r"ריכוז|שינוי|סימון",                          # "summary of changes" / tracked-changes versions
    r"(19|20)(0\d|1\d|2[0-3])",                       # documents dated before 2024
]


def collect_candidates() -> list[tuple[str, int, str]]:
    """(pdf_url, score, title of a linking page), best first."""
    score: dict[str, int] = defaultdict(int)
    linked_from: dict[str, str] = {}
    for f in config.RAW_DIR.glob("*.json"):
        page = json.loads(f.read_text(encoding="utf-8"))
        if page.get("source_type") != "html":
            continue
        weight = CATEGORY_WEIGHT.get(page.get("category", ""), 1)
        for pdf in page.get("pdf_links", []):
            score[pdf] += 1 + weight
            linked_from.setdefault(pdf, page.get("title", ""))
    robots = load_robots()
    ranked = []
    for pdf, s in score.items():
        path = unquote(urlparse(pdf).path).lower()
        if any(re.search(p, path) for p in SKIP_PATTERNS) or not robots.can_fetch(USER_AGENT, pdf):
            continue
        ranked.append((pdf, s, linked_from[pdf]))
    ranked.sort(key=lambda t: -t[1])
    return ranked


def pdf_to_markdown(data: bytes) -> tuple[str, str]:
    """Return (title, text) with a '## עמוד N' heading per page, so chunks keep page context."""
    with fitz.open(stream=data, filetype="pdf") as doc:
        title = (doc.metadata or {}).get("title", "") or ""
        parts = []
        for i, page in enumerate(doc, start=1):
            if i > config.MAX_PDF_PAGES:
                break
            # No sort=True: sorting by position reverses word order in Hebrew (visual-order) PDFs.
            text = page.get_text("text").strip()
            if text:
                parts.append(f"## עמוד {i}\n{text}")
    return title.strip(), "\n\n".join(parts)


def main() -> None:
    config.PDF_DIR.mkdir(parents=True, exist_ok=True)
    candidates = collect_candidates()[: config.MAX_PDFS]
    print(f"{len(candidates)} PDFs selected")
    saved = 0
    with httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=60, follow_redirects=True) as client:
        for i, (url, _, linking_title) in enumerate(candidates, start=1):
            out = page_path(url)
            if out.exists():
                continue
            try:
                resp = client.get(url)
                resp.raise_for_status()
                if not resp.content.startswith(b"%PDF"):
                    raise ValueError(f"not a PDF ({resp.headers.get('content-type')})")
                title, text = pdf_to_markdown(resp.content)
                if len(text) < 200:
                    raise ValueError("no extractable text (scanned PDF?)")
                filename = unquote(urlparse(url).path.rsplit("/", 1)[-1]).removesuffix(".pdf")
                record = {
                    "url": url,
                    "category": "pdf",
                    "source_type": "pdf",
                    "title": title or filename.replace("_", " ").replace("-", " "),
                    "linked_from_title": linking_title,
                    "markdown": text,
                    "crawled_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    "content_hash": hashlib.sha1(text.encode()).hexdigest(),
                    "internal_links": [],
                    "pdf_links": [],
                }
                out.write_text(json.dumps(record, ensure_ascii=False, indent=1), encoding="utf-8")
                saved += 1
            except Exception as e:  # noqa: BLE001 - keep going on any single PDF failure
                log_error(url, f"pdf: {e}")
            if i % 20 == 0:
                print(f"  {i}/{len(candidates)}")
            time.sleep(config.CRAWL_DELAY_SEC)
    print(f"saved {saved} PDFs")


if __name__ == "__main__":
    main()
