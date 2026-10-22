"""Stage 1a: build the list of public URLs to crawl.

sitemap.xml -> filter by robots.txt and exclusions -> categorize & prioritize -> data/urls.json
Run from backend/:  python -m crawler.sitemap
"""
import json
import re
import xml.etree.ElementTree as ET
from collections import Counter
from urllib.parse import urlparse, unquote
from urllib.robotparser import RobotFileParser

import httpx

import config

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) FnxHackathonBot/1.0"
NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}

# Paths that are public but useless for a customer-facing Q&A bot.
EXCLUDE_PATTERNS = [
    r"^/en(/|$)",
    r"^/(tags|career|404|sitemap|agents-promotions)(/|$)",
    r"thank-you",
    r"/sales/",
    r"calculator",
    r"/search",
    r"/login",
    r"\.(jpg|jpeg|png|gif|svg|webp|mp4|zip|docx?|xlsx?)$",
]

# Ordered by crawl priority: first match wins.
CATEGORIES = [
    ("claims", r"^/claims-customer-service/|claim"),
    ("faq", r"faq|questions"),
    ("service", r"^/customer-service/"),
    ("corporate", r"^/(investor-relations|fnx-insurance-ltd|esop|haskaot-mitkadmot)/"),
    ("product", r"^/[^/]+/"),
]
LOWEST_PRIORITY = {"corporate"}  # investor material: public, but rarely what a customer asks


def fetch(url: str) -> str:
    resp = httpx.get(url, headers={"User-Agent": USER_AGENT}, timeout=30, follow_redirects=True)
    resp.raise_for_status()
    return resp.text


def load_robots() -> RobotFileParser:
    rp = RobotFileParser()
    rp.parse(fetch(config.ROBOTS_URL).splitlines())
    return rp


def parse_sitemap(xml_text: str) -> list[str]:
    """Return page URLs; follows nested sitemap indexes if present."""
    root = ET.fromstring(xml_text)
    if root.tag.endswith("sitemapindex"):
        urls: list[str] = []
        for loc in root.findall("sm:sitemap/sm:loc", NS):
            urls.extend(parse_sitemap(fetch(loc.text.strip())))
        return urls
    return [loc.text.strip() for loc in root.findall("sm:url/sm:loc", NS) if loc.text]


def normalize(url: str) -> str:
    p = urlparse(url)
    path = p.path or "/"
    return f"https://www.fnx.co.il{path}" + (f"?{p.query}" if p.query else "")


def categorize(url: str) -> str:
    path = unquote(urlparse(url).path).lower()
    for name, pattern in CATEGORIES:
        if re.search(pattern, path):
            return name
    return "other"


def is_excluded(url: str) -> bool:
    p = urlparse(url)
    # robots.txt blocks /*?page=, ?tag= etc. with wildcards that urllib.robotparser
    # does not support, so drop query-string URLs entirely.
    if p.query:
        return True
    path = unquote(p.path).lower()
    return any(re.search(pat, path) for pat in EXCLUDE_PATTERNS)


def build_url_list() -> list[dict]:
    robots = load_robots()
    raw = parse_sitemap(fetch(config.SITEMAP_URL))
    seen: set[str] = set()
    items: list[dict] = []
    skipped = Counter()
    for url in raw:
        url = normalize(url)
        if url in seen:
            skipped["duplicate"] += 1
            continue
        seen.add(url)
        if urlparse(url).netloc != "www.fnx.co.il":
            skipped["other_domain"] += 1
        elif not robots.can_fetch(USER_AGENT, url):
            skipped["robots"] += 1
        elif is_excluded(url):
            skipped["excluded"] += 1
        else:
            items.append({"url": url, "category": categorize(url)})

    priority = {name: i for i, (name, _) in enumerate(CATEGORIES)}
    for name in LOWEST_PRIORITY:
        priority[name] = len(CATEGORIES) + 1
    items.sort(key=lambda it: (priority.get(it["category"], len(CATEGORIES)), it["url"]))

    print(f"sitemap URLs: {len(raw)}  kept: {len(items)}  skipped: {dict(skipped)}")
    print("by category:", dict(Counter(it["category"] for it in items)))
    return items


if __name__ == "__main__":
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    urls = build_url_list()
    config.URLS_FILE.write_text(json.dumps(urls, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"wrote {config.URLS_FILE}")
