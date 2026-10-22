"""Stage 1 checkpoint: summarize what was crawled.

Run from backend/:  python -m crawler.report
"""
import json
import random
from collections import Counter

import config
from crawler.crawl import load_not_found


def main() -> None:
    pages = [json.loads(f.read_text(encoding="utf-8")) for f in config.RAW_DIR.glob("*.json")]
    urls = json.loads(config.URLS_FILE.read_text(encoding="utf-8"))
    errors = config.ERRORS_LOG.read_text(encoding="utf-8").splitlines() if config.ERRORS_LOG.exists() else []
    error_urls = {line.split("\t")[1] for line in errors if "\t" in line}
    saved_urls = {p["url"] for p in pages}

    html = [p for p in pages if p["source_type"] == "html"]
    pdf = [p for p in pages if p["source_type"] == "pdf"]
    print(f"sitemap URLs to crawl: {len(urls)}")
    print(f"saved HTML pages:      {len(html)}")
    print(f"saved PDFs:            {len(pdf)}")
    print(f"404 (stale sitemap):   {len(load_not_found())}")
    print(f"still failing:         {len(error_urls - saved_urls)}  (bot protection etc. - rerun crawl to retry)")
    print(f"total characters:      {sum(len(p['markdown']) for p in pages):,}")
    print("pages by category:", dict(Counter(p["category"] for p in pages)))

    short = [p for p in html if len(p["markdown"]) < 200]
    print(f"\nshort HTML pages (<200 chars): {len(short)}")
    for p in short[:10]:
        print(f"  {len(p['markdown']):4}  {p['url']}")

    print("\nrandom samples:")
    random.seed(1)
    for p in random.sample(pages, min(5, len(pages))):
        print(f"\n--- {p['title']}  ({p['url']})")
        print(p["markdown"][:400])


if __name__ == "__main__":
    main()
