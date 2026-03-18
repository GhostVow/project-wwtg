"""Tests for the M2 crawler module, data service, and schemas."""

import asyncio
import json
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.schemas import CrawlResult, POIData
from app.services.crawler.config import REQUEST_INTERVAL
from app.services.crawler.cookie_manager import CookieManager
from app.services.crawler.stealth import random_delay
from app.services.crawler.xhs_crawler import XHSCrawler
from app.services.data_service import DataService


# ---------------------------------------------------------------------------
# XHSCrawler.parse_note_list
# ---------------------------------------------------------------------------

class TestParseNoteList:
    """Test parsing of __INITIAL_STATE__ search results."""

    SAMPLE_STATE: dict = {
        "search": {
            "notes": [
                {
                    "id": "note_001",
                    "note_card": {
                        "title": "苏州周末好去处",
                        "desc": "推荐几个苏州周末遛娃的好地方",
                        "interact_info": {
                            "liked_count": 1200,
                            "comment_count": 45,
                            "share_count": 30,
                        },
                        "user": {"nickname": "旅行达人"},
                        "image_list": [
                            {"url": "https://img.xhs.com/1.jpg"},
                            {"url": "https://img.xhs.com/2.jpg"},
                        ],
                        "tag_list": [
                            {"name": "苏州"},
                            {"name": "周末"},
                        ],
                    },
                },
                {
                    "id": "note_002",
                    "note_card": {
                        "title": "上海一日游攻略",
                        "desc": "超全攻略",
                        "interact_info": {
                            "liked_count": 800,
                            "comment_count": 20,
                            "share_count": 10,
                        },
                        "user": {"nickname": "小红薯"},
                        "image_list": [],
                        "tag_list": [{"name": "上海"}],
                    },
                },
            ]
        }
    }

    def test_parses_notes_correctly(self) -> None:
        results = XHSCrawler.parse_note_list(self.SAMPLE_STATE)
        assert len(results) == 2

        first = results[0]
        assert first["note_id"] == "note_001"
        assert first["title"] == "苏州周末好去处"
        assert first["likes"] == 1200
        assert first["comments"] == 45
        assert first["shares"] == 30
        assert first["author"] == "旅行达人"
        assert len(first["images"]) == 2
        assert first["tags"] == ["苏州", "周末"]
        assert "note_001" in first["url"]

    def test_empty_state_returns_empty(self) -> None:
        assert XHSCrawler.parse_note_list({}) == []

    def test_missing_note_card_fields(self) -> None:
        state = {"search": {"notes": [{"id": "x", "note_card": {}}]}}
        results = XHSCrawler.parse_note_list(state)
        assert len(results) == 1
        assert results[0]["title"] == ""
        assert results[0]["likes"] == 0


# ---------------------------------------------------------------------------
# CookieManager
# ---------------------------------------------------------------------------

class TestCookieManager:
    """Test cookie save/load with mocked Redis."""

    @pytest.mark.asyncio
    async def test_save_and_load_redis(self) -> None:
        mock_redis = AsyncMock()
        stored: dict[str, str] = {}

        async def fake_set(key: str, value: str, ex: int = 0) -> None:
            stored[key] = value

        async def fake_get(key: str) -> str | None:
            return stored.get(key)

        mock_redis.set = fake_set
        mock_redis.get = fake_get

        cm = CookieManager(redis_client=mock_redis)
        cookies = [{"name": "a]", "value": "b", "domain": ".xiaohongshu.com"}]

        await cm.save_cookies(cookies)
        loaded = await cm.load_cookies()

        assert len(loaded) == 1
        assert loaded[0]["name"] == "a]"

    @pytest.mark.asyncio
    async def test_is_expired_when_not_loaded(self) -> None:
        cm = CookieManager()
        assert cm.is_expired() is True

    @pytest.mark.asyncio
    async def test_is_expired_after_save(self) -> None:
        cm = CookieManager()
        # Manually set internal state
        cm._cached_cookies = [{"name": "x"}]
        cm._loaded_at = time.time()
        assert cm.is_expired() is False


# ---------------------------------------------------------------------------
# stealth.random_delay
# ---------------------------------------------------------------------------

class TestRandomDelay:
    """Test that random_delay respects bounds."""

    @pytest.mark.asyncio
    async def test_delay_within_bounds(self) -> None:
        # Use very small bounds so test is fast
        delay = await random_delay(0.01, 0.05)
        assert 0.01 <= delay <= 0.05

    @pytest.mark.asyncio
    async def test_delay_default_params(self) -> None:
        # Just verify it's callable with defaults (don't actually wait 5-15s)
        with patch("app.services.crawler.stealth.asyncio.sleep", new_callable=AsyncMock):
            delay = await random_delay()
            assert 5 <= delay <= 15


# ---------------------------------------------------------------------------
# DataService.get_cached_pois
# ---------------------------------------------------------------------------

class TestDataServiceCache:
    """Test cache read behavior."""

    @pytest.mark.asyncio
    async def test_returns_empty_on_no_redis(self) -> None:
        ds = DataService()
        result = await ds.get_cached_pois("苏州", [])
        assert result == []

    @pytest.mark.asyncio
    async def test_returns_empty_on_cache_miss(self) -> None:
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)

        ds = DataService(redis_client=mock_redis)
        result = await ds.get_cached_pois("苏州", [])
        assert result == []

    @pytest.mark.asyncio
    async def test_returns_cached_pois(self) -> None:
        pois = [{"name": "拙政园", "city": "苏州", "tags": ["园林"]}]
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=json.dumps(pois))

        ds = DataService(redis_client=mock_redis)
        result = await ds.get_cached_pois("苏州")
        assert len(result) == 1
        assert result[0]["name"] == "拙政园"

    @pytest.mark.asyncio
    async def test_filters_by_tags(self) -> None:
        pois = [
            {"name": "拙政园", "city": "苏州", "tags": ["园林"]},
            {"name": "观前街", "city": "苏州", "tags": ["美食"]},
        ]
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=json.dumps(pois))

        ds = DataService(redis_client=mock_redis)
        result = await ds.get_cached_pois("苏州", ["园林"])
        assert len(result) == 1
        assert result[0]["name"] == "拙政园"


# ---------------------------------------------------------------------------
# Pydantic model validation
# ---------------------------------------------------------------------------

class TestSchemaValidation:
    """Test POIData and CrawlResult models."""

    def test_poi_data_minimal(self) -> None:
        poi = POIData(name="测试地点", city="苏州")
        assert poi.source_type == "xiaohongshu"
        assert poi.tags == []
        assert poi.suitable_for == []

    def test_poi_data_full(self) -> None:
        poi = POIData(
            name="拙政园",
            address="苏州市姑苏区东北街178号",
            city="苏州",
            tags=["园林", "世界遗产"],
            description="苏州最大的古典园林",
            cost_range="50-100",
            suitable_for=["亲子", "情侣"],
            source_type="xiaohongshu",
            source_url="https://www.xiaohongshu.com/explore/123",
            source_likes=5000,
            route_suggestions=["搭配虎丘"],
        )
        assert poi.cost_range == "50-100"
        assert "亲子" in poi.suitable_for

    def test_crawl_result_minimal(self) -> None:
        cr = CrawlResult(
            note_id="abc123",
            title="测试笔记",
            content="内容",
            url="https://www.xiaohongshu.com/explore/abc123",
        )
        assert cr.likes == 0
        assert cr.images == []

    def test_crawl_result_full(self) -> None:
        cr = CrawlResult(
            note_id="abc123",
            title="周末好去处",
            content="推荐几个地方",
            likes=100,
            comments=10,
            shares=5,
            author="小红薯",
            images=["img1.jpg"],
            tags=["周末"],
            url="https://www.xiaohongshu.com/explore/abc123",
        )
        assert cr.author == "小红薯"
        assert len(cr.tags) == 1
