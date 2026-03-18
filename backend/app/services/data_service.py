"""Data pipeline service: crawler orchestration + Redis/PostgreSQL caching.

Replaces the W1 stub with real pipeline logic.
All external dependencies (Redis, PostgreSQL, crawler) are injected for testability.
"""

import json
import logging
from typing import Any, Optional

from app.models.schemas import CrawlResult, POIData
from app.services.crawler.config import (
    BATCH_COOLDOWN,
    CITIES,
    SEARCH_KEYWORDS,
)
from app.services.crawler.stealth import random_delay
from app.services.crawler.xhs_crawler import XHSCrawler

logger = logging.getLogger(__name__)

# Redis key patterns
_CACHE_KEY = "wwtg:pois:{city}"
_CACHE_TTL = 48 * 3600  # 48 hours


class DataService:
    """Manages POI data: crawling, LLM extraction, caching, and persistence.

    Args:
        crawler: XHSCrawler instance (or None to skip crawling).
        redis_client: Async Redis client (or None for no-cache mode).
        db_session: Async SQLAlchemy session (or None for no-persist mode).
    """

    def __init__(
        self,
        crawler: Optional[XHSCrawler] = None,
        redis_client: Any = None,
        db_session: Any = None,
    ) -> None:
        self._crawler = crawler
        self._redis = redis_client
        self._db = db_session

    # ------------------------------------------------------------------
    # Public API (preserved from W1 for backward compat)
    # ------------------------------------------------------------------

    async def get_pois(self, city: str, tags: list[str]) -> list[dict[str, Any]]:
        """Fetch POIs for a city/tag combo from cache or crawler."""
        return await self.get_cached_pois(city, tags)

    async def refresh_cache(self, city: str) -> int:
        """Trigger a cache refresh for a city. Returns number of POIs updated."""
        if self._crawler is None:
            return 0
        pois = await self._crawl_city(city)
        await self.cache_pois(city, pois)
        return len(pois)

    async def get_cache_stats(self) -> dict[str, Any]:
        """Return cache statistics."""
        stats: dict[str, Any] = {"total_pois": 0, "cities_cached": [], "last_refresh": None}
        if self._redis is None:
            return stats
        for city in CITIES:
            key = _CACHE_KEY.format(city=city)
            try:
                raw = await self._redis.get(key)
                if raw:
                    pois = json.loads(raw)
                    stats["total_pois"] += len(pois)
                    stats["cities_cached"].append(city)
            except Exception:
                pass
        return stats

    # ------------------------------------------------------------------
    # Pipeline
    # ------------------------------------------------------------------

    async def run_daily_pipeline(self) -> dict[str, int]:
        """Orchestrate the daily crawl for all cities and keywords.

        Returns:
            Dict mapping city name to number of POIs collected.
        """
        results: dict[str, int] = {}

        for city in CITIES:
            logger.info("Starting pipeline for city: %s", city)
            pois = await self._crawl_city(city)
            await self.cache_pois(city, pois)
            results[city] = len(pois)
            logger.info("City %s: %d POIs cached", city, len(pois))

        return results

    async def _crawl_city(self, city: str) -> list[POIData]:
        """Crawl all keywords for a single city and process into POIs."""
        all_pois: list[POIData] = []

        if self._crawler is None:
            logger.warning("No crawler configured, skipping crawl for %s", city)
            return all_pois

        for i, keyword in enumerate(SEARCH_KEYWORDS):
            logger.info("  Crawling keyword %d/%d: %s %s", i + 1, len(SEARCH_KEYWORDS), city, keyword)
            try:
                raw_notes = await self._crawler.search_notes(keyword=keyword, city=city, limit=20)
                notes = [CrawlResult(**n) for n in raw_notes]
                pois = await self.process_notes(notes, city)
                all_pois.extend(pois)
            except Exception:
                logger.exception("Error crawling %s %s", city, keyword)

            # Batch cooldown between keyword groups
            if i < len(SEARCH_KEYWORDS) - 1:
                logger.debug("  Batch cooldown %ds", BATCH_COOLDOWN)
                await random_delay(BATCH_COOLDOWN, BATCH_COOLDOWN + 5)

        return all_pois

    # ------------------------------------------------------------------
    # Processing
    # ------------------------------------------------------------------

    async def process_notes(self, notes: list[CrawlResult], city: str) -> list[POIData]:
        """Extract POI data from crawled notes using LLM.

        Currently returns a mock/heuristic extraction.
        Will integrate real LLM in a future milestone.

        Args:
            notes: List of crawled note results.
            city: City the notes belong to.

        Returns:
            List of extracted POIData.
        """
        pois: list[POIData] = []

        for note in notes:
            # Mock LLM extraction: create a POI from the note metadata
            poi = POIData(
                name=note.title[:50] if note.title else "未知地点",
                city=city,
                tags=note.tags[:5],
                description=note.content[:200] if note.content else None,
                source_type="xiaohongshu",
                source_url=note.url,
                source_likes=note.likes,
            )
            pois.append(poi)

        return pois

    # ------------------------------------------------------------------
    # Caching
    # ------------------------------------------------------------------

    async def cache_pois(self, city: str, pois: list[POIData]) -> None:
        """Write POIs to Redis (48h TTL) and optionally PostgreSQL.

        Args:
            city: City key.
            pois: List of POIData to cache.
        """
        payload = json.dumps(
            [p.model_dump() for p in pois],
            ensure_ascii=False,
        )

        # Redis
        if self._redis is not None:
            key = _CACHE_KEY.format(city=city)
            try:
                await self._redis.set(key, payload, ex=_CACHE_TTL)
                logger.debug("Cached %d POIs for %s in Redis (TTL=%ds)", len(pois), city, _CACHE_TTL)
            except Exception:
                logger.warning("Failed to cache POIs in Redis for %s", city)

        # PostgreSQL persistence (placeholder — needs DB models)
        if self._db is not None:
            logger.debug("PostgreSQL persistence not yet implemented")

    async def get_cached_pois(self, city: str, tags: list[str] | None = None) -> list[dict[str, Any]]:
        """Read POIs from Redis cache, optionally filtered by tags.

        Args:
            city: City to query.
            tags: Optional tag filter (any-match).

        Returns:
            List of POI dicts. Empty list on cache miss.
        """
        if self._redis is None:
            logger.debug("Cache SKIP for %s (no Redis client configured)", city)
            return []

        key = _CACHE_KEY.format(city=city)
        try:
            raw = await self._redis.get(key)
            if not raw:
                logger.info("Cache MISS for %s", city)
                return []

            logger.info("Cache HIT for %s", city)
            pois: list[dict[str, Any]] = json.loads(raw)

            # Filter by tags if requested
            if tags:
                tag_set = set(tags)
                pois = [p for p in pois if tag_set & set(p.get("tags", []))]

            return pois
        except Exception:
            logger.warning("Failed to read cached POIs for %s", city)
            return []
