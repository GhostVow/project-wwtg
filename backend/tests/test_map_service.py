"""Tests for Map service."""

import pytest

from app.services.map_service import MapService


@pytest.fixture
def map_no_key() -> MapService:
    return MapService(api_key="")


class TestMapService:

    def test_generate_nav_link(self, map_no_key: MapService) -> None:
        link = map_no_key.generate_nav_link("双塔市集", 31.316, 120.636)
        assert "uri.amap.com/marker" in link
        assert "position=120.636,31.316" in link
        assert "%E5%8F%8C%E5%A1%94%E5%B8%82%E9%9B%86" in link

    def test_generate_nav_link_special_chars(self, map_no_key: MapService) -> None:
        link = map_no_key.generate_nav_link("猫的天空之城", 31.0, 120.0)
        assert "uri.amap.com" in link
        assert "position=120.0,31.0" in link

    @pytest.mark.asyncio
    async def test_mock_geocode(self, map_no_key: MapService) -> None:
        result = await map_no_key.geocode("双塔市集", "苏州")
        assert result is not None
        assert "lat" in result
        assert "lng" in result
        assert result["lat"] == 31.316

    @pytest.mark.asyncio
    async def test_mock_geocode_unknown(self, map_no_key: MapService) -> None:
        result = await map_no_key.geocode("随便一个地方", "苏州")
        assert result is not None
        assert "lat" in result

    @pytest.mark.asyncio
    async def test_walking_distance_mock(self, map_no_key: MapService) -> None:
        result = await map_no_key.calculate_walking_distance(
            (120.636, 31.316), (120.643, 31.318)
        )
        assert "distance" in result
        assert "duration" in result
