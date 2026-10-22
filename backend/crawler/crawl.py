"""Stage 1b/1c: crawl the URL list with Crawl4AI and save clean Markdown per page.

Run from backend/:
    python -m crawler.crawl --pilot 30     # small varied sample, for tuning cleaning
    python -m crawler.crawl                # full crawl (resumable)
    python -m crawler.crawl --discover     # also crawl internal links missing from the sitemap (depth 1)
"""
import argparse
import asyncio
import hashlib
import json
import random
import re
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse

from crawl4ai import AsyncWebCrawler, BrowserConfig, CacheMode, CrawlerRunConfig

import config
from crawler.sitemap import USER_AGENT, is_excluded, load_robots, normalize

EXCLUDED_TAGS = ["nav", "header", "footer", "aside", "form", "script", "style", "noscript", "iframe"]
# Site chrome that is not inside semantic tags; found during the pilot crawl.
EXCLUDED_SELECTOR = ", ".join([
    ".shadow-ituran-selection",   # cookie consent banner (desktop + mobile)
    ".entrance-bar",              # "כניסה לפורטלים" portals bar
    ".contacts-section",          # "כל הדרכים לדבר איתנו" block repeated on every page
    ".modal-dropdown-content",    # hidden mobile copy of sections already rendered for desktop
    "[class*='cookie']", "[id*='cookie']",
    "[class*='breadcrumb']",
    "[class*='skip-link']",
    "[class*='accessibility']",
    "[class*='share']",
])
# Radware bot protection serves a captcha page instead of content.
BLOCK_MARKERS = ("Radware", "captcha", "Captcha")
# Under load the site renders a generic error template ("משהו השתבש") with HTTP 200.
ERROR_TITLE = "Error"
ERROR_TEXT = "משהו השתבש"
# Stale sitemap entries render the site's 404 template with HTTP 200.
NOT_FOUND_TITLE = "שגיאה |"
NOT_FOUND_TEXT = "העמוד שחיפשת לא נמצא"


class PageNotFound(Exception):
    pass


def load_not_found() -> set[str]:
    return set(json.loads(config.NOT_FOUND_FILE.read_text(encoding="utf-8"))) if config.NOT_FOUND_FILE.exists() else set()


def mark_not_found(url: str) -> None:
    gone = load_not_found() | {url}
    config.NOT_FOUND_FILE.write_text(json.dumps(sorted(gone), ensure_ascii=False, indent=1), encoding="utf-8")


def page_path(url: str):
    return config.RAW_DIR / f"{hashlib.sha1(url.encode()).hexdigest()}.json"


def run_config() -> CrawlerRunConfig:
    return CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        excluded_tags=EXCLUDED_TAGS,
        excluded_selector=EXCLUDED_SELECTOR,
        remove_overlay_elements=True,
        word_count_threshold=3,
        page_timeout=45_000,
        wait_until="domcontentloaded",
        delay_before_return_html=1.0,
        # Open collapsed FAQ accordions so their answers are in the DOM text.
        js_code="""
            document.querySelectorAll('details').forEach(d => d.open = true);
            document.querySelectorAll('[aria-expanded="false"]').forEach(b => { try { b.click(); } catch (e) {} });
        """,
        check_robots_txt=True,
        user_agent=USER_AGENT,
    )


def clean_markdown(md: str) -> str:
    md = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", md)                    # images
    md = re.sub(r"\[([^\]]*)\]\((?:javascript:|#)[^)]*\)", r"\1", md)  # dead links -> text
    md = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", md)                 # keep link text only
    md = re.sub(r"[ \t]+\n", "\n", md)
    md = re.sub(r"\n{3,}", "\n\n", md)
    return dedupe_blocks(md).strip()


def dedupe_blocks(md: str) -> str:
    """Drop repeated paragraphs (the site renders desktop and mobile copies of some sections)."""
    seen: set[str] = set()
    out = []
    for block in md.split("\n\n"):
        key = re.sub(r"\s+", " ", block).strip()
        if len(key) >= 40 and key in seen:
            continue
        seen.add(key)
        out.append(block)
    return "\n\n".join(out)


def blocked_reason(result) -> str | None:
    """Why this result is not real page content, or None if it is."""
    if not result.success:
        return result.error_message or f"status {result.status_code}"
    title = (result.metadata or {}).get("title", "") or ""
    if any(m in title for m in BLOCK_MARKERS):
        return f"bot protection page: {title}"
    md = result.markdown.raw_markdown if result.markdown else ""
    if not md.strip():
        return "empty page"
    if title.strip() == ERROR_TITLE or ERROR_TEXT in md[:3000]:
        return "site error page (overloaded)"
    if title.startswith(NOT_FOUND_TITLE) or NOT_FOUND_TEXT in md[:3000]:
        raise PageNotFound
    return None


def extract_links(result, base: str) -> tuple[list[str], list[str]]:
    internal, pdfs = set(), set()
    for link in (result.links or {}).get("internal", []) + (result.links or {}).get("external", []):
        href = link.get("href") if isinstance(link, dict) else link
        if not href:
            continue
        absolute = urljoin(base, href.split("#")[0])
        host = urlparse(absolute).netloc
        if not host.endswith("fnx.co.il"):
            continue
        if absolute.lower().split("?")[0].endswith(".pdf"):
            pdfs.add(absolute)
        elif host == "www.fnx.co.il":
            internal.add(normalize(absolute))
    return sorted(internal), sorted(pdfs)


def save(url: str, category: str, result) -> dict:
    md = clean_markdown(result.markdown.raw_markdown if result.markdown else "")
    internal, pdfs = extract_links(result, url)
    record = {
        "url": url,
        "category": category,
        "source_type": "html",
        "title": (result.metadata or {}).get("title", "").strip(),
        "markdown": md,
        "crawled_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "content_hash": hashlib.sha1(md.encode()).hexdigest(),
        "internal_links": internal,
        "pdf_links": pdfs,
    }
    page_path(url).write_text(json.dumps(record, ensure_ascii=False, indent=1), encoding="utf-8")
    return record


def log_error(url: str, msg: str) -> None:
    with config.ERRORS_LOG.open("a", encoding="utf-8") as f:
        f.write(f"{datetime.now().isoformat(timespec='seconds')}\t{url}\t{msg}\n")


async def crawl_all(items: list[dict], concurrency: int = config.CRAWL_CONCURRENCY,
                    delay: float = config.CRAWL_DELAY_SEC) -> None:
    gone = load_not_found()
    todo = [it for it in items if not page_path(it["url"]).exists() and it["url"] not in gone]
    print(f"{len(items)} URLs, {len(items) - len(todo)} already saved, {len(todo)} to crawl", flush=True)
    sem = asyncio.Semaphore(concurrency)
    cfg = run_config()
    done = 0

    async with AsyncWebCrawler(config=BrowserConfig(headless=True, verbose=False)) as crawler:
        async def one(item: dict) -> None:
            nonlocal done
            async with sem:
                for attempt in (1, 2):
                    try:
                        result = await crawler.arun(item["url"], config=cfg)
                        err = blocked_reason(result)
                        if err is None:
                            save(item["url"], item["category"], result)
                            break
                    except PageNotFound:
                        mark_not_found(item["url"])
                        break
                    except Exception as e:  # noqa: BLE001 - keep crawling on any page failure
                        err = repr(e)
                    if attempt == 2:
                        log_error(item["url"], err)
                    else:
                        await asyncio.sleep(config.BLOCK_BACKOFF_SEC)  # let the bot protection cool down
                await asyncio.sleep(delay)
                done += 1
                if done % 25 == 0 or done == len(todo):
                    print(f"  {done}/{len(todo)}", flush=True)

        await asyncio.gather(*(one(it) for it in todo))


def discovered_items(known: set[str]) -> list[dict]:
    """Internal links found on crawled pages that the sitemap did not list."""
    from crawler.sitemap import categorize

    robots = load_robots()
    found: set[str] = set()
    for f in config.RAW_DIR.glob("*.json"):
        found.update(json.loads(f.read_text(encoding="utf-8")).get("internal_links", []))
    new = sorted(u for u in found - known
                 if not is_excluded(u) and not JUNK_LINK_RE.search(u) and robots.can_fetch(USER_AGENT, u))
    return [{"url": u, "category": categorize(u)} for u in new]


# Links that are not content pages: fund-id pages, office files, mangled external hosts, repeated path segments.
JUNK_LINK_RE = re.compile(
    r"/\d+/?$"                              # fund-id pages
    r"|\.(xlsm?|pptx?|docx?|zip)$"          # office files
    r"|\.(org|gov)\.il|/www\.fnx\.co\.il$"  # external hosts mangled into paths
    r"|^https://www\.fnx\.co\.il/[^/]+/.+/(health-insurance|apartment-insurance)/$",  # broken relative links
    re.IGNORECASE,
)


def pilot_sample(items: list[dict], n: int) -> list[dict]:
    """A varied sample: a few URLs from every category."""
    random.seed(7)
    by_cat: dict[str, list[dict]] = {}
    for it in items:
        by_cat.setdefault(it["category"], []).append(it)
    sample: list[dict] = []
    while len(sample) < n and any(by_cat.values()):
        for cat in list(by_cat):
            if by_cat[cat]:
                sample.append(by_cat[cat].pop(random.randrange(len(by_cat[cat]))))
    return sample[:n]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pilot", type=int, default=0, help="crawl only a varied sample of N URLs")
    ap.add_argument("--discover", action="store_true", help="crawl internal links missing from the sitemap")
    ap.add_argument("--slow", action="store_true", help="one page at a time, 4s apart (retry pass after blocks)")
    ap.add_argument("--skip", default="", help="comma-separated categories to skip, e.g. corporate")
    args = ap.parse_args()

    config.RAW_DIR.mkdir(parents=True, exist_ok=True)
    items = json.loads(config.URLS_FILE.read_text(encoding="utf-8"))
    if args.pilot:
        items = pilot_sample(items, args.pilot)
    elif args.discover:
        items = discovered_items({it["url"] for it in items})
    skip = {c for c in args.skip.split(",") if c}
    items = [it for it in items if it["category"] not in skip]
    if args.slow:
        asyncio.run(crawl_all(items, concurrency=1, delay=4.0))
    else:
        asyncio.run(crawl_all(items))


if __name__ == "__main__":
    main()
