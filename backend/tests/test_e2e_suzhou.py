"""M3: End-to-end integration tests — Suzhou 3 scenarios.

Tests the complete pipeline: AMAP fetch → LLM enrich → cache → retrieve.
Uses mock AMAP + mock LLM to verify data flow without external dependencies.

Acceptance criteria:
1. Pipeline produces POIs with correct schema for Suzhou
2. Each POI has tags, reason, suitable_for, cost_range after LLM enrichment
3. Three scenarios: 景点+亲子, 情侣美食+咖啡, 全品类无LLM
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.schemas import POIData
from app.pipeline.amap_config import AMAP_TYPE_CODES
from app.services.amap_poi_service import AmapPoiService
from app.services.data_service import DataService
from app.services.llm_service import LLMService


# ---------------------------------------------------------------------------
# Fixtures: mock AMAP responses for Suzhou
# ---------------------------------------------------------------------------

def _amap_poi(name: str, amap_type: str, rating: float | None = None, address: str = "") -> dict:
    """Build a parsed AMAP POI dict (post-_parse_poi format)."""
    return {
        "name": name,
        "address": address or f"苏州市{name}路1号",
        "location": "120.632,31.321",
        "amap_type": amap_type,
        "tags": [],  # will be filled by _map_type_to_tags in real flow
        "rating": rating,
        "phone": "",
    }


SUZHOU_SCENIC = [
    _amap_poi("拙政园", "风景名胜;公园", 4.8, "苏州市姑苏区东北街178号"),
    _amap_poi("虎丘", "风景名胜;公园", 4.7, "苏州市虎丘区虎丘山门内8号"),
    _amap_poi("留园", "风景名胜;公园", 4.7, "苏州市姑苏区留园路338号"),
]

SUZHOU_FOOD = [
    _amap_poi("松鹤楼", "餐饮服务;中餐厅", 4.6, "苏州市姑苏区太监弄72号"),
    _amap_poi("得月楼", "餐饮服务;中餐厅", 4.5, "苏州市姑苏区太监弄43号"),
]

SUZHOU_CAFE = [
    _amap_poi("% Arabica", "餐饮服务;咖啡厅", 4.3, "苏州市姑苏区平江路"),
    _amap_poi("猫的天空之城", "餐饮服务;咖啡厅", 4.4, "苏州市姑苏区平江路"),
]

SUZHOU_KIDS = [
    _amap_poi("苏州乐园", "体育休闲服务;游乐场", 4.2, "苏州市虎丘区"),
    _amap_poi("华谊兄弟电影世界", "体育休闲服务;游乐场", 4.0, "苏州市相城区"),
]

SUZHOU_MUSEUM = [
    _amap_poi("苏州博物馆", "科教文化服务;博物馆", 4.9, "苏州市姑苏区东北街204号"),
]

# Map type codes → mock responses
_MOCK_TYPE_RESPONSES = {
    "110000": SUZHOU_SCENIC,
    "050000": SUZHOU_FOOD,
    "050500": SUZHOU_CAFE,
    "141200|141300": SUZHOU_KIDS,
    "080000": [],  # no results for 休闲
    "110201": SUZHOU_MUSEUM,
}


def _make_mock_amap_service() -> AmapPoiService:
    """Create an AmapPoiService that returns mock data without HTTP calls."""
    svc = AmapPoiService(api_key="test-key")

    async def mock_search_text(city, types="", page=1, **kw):
        if page > 1:
            return []  # single page of results
        return _MOCK_TYPE_RESPONSES.get(types, [])

    svc.search_text = mock_search_text  # type: ignore[assignment]
    return svc


def _make_mock_llm_service() -> LLMService:
    """Create an LLMService that returns deterministic recommendations."""
    svc = LLMService(api_key="test-key")

    async def mock_chat_completion(system: str, user: str, **kw):
        """Parse POI names from user prompt and generate mock recommendations."""
        import re
        # Extract POI data from the JSON in the prompt
        try:
            json_match = re.search(r'\[.*\]', user, re.DOTALL)
            if json_match:
                pois = json.loads(json_match.group())
            else:
                pois = [{}]
        except json.JSONDecodeError:
            pois = [{}]

        results = []
        for p in pois:
            name = p.get("name", "")
            poi_type = p.get("type", "")
            is_park = any(t in poi_type for t in ("风景", "公园"))
            is_cafe = "咖啡" in poi_type
            is_kids = any(t in poi_type for t in ("游乐", "亲子", "儿童"))
            is_museum = "博物馆" in poi_type

            if is_park:
                results.append({
                    "tags": ["园林", "古典", "拍照"],
                    "reason": f"{name}是苏州经典园林，四季皆宜",
                    "suitable_for": ["情侣", "朋友", "家人"],
                    "cost_range": "50-100",
                })
            elif is_cafe:
                results.append({
                    "tags": ["下午茶", "文艺", "拍照"],
                    "reason": f"{name}适合和朋友坐坐聊聊天",
                    "suitable_for": ["情侣", "朋友"],
                    "cost_range": "30以内",
                })
            elif is_kids:
                results.append({
                    "tags": ["遛娃", "户外", "周末"],
                    "reason": f"{name}适合带孩子玩一天",
                    "suitable_for": ["亲子", "家人"],
                    "cost_range": "100+",
                })
            elif is_museum:
                results.append({
                    "tags": ["文化", "免费", "室内"],
                    "reason": f"{name}免费开放，建筑本身就是展品",
                    "suitable_for": ["独自", "情侣", "朋友", "家人"],
                    "cost_range": "免费",
                })
            else:
                results.append({
                    "tags": ["美食", "老字号"],
                    "reason": f"{name}是苏帮菜代表",
                    "suitable_for": ["情侣", "朋友", "家人"],
                    "cost_range": "50-100",
                })

        return json.dumps(results, ensure_ascii=False)

    svc.chat_completion = mock_chat_completion  # type: ignore[assignment]
    return svc


# ---------------------------------------------------------------------------
# Scenario 1: 景点 + 亲子 — Family outing
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestScenario1FamilyOuting:
    """Suzhou family outing: scenic spots + kid-friendly places."""

    async def test_pipeline_produces_scenic_and_kids_pois(self):
        """Pipeline fetches scenic + kids POIs for Suzhou."""
        amap = _make_mock_amap_service()
        type_codes = {"景点": "110000", "亲子": "141200|141300"}

        raw = await amap.fetch_city_pois("苏州", type_codes, pages=3)
        await amap.close()

        names = [p["name"] for p in raw]
        assert "拙政园" in names
        assert "苏州乐园" in names
        assert len(raw) == 5  # 3 scenic + 2 kids

    async def test_llm_enrichment_adds_fields(self):
        """Each POI gets reason + tags after LLM enrichment."""
        amap = _make_mock_amap_service()
        llm = _make_mock_llm_service()
        type_codes = {"景点": "110000", "亲子": "141200|141300"}

        raw = await amap.fetch_city_pois("苏州", type_codes, pages=3)
        enrichment_input = [{**p, "city": "苏州"} for p in raw]
        recs = await llm.generate_poi_recommendations(enrichment_input, season="春天")
        await amap.close()
        await llm.close()

        assert len(recs) == len(raw)
        for rec in recs:
            assert len(rec["tags"]) >= 1
            assert len(rec["reason"]) > 0
            assert len(rec["suitable_for"]) >= 1
            assert rec["cost_range"] != ""

    async def test_full_pipeline_to_cache(self):
        """Full pipeline: fetch → enrich → convert to POIData → cache."""
        amap = _make_mock_amap_service()
        llm = _make_mock_llm_service()
        redis = AsyncMock()
        redis.get.return_value = None

        type_codes = {"景点": "110000", "亲子": "141200|141300"}
        raw = await amap.fetch_city_pois("苏州", type_codes, pages=3)

        enrichment_input = [{**p, "city": "苏州"} for p in raw]
        recs = await llm.generate_poi_recommendations(enrichment_input, season="春天")

        # Merge and convert
        poi_models = []
        for idx, r in enumerate(raw):
            rec = recs[idx] if idx < len(recs) else {}
            amap_tags = r.get("tags", [])
            llm_tags = rec.get("tags", [])
            merged = list(dict.fromkeys(amap_tags + llm_tags))

            poi = POIData(
                name=r["name"],
                address=r.get("address"),
                city="苏州",
                tags=merged,
                description=rec.get("reason", ""),
                cost_range=rec.get("cost_range"),
                suitable_for=rec.get("suitable_for", []),
                source_type="amap",
                rating=r.get("rating"),
                phone=r.get("phone"),
                location=r.get("location"),
                verified=True,
            )
            poi_models.append(poi)

        svc = DataService(redis_client=redis)
        await svc.cache_pois("苏州", poi_models)
        await amap.close()
        await llm.close()

        # Verify cache was written
        redis.set.assert_called_once()
        cached = json.loads(redis.set.call_args[0][1])
        assert len(cached) == 5

        # Verify scenic spot fields
        zhuozheng = next(p for p in cached if p["name"] == "拙政园")
        assert zhuozheng["source_type"] == "amap"
        assert zhuozheng["rating"] == 4.8
        assert zhuozheng["description"]  # has reason
        assert len(zhuozheng["suitable_for"]) >= 1
        assert zhuozheng["verified"] is True

        # Verify kids spot fields
        leyuan = next(p for p in cached if p["name"] == "苏州乐园")
        assert "亲子" in leyuan["suitable_for"] or "家人" in leyuan["suitable_for"]


# ---------------------------------------------------------------------------
# Scenario 2: 情侣约会 — Couple date (food + café)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestScenario2CoupleDate:
    """Suzhou couple date: restaurants + cafés."""

    async def test_food_and_cafe_pois(self):
        """Pipeline fetches food + café POIs."""
        amap = _make_mock_amap_service()
        type_codes = {"餐饮": "050000", "咖啡": "050500"}

        raw = await amap.fetch_city_pois("苏州", type_codes, pages=3)
        await amap.close()

        names = [p["name"] for p in raw]
        assert "松鹤楼" in names
        assert "% Arabica" in names
        assert len(raw) == 4  # 2 food + 2 café

    async def test_enrichment_infers_couple_friendly(self):
        """LLM enrichment marks cafés as couple-friendly."""
        amap = _make_mock_amap_service()
        llm = _make_mock_llm_service()
        type_codes = {"咖啡": "050500"}

        raw = await amap.fetch_city_pois("苏州", type_codes, pages=3)
        enrichment_input = [{**p, "city": "苏州"} for p in raw]
        recs = await llm.generate_poi_recommendations(enrichment_input)
        await amap.close()
        await llm.close()

        for rec in recs:
            assert "情侣" in rec["suitable_for"]
            assert "下午茶" in rec["tags"] or "文艺" in rec["tags"]

    async def test_cost_range_populated(self):
        """All POIs have cost_range after enrichment."""
        amap = _make_mock_amap_service()
        llm = _make_mock_llm_service()
        type_codes = {"餐饮": "050000", "咖啡": "050500"}

        raw = await amap.fetch_city_pois("苏州", type_codes, pages=3)
        enrichment_input = [{**p, "city": "苏州"} for p in raw]
        recs = await llm.generate_poi_recommendations(enrichment_input)
        await amap.close()
        await llm.close()

        for rec in recs:
            assert rec["cost_range"] in ("免费", "30以内", "50以内", "50-100", "100+")


# ---------------------------------------------------------------------------
# Scenario 3: 全品类 no-LLM — All categories, mock fallback
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestScenario3AllCategoriesNoLLM:
    """Full Suzhou pipeline with all type codes, no LLM (mock fallback)."""

    async def test_all_types_fetch(self):
        """Pipeline fetches all 6 type codes."""
        amap = _make_mock_amap_service()
        raw = await amap.fetch_city_pois("苏州", AMAP_TYPE_CODES, pages=3)
        await amap.close()

        # 3 scenic + 2 food + 2 café + 2 kids + 0 leisure + 1 museum = 10
        assert len(raw) == 10

    async def test_no_llm_mock_fallback(self):
        """Without LLM API key, recommendations use mock fallback."""
        llm = LLMService(api_key="")  # No key → mock path
        pois = [
            {"name": "拙政园", "amap_type": "风景名胜;公园", "city": "苏州"},
            {"name": "苏州博物馆", "amap_type": "科教文化服务;博物馆", "city": "苏州"},
            {"name": "苏州乐园", "amap_type": "体育休闲服务;游乐场;亲子乐园", "city": "苏州"},
        ]

        recs = await llm.generate_poi_recommendations(pois)
        assert len(recs) == 3

        # Each has required fields
        for rec in recs:
            assert "tags" in rec
            assert "reason" in rec
            assert "suitable_for" in rec
            assert "cost_range" in rec

        # Mock should infer park is free-ish, kids place is 亲子
        park_rec = recs[0]
        museum_rec = recs[1]
        kids_rec = recs[2]
        assert museum_rec["cost_range"] == "免费"  # 博物馆 → 免费
        assert "亲子" in kids_rec["suitable_for"]

    async def test_dedup_across_types(self):
        """Duplicate POIs across type codes are deduplicated."""
        svc = AmapPoiService(api_key="test")

        call_count = 0
        async def mock_search(city, types="", page=1, **kw):
            nonlocal call_count
            call_count += 1
            if page > 1:
                return []
            # Same POI returned under two different type searches
            return [
                _amap_poi("苏州博物馆", "科教文化服务;博物馆", 4.9),
            ]

        svc.search_text = mock_search  # type: ignore[assignment]
        raw = await svc.fetch_city_pois("苏州", {"景点": "110000", "博物馆": "110201"}, pages=3)
        await svc.close()

        names = [p["name"] for p in raw]
        assert names.count("苏州博物馆") == 1

    async def test_poidata_schema_completeness(self):
        """All POIData fields are properly populated end-to-end."""
        amap = _make_mock_amap_service()
        llm = LLMService(api_key="")  # mock

        raw = await amap.fetch_city_pois("苏州", {"景点": "110000"}, pages=3)
        enrichment_input = [{**p, "city": "苏州"} for p in raw]
        recs = await llm.generate_poi_recommendations(enrichment_input)

        for idx, r in enumerate(raw):
            rec = recs[idx]
            poi = POIData(
                name=r["name"],
                address=r.get("address"),
                city="苏州",
                tags=list(dict.fromkeys(r.get("tags", []) + rec.get("tags", []))),
                description=rec.get("reason", ""),
                cost_range=rec.get("cost_range"),
                suitable_for=rec.get("suitable_for", []),
                source_type="amap",
                rating=r.get("rating"),
                phone=r.get("phone"),
                location=r.get("location"),
                verified=True,
            )
            # Required fields present
            assert poi.name
            assert poi.city == "苏州"
            assert poi.source_type == "amap"
            assert poi.verified is True
            # AMAP fields
            assert poi.location
            assert poi.address
            # Enrichment fields
            assert poi.description  # reason
            assert isinstance(poi.suitable_for, list)

        await amap.close()

    async def test_cache_roundtrip(self):
        """POIs survive cache write → read cycle."""
        redis = AsyncMock()

        # Capture what's written to Redis
        stored = {}
        async def mock_set(key, value, **kw):
            stored[key] = value
        async def mock_get(key):
            return stored.get(key)

        redis.set = mock_set
        redis.get = mock_get

        svc = DataService(redis_client=redis)

        pois = [
            POIData(
                name="拙政园", city="苏州", tags=["园林", "拍照"],
                description="经典园林", suitable_for=["情侣"],
                source_type="amap", rating=4.8, location="120.632,31.321",
                cost_range="50-100", verified=True,
            ),
            POIData(
                name="苏州博物馆", city="苏州", tags=["文化", "免费"],
                description="贝聿铭设计", suitable_for=["独自", "情侣"],
                source_type="amap", rating=4.9, location="120.633,31.322",
                cost_range="免费", verified=True,
            ),
        ]

        await svc.cache_pois("苏州", pois)
        retrieved = await svc.get_cached_pois("苏州")

        assert len(retrieved) == 2
        assert retrieved[0]["name"] == "拙政园"
        assert retrieved[0]["rating"] == 4.8
        assert retrieved[1]["cost_range"] == "免费"
