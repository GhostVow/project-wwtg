"""Xiaohongshu crawler: search notes and extract POI-relevant data."""

import json
import logging
from typing import Any, Optional

from .config import (
    BATCH_COOLDOWN,
    REQUEST_INTERVAL,
    XHS_NOTE_URL,
    XHS_SEARCH_URL,
)
from .cookie_manager import CookieManager
from .stealth import apply_stealth, random_delay

logger = logging.getLogger(__name__)


class XHSCrawler:
    """Async crawler for Xiaohongshu notes.

    All browser interactions go through the injected ``browser`` dependency,
    making the class fully mockable without real Playwright.

    Args:
        browser: A Playwright async browser instance (or mock).
        cookie_manager: CookieManager for session persistence.
    """

    def __init__(
        self,
        browser: Any = None,
        cookie_manager: Optional[CookieManager] = None,
    ) -> None:
        self._browser = browser
        self._cookie_manager = cookie_manager or CookieManager()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def search_notes(
        self,
        keyword: str,
        city: str,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Search XHS for notes matching keyword + city.

        Args:
            keyword: Search term (e.g. "周末去哪玩").
            city: City name to scope the search.
            limit: Max notes to return.

        Returns:
            List of parsed note dicts.
        """
        query = f"{city} {keyword}"
        url = f"{XHS_SEARCH_URL}?keyword={query}"

        page = await self._new_page()
        try:
            await apply_stealth(page)

            # Load cookies if available
            cookies = await self._cookie_manager.load_cookies()
            if cookies:
                await page.context.add_cookies(cookies)

            await page.goto(url, wait_until="networkidle")
            await random_delay(*REQUEST_INTERVAL)

            initial_state = await self.extract_initial_state(page)
            notes = self.parse_note_list(initial_state)

            # Save cookies after successful request
            new_cookies = await page.context.cookies()
            await self._cookie_manager.save_cookies(new_cookies)

            return notes[:limit]
        finally:
            await page.close()

    async def get_note_detail(self, note_id: str) -> dict[str, Any]:
        """Fetch full details for a single note.

        Args:
            note_id: The XHS note identifier.

        Returns:
            Dict with note details (title, content, likes, etc.).
        """
        url = XHS_NOTE_URL.format(note_id=note_id)

        page = await self._new_page()
        try:
            await apply_stealth(page)

            cookies = await self._cookie_manager.load_cookies()
            if cookies:
                await page.context.add_cookies(cookies)

            await page.goto(url, wait_until="networkidle")
            await random_delay(*REQUEST_INTERVAL)

            initial_state = await self.extract_initial_state(page)
            note = self._parse_note_detail(initial_state, note_id)

            new_cookies = await page.context.cookies()
            await self._cookie_manager.save_cookies(new_cookies)

            return note
        finally:
            await page.close()

    # ------------------------------------------------------------------
    # Extraction helpers
    # ------------------------------------------------------------------

    async def extract_initial_state(self, page: Any) -> dict[str, Any]:
        """Extract ``window.__INITIAL_STATE__`` from a loaded XHS page.

        Args:
            page: Playwright page with XHS content loaded.

        Returns:
            Parsed dict of the initial state, or empty dict on failure.
        """
        try:
            raw = await page.evaluate("() => JSON.stringify(window.__INITIAL_STATE__)")
            if raw:
                return json.loads(raw)
        except Exception:
            logger.warning("Failed to extract __INITIAL_STATE__")
        return {}

    @staticmethod
    def parse_note_list(initial_state: dict[str, Any]) -> list[dict[str, Any]]:
        """Parse search results from the initial state into structured data.

        Expected structure (simplified)::

            {
                "search": {
                    "notes": [
                        {
                            "id": "...",
                            "note_card": {
                                "title": "...",
                                "desc": "...",
                                "interact_info": {"liked_count": 100, "comment_count": 10, "share_count": 5},
                                "user": {"nickname": "..."},
                                "image_list": [{"url": "..."}],
                                "tag_list": [{"name": "..."}]
                            }
                        }
                    ]
                }
            }

        Args:
            initial_state: Parsed ``__INITIAL_STATE__`` dict.

        Returns:
            List of note dicts with normalised keys.
        """
        results: list[dict[str, Any]] = []

        notes_data = (
            initial_state
            .get("search", {})
            .get("notes", [])
        )

        for item in notes_data:
            card = item.get("note_card", {})
            interact = card.get("interact_info", {})
            images = [img.get("url", "") for img in card.get("image_list", [])]
            tags = [t.get("name", "") for t in card.get("tag_list", [])]

            results.append({
                "note_id": item.get("id", ""),
                "title": card.get("title", ""),
                "content": card.get("desc", ""),
                "likes": int(interact.get("liked_count", 0)),
                "comments": int(interact.get("comment_count", 0)),
                "shares": int(interact.get("share_count", 0)),
                "author": card.get("user", {}).get("nickname"),
                "images": images,
                "tags": tags,
                "url": f"https://www.xiaohongshu.com/explore/{item.get('id', '')}",
            })

        return results

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_note_detail(
        initial_state: dict[str, Any],
        note_id: str,
    ) -> dict[str, Any]:
        """Parse a single note detail page's initial state."""
        note_data = initial_state.get("note", {}).get("note", {})
        interact = note_data.get("interact_info", {})
        images = [img.get("url", "") for img in note_data.get("image_list", [])]
        tags = [t.get("name", "") for t in note_data.get("tag_list", [])]

        return {
            "note_id": note_id,
            "title": note_data.get("title", ""),
            "content": note_data.get("desc", ""),
            "likes": int(interact.get("liked_count", 0)),
            "comments": int(interact.get("comment_count", 0)),
            "shares": int(interact.get("share_count", 0)),
            "author": note_data.get("user", {}).get("nickname"),
            "images": images,
            "tags": tags,
            "url": f"https://www.xiaohongshu.com/explore/{note_id}",
        }

    async def _new_page(self) -> Any:
        """Create a new browser page. Raises if no browser is set."""
        if self._browser is None:
            raise RuntimeError("No browser instance provided to XHSCrawler")
        context = await self._browser.new_context()
        return await context.new_page()
