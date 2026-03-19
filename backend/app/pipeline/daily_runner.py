"""Daily pipeline runner: crawl XHS → extract POIs → cache.

Usage:
    python -m app.pipeline.daily_runner
    python -m app.pipeline.daily_runner --city 上海 --limit 2
"""

import argparse
import asyncio
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="WWTG daily data pipeline")
    parser.add_argument("--city", type=str, help="Single city to crawl (default: all)")
    parser.add_argument("--limit", type=int, help="Max keywords per city (default: all)")
    return parser.parse_args()


async def main() -> None:
    """Run the daily data pipeline."""
    args = parse_args()

    from app.config import settings
    from app.services.crawler.cookie_manager import CookieManager
    from app.services.crawler.xhs_crawler import XHSCrawler
    from app.services.data_service import DataService

    logger.info("=== Daily Pipeline Starting ===")

    redis_client = None
    browser = None
    pw = None

    # --- Redis ---
    try:
        import redis.asyncio as aioredis

        redis_client = aioredis.from_url(settings.redis_url)
        await redis_client.ping()
        logger.info("Connected to Redis at %s", settings.redis_url)
    except Exception:
        logger.warning("Redis not available — running without cache persistence")
        redis_client = None

    # --- Cookie check ---
    cookie_manager = CookieManager(redis_client=redis_client)
    cookies = await cookie_manager.load_cookies()

    if not cookies:
        logger.warning(
            "⚠️  No XHS cookies found. Skipping crawl. "
            "Place cookies in $XHS_COOKIES_DIR (default /data/cookies/cookies.json) "
            "or store them in Redis key '%s'.",
            CookieManager.REDIS_KEY,
        )
        logger.info("=== Pipeline Skipped (no cookies) ===")
        if redis_client:
            await redis_client.close()
        return

    if cookie_manager.is_expired():
        logger.warning(
            "⚠️  XHS cookies are expired. Crawl may fail — "
            "consider re-logging and updating cookies."
        )

    # --- Playwright browser ---
    try:
        from playwright.async_api import async_playwright

        pw = await async_playwright().start()
        browser = await pw.chromium.launch(headless=True)
        logger.info("Playwright browser launched")
    except Exception:
        logger.warning(
            "Playwright not available — cannot crawl. "
            "Install with: pip install playwright && playwright install chromium"
        )
        if redis_client:
            await redis_client.close()
        return

    # --- Run pipeline ---
    try:
        crawler = XHSCrawler(browser=browser, cookie_manager=cookie_manager)
        service = DataService(crawler=crawler, redis_client=redis_client)

        results = await service.run_daily_pipeline(
            cities=[args.city] if args.city else None,
            keyword_limit=args.limit,
        )

        logger.info("=== Pipeline Complete ===")
        for city, count in results.items():
            logger.info("  %s: %d POIs", city, count)
    except Exception:
        logger.exception("Pipeline failed with unexpected error")
    finally:
        if browser:
            await browser.close()
        if pw:
            await pw.stop()
        if redis_client:
            await redis_client.close()


if __name__ == "__main__":
    asyncio.run(main())
