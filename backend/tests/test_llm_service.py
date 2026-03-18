"""Tests for LLM service."""

import pytest

from app.services.llm_service import LLMService


@pytest.fixture
def llm_no_key() -> LLMService:
    return LLMService(api_key="")


@pytest.fixture
def llm_with_key() -> LLMService:
    return LLMService(api_key="test-key-123")


class TestParseIntentMock:
    """Test mock parse_intent (no API key)."""

    @pytest.mark.asyncio
    async def test_single_city(self, llm_no_key: LLMService) -> None:
        result = await llm_no_key.parse_intent("苏州", [])
        assert result["city"] == "苏州"

    @pytest.mark.asyncio
    async def test_multi_info(self, llm_no_key: LLMService) -> None:
        result = await llm_no_key.parse_intent("苏州，和老公，我是孕妇", [])
        assert result["city"] == "苏州"
        assert result["companion_type"] == "情侣"
        assert "孕妇" in result["constraints"]

    @pytest.mark.asyncio
    async def test_preferences(self, llm_no_key: LLMService) -> None:
        result = await llm_no_key.parse_intent("人少免费的地方", [])
        assert "人少" in result["preferences"]
        assert "免费" in result["preferences"]

    @pytest.mark.asyncio
    async def test_no_info(self, llm_no_key: LLMService) -> None:
        result = await llm_no_key.parse_intent("你好", [])
        assert result["city"] is None
        assert result["companion_type"] is None

    @pytest.mark.asyncio
    async def test_friend_companion(self, llm_no_key: LLMService) -> None:
        result = await llm_no_key.parse_intent("和朋友去杭州", [])
        assert result["city"] == "杭州"
        assert result["companion_type"] == "朋友"

    @pytest.mark.asyncio
    async def test_parent_child(self, llm_no_key: LLMService) -> None:
        result = await llm_no_key.parse_intent("带孩子去上海", [])
        assert result["city"] == "上海"
        assert result["companion_type"] == "亲子"


class TestGeneratePlansMock:
    """Test mock plan generation."""

    @pytest.mark.asyncio
    async def test_returns_two_plans(self, llm_no_key: LLMService) -> None:
        plans = await llm_no_key.generate_plans(
            context={"city": "苏州", "constraints": []},
            weather={"city": "苏州", "condition": "晴"},
            pois=[],
        )
        assert len(plans) == 2

    @pytest.mark.asyncio
    async def test_plan_has_required_fields(self, llm_no_key: LLMService) -> None:
        plans = await llm_no_key.generate_plans(
            context={"city": "苏州", "constraints": []},
            weather={},
            pois=[],
        )
        for plan in plans:
            assert "plan_id" in plan
            assert "title" in plan
            assert "emoji" in plan
            assert "stops" in plan
            assert "tips" in plan

    @pytest.mark.asyncio
    async def test_plans_with_constraints(self, llm_no_key: LLMService) -> None:
        plans = await llm_no_key.generate_plans(
            context={"city": "苏州", "constraints": ["孕妇"]},
            weather={},
            pois=[],
        )
        tags_all = []
        for p in plans:
            tags_all.extend(p.get("tags", []))
        assert "孕妇友好" in tags_all


class TestFallback:
    """Test that API failure falls back to mock."""

    @pytest.mark.asyncio
    async def test_parse_intent_fallback(self, llm_with_key: LLMService) -> None:
        # With a fake key, API call will fail and fall back to mock
        result = await llm_with_key.parse_intent("苏州", [])
        assert result["city"] == "苏州"

    @pytest.mark.asyncio
    async def test_generate_plans_fallback(self, llm_with_key: LLMService) -> None:
        plans = await llm_with_key.generate_plans(
            context={"city": "苏州", "constraints": []},
            weather={},
            pois=[],
        )
        assert len(plans) == 2
