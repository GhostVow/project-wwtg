"""Cookie management for XHS crawler: Redis-backed with file fallback."""

import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Optional

from .config import COOKIE_TTL

logger = logging.getLogger(__name__)


def _default_cookie_dir() -> Path:
    """Return the cookie storage directory from env or default."""
    return Path(os.environ.get("XHS_COOKIES_DIR", "/data/cookies"))


def _default_cookie_file() -> Path:
    """Return the default cookie file path (inside the configurable dir)."""
    return _default_cookie_dir() / "cookies.json"


class CookieManager:
    """Manages browser cookies for the XHS crawler.

    Primary storage: Redis (key ``xhs:cookies``).
    Fallback: local JSON file when Redis is unavailable.

    Args:
        redis_client: An async Redis client (or None for file-only mode).
        cookie_file: Path to the fallback cookie file.
    """

    REDIS_KEY: str = "xhs:cookies"

    def __init__(
        self,
        redis_client: Any = None,
        cookie_file: Optional[Path] = None,
    ) -> None:
        self._redis = redis_client
        self._cookie_file = cookie_file or _default_cookie_file()
        self._cached_cookies: Optional[list[dict[str, Any]]] = None
        self._loaded_at: Optional[float] = None

    async def load_cookies(self) -> list[dict[str, Any]]:
        """Load cookies from Redis, falling back to file.

        Returns:
            List of cookie dicts (Playwright format).
        """
        # Try Redis first
        if self._redis is not None:
            try:
                raw = await self._redis.get(self.REDIS_KEY)
                if raw:
                    cookies = json.loads(raw)
                    self._cached_cookies = cookies
                    self._loaded_at = time.time()
                    logger.debug("Loaded %d cookies from Redis", len(cookies))
                    return cookies
            except Exception:
                logger.warning("Failed to load cookies from Redis, trying file fallback")

        # File fallback
        if self._cookie_file.exists():
            try:
                data = json.loads(self._cookie_file.read_text(encoding="utf-8"))
                cookies = data.get("cookies", [])
                self._cached_cookies = cookies
                self._loaded_at = data.get("saved_at", time.time())
                logger.debug("Loaded %d cookies from file", len(cookies))
                return cookies
            except Exception:
                logger.warning("Failed to load cookies from file")

        return []

    async def save_cookies(self, cookies: list[dict[str, Any]]) -> None:
        """Save cookies to Redis (with TTL) and file.

        Args:
            cookies: List of cookie dicts from Playwright.
        """
        self._cached_cookies = cookies
        self._loaded_at = time.time()

        payload = json.dumps(cookies, ensure_ascii=False)

        # Redis
        if self._redis is not None:
            try:
                await self._redis.set(self.REDIS_KEY, payload, ex=COOKIE_TTL)
                logger.debug("Saved %d cookies to Redis (TTL=%ds)", len(cookies), COOKIE_TTL)
            except Exception:
                logger.warning("Failed to save cookies to Redis")

        # File fallback
        try:
            file_data = json.dumps(
                {"cookies": cookies, "saved_at": time.time()},
                ensure_ascii=False,
                indent=2,
            )
            self._cookie_file.write_text(file_data, encoding="utf-8")
        except Exception:
            logger.warning("Failed to save cookies to file")

    def is_expired(self) -> bool:
        """Check if the currently loaded cookies are expired.

        Returns:
            True if cookies are expired or not loaded.
        """
        if self._loaded_at is None or self._cached_cookies is None:
            return True
        return (time.time() - self._loaded_at) > COOKIE_TTL
