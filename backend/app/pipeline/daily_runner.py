"""Daily pipeline runner: crawl XHS → extract POIs → cache.

Usage:
    python -m app.pipeline.daily_runner
"""

import asyncio
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


async def main() -> None:
    """Run the daily data pipeline."""
    from app.services.crawler.cookie_manager import CookieManager
    from app.services.crawler.xhs_crawler import XHSCrawler
    from app.services.data_service import DataService

    logger.info("=== Daily Pipeline Starting ===")

    # In production, these would come from real Playwright browser and Redis.
    # For now, we allow running without them (dry-run / mock mode).
    browser = None
    redis_client = None

    try:
        # Try to import and connect to Redis
        import redis.asyncio as aioredis
        from app.config import settings
        redis_client = aioredis.from_url(settings.redis_url)
        logger.info("Connected to Redis at %s", settings.redis_url)
    except Exception:
        logger.warning("Redis not available, running without cache persistence")

    try:
        # Try to launch Playwright browser
        from playwright.async_api import async_playwright
        pw = await async_playwright().start()
        browser = await pw.chromium.launch(headless=True)
        logger.info("Playwright browser launched")
    except Exception:
        logger.warning("Playwright not available, running in mock mode (no crawling)")

    cookie_manager = CookieManager(redis_client=redis_client)

    # Check cookie status before crawling
    if cookie_manager.is_expired():
        logger.warning(
            "⚠️ XHS cookies are expired or missing! "
            "Crawler will likely fail. Please re-login and update cookies."
        )

    crawler = XHSCrawler(browser=browser, cookie_manager=cookie_manager) if browser else None
    service = DataService(crawler=crawler, redis_client=redis_client)

    results = await service.run_daily_pipeline()

    logger.info("=== Pipeline Complete ===")
    for city, count in results.items():
        logger.info("  %s: %d POIs", city, count)

    # Cleanup
    if browser:
        await browser.close()
    if redis_client:
        await redis_client.close()


if __name__ == "__main__":
    asyncio.run(main())
