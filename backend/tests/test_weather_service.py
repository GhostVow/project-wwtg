"""Tests for Weather service."""

import pytest

from app.services.weather_service import WeatherService


@pytest.fixture
def weather_no_key() -> WeatherService:
    return WeatherService(api_key="")


class TestWeatherService:

    @pytest.mark.asyncio
    async def test_mock_weather(self, weather_no_key: WeatherService) -> None:
        result = await weather_no_key.get_weather("苏州")
        assert result["city"] == "苏州"
        assert "temperature" in result
        assert "condition" in result
        assert "suggestion" in result

    @pytest.mark.asyncio
    async def test_mock_weather_unknown_city(self, weather_no_key: WeatherService) -> None:
        result = await weather_no_key.get_weather("火星")
        assert result["city"] == "火星"

    def test_city_adcodes(self) -> None:
        assert "苏州" in WeatherService.CITY_ADCODES
        assert "上海" in WeatherService.CITY_ADCODES
        assert "杭州" in WeatherService.CITY_ADCODES
        assert WeatherService.CITY_ADCODES["苏州"] == "320500"

    def test_weather_suggestion(self, weather_no_key: WeatherService) -> None:
        assert "伞" in weather_no_key._weather_suggestion("小雨")
        assert "户外" in weather_no_key._weather_suggestion("晴")
        assert "户外" in weather_no_key._weather_suggestion("多云")
