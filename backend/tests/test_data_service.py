"""Tests for DataService LLM extraction and DB persistence (M7)."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.schemas import CrawlResult, POIData
from app.services.data_service import DataService


def _make_note(**overrides) -> CrawlResult:
    defaults = {
        "note_id": "n1",
        "title": "苏州周末好去处",
        "content": "平江路超好逛，推荐去猫的天空之城",
        "likes": 100,
        "tags": ["苏州", "周末"],
        "url": "https://xhs.com/note/1",
    }
    defaults.update(overrides)
    return CrawlResult(**defaults)


@pytest.mark.asyncio
class TestProcessNotesLLM:
    """Test LLM-based POI extraction in process_notes()."""

    async def test_uses_llm_when_available(self):
        llm = AsyncMock()
        llm.api_key = "test-key"
        llm.extract_pois.return_value = [
            {
                "name": "平江路",
                "address": "苏州市姑苏区平江路",
                "tags": ["古街", "文艺"],
                "description": "苏州最有特色的历史街区",
                "cost_range": "免费",
                "suitable_for": ["情侣", "朋友"],
            }
        ]

        svc = DataService(llm_service=llm)
        notes = [_make_note()]
        pois = await svc.process_notes(notes, "苏州")

        assert len(pois) == 1
        assert pois[0].name == "平江路"
        assert pois[0].city == "苏州"
        assert pois[0].source_url == "https://xhs.com/note/1"
        llm.extract_pois.assert_called_once()

    async def test_falls_back_to_mock_on_llm_failure(self):
        llm = AsyncMock()
        llm.api_key = "test-key"
        llm.extract_pois.side_effect = Exception("API error")

        svc = DataService(llm_service=llm)
        notes = [_make_note()]
        pois = await svc.process_notes(notes, "苏州")

        # Should fall back to mock extraction
        assert len(pois) == 1
        assert pois[0].name == "苏州周末好去处"

    async def test_uses_mock_when_no_api_key(self):
        llm = AsyncMock()
        llm.api_key = ""

        svc = DataService(llm_service=llm)
        notes = [_make_note()]
        pois = await svc.process_notes(notes, "苏州")

        assert len(pois) == 1
        assert pois[0].name == "苏州周末好去处"
        llm.extract_pois.assert_not_called()

    async def test_uses_mock_when_no_llm(self):
        svc = DataService()
        notes = [_make_note()]
        pois = await svc.process_notes(notes, "苏州")

        assert len(pois) == 1
        assert pois[0].name == "苏州周末好去处"

    async def test_batch_processing(self):
        """Notes are sent to LLM in batches of 5."""
        llm = AsyncMock()
        llm.api_key = "test-key"
        llm.extract_pois.return_value = [{"name": "地点", "tags": []}]

        svc = DataService(llm_service=llm)
        notes = [_make_note(note_id=f"n{i}") for i in range(7)]
        pois = await svc.process_notes(notes, "苏州")

        # 7 notes → 2 batches (5 + 2)
        assert llm.extract_pois.call_count == 2


@pytest.mark.asyncio
class TestGetCachedPoisFallback:
    """Test Redis → DB fallback in get_cached_pois()."""

    async def test_falls_back_to_db_on_redis_miss(self):
        redis = AsyncMock()
        redis.get.return_value = None

        db = AsyncMock()
        # Mock DB returning empty
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = []
        db.execute.return_value = result_mock

        svc = DataService(redis_client=redis, db_session=db)
        pois = await svc.get_cached_pois("苏州")

        # Should have tried DB
        assert db.execute.called

    async def test_no_redis_no_db_returns_empty(self):
        svc = DataService()
        pois = await svc.get_cached_pois("苏州")
        assert pois == []
