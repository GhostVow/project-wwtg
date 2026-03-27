"""Fetch XHS note details and save to JSON for POI extraction.

Reads a seed JSON file (search results with note IDs), fetches each note's
full content via Playwright, and saves enriched data.

Usage (run locally, NOT in Docker):
    python fetch_note_details.py data/seed/suzhou.json --output data/seed/suzhou_full.json
"""

import argparse
import asyncio
import json
import logging
import random
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

XHS_NOTE_URL = "https://www.xiaohongshu.com/explore/{note_id}"


async def fetch_note(page, note_id: str, title: str) -> dict | None:
    """Fetch a single note's content."""
    url = XHS_NOTE_URL.format(note_id=note_id)
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        # Wait for content to load
        await page.wait_for_selector("#detail-desc, .note-content, .content", timeout=10000)

        # Extract content from multiple possible selectors
        content = ""
        for selector in ["#detail-desc", ".note-content", ".content", "article"]:
            try:
                el = await page.query_selector(selector)
                if el:
                    text = await el.inner_text()
                    if len(text) > len(content):
                        content = text
            except Exception:
                pass

        # Extract tags
        tags = []
        try:
            tag_elements = await page.query_selector_all(".tag-item, a[href*='search']")
            for tag_el in tag_elements:
                tag_text = await tag_el.inner_text()
                tag_text = tag_text.strip().lstrip("#")
                if tag_text and len(tag_text) < 20:
                    tags.append(tag_text)
        except Exception:
            pass

        # Extract location if available
        location = None
        try:
            loc_el = await page.query_selector(".location, [data-type='location']")
            if loc_el:
                location = await loc_el.inner_text()
        except Exception:
            pass

        logger.info("✅ %s — %d chars, %d tags", title[:30], len(content), len(tags))
        return {
            "note_id": note_id,
            "content": content,
            "tags": tags,
            "location": location,
        }

    except Exception as e:
        logger.warning("❌ %s — %s", title[:30], str(e)[:80])
        return None


async def main():
    parser = argparse.ArgumentParser(description="Fetch XHS note details")
    parser.add_argument("input", help="Input JSON file (search results)")
    parser.add_argument("--output", "-o", help="Output JSON file (enriched)")
    parser.add_argument("--limit", "-l", type=int, default=50, help="Max notes to fetch")
    parser.add_argument("--delay-min", type=int, default=5, help="Min delay between requests (seconds)")
    parser.add_argument("--delay-max", type=int, default=15, help="Max delay between requests (seconds)")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        logger.error("File not found: %s", input_path)
        sys.exit(1)

    output_path = Path(args.output) if args.output else input_path.with_name(input_path.stem + "_full.json")

    raw = json.loads(input_path.read_text(encoding="utf-8"))

    # Extract items
    if isinstance(raw, dict) and "results" in raw:
        items = raw["results"]
    elif isinstance(raw, list):
        items = raw
    else:
        items = []

    items = items[:args.limit]
    logger.info("Fetching details for %d notes...", len(items))

    try:
        from playwright.async_api import async_playwright
    except ImportError:
        logger.error("playwright not installed. Run: pip install playwright && playwright install chromium")
        sys.exit(1)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # headless=False for anti-detection
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1440, "height": 900},
            locale="zh-CN",
        )
        page = await context.new_page()

        enriched = []
        for i, item in enumerate(items):
            note_id = item.get("id", item.get("note_id", ""))
            title = item.get("title", "")
            if not note_id:
                continue

            result = await fetch_note(page, note_id, title)
            if result:
                # Merge with original data
                enriched_item = {**item, **result}
                enriched.append(enriched_item)
            else:
                enriched.append(item)  # Keep original even if fetch failed

            # Random delay
            if i < len(items) - 1:
                delay = random.randint(args.delay_min, args.delay_max)
                logger.info("  Waiting %ds...", delay)
                await asyncio.sleep(delay)

        await browser.close()

    # Save
    output_path.write_text(
        json.dumps(enriched, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info("Saved %d enriched notes to %s", len(enriched), output_path)
    logger.info("Notes with content: %d/%d",
                sum(1 for e in enriched if e.get("content")), len(enriched))


if __name__ == "__main__":
    asyncio.run(main())
