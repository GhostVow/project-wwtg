"""Weather API client: AMAP (高德) integration with mock fallback."""

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class WeatherService:
    """AMAP (高德) weather API client."""

    # MVP city → adcode mapping
    CITY_ADCODES: dict[str, str] = {
        "苏州": "320500",
        "上海": "310000",
        "杭州": "330100",
        "南京": "320100",
        "北京": "110000",
        "广州": "440100",
        "深圳": "440300",
        "成都": "510100",
    }

    def __init__(self, api_key: str = "") -> None:
        self.api_key = api_key
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=httpx.Timeout(10.0))
        return self._client

    async def get_weather(self, city: str) -> dict[str, Any]:
        """Get weekend weather forecast for a city.

        Returns:
            {"city": str, "temperature": str, "condition": str, "suggestion": str}
        """
        if not self.api_key:
            return self._mock_weather(city)

        adcode = self.CITY_ADCODES.get(city)
        if not adcode:
            logger.warning("No adcode for city: %s, using mock", city)
            return self._mock_weather(city)

        try:
            client = await self._get_client()
            resp = await client.get(
                "https://restapi.amap.com/v3/weather/weatherInfo",
                params={
                    "key": self.api_key,
                    "city": adcode,
                    "extensions": "all",  # forecast
                    "output": "JSON",
                },
            )
            resp.raise_for_status()
            data = resp.json()

            if data.get("status") != "1" or not data.get("forecasts"):
                logger.warning("AMAP weather API returned error: %s", data)
                return self._mock_weather(city)

            forecast = data["forecasts"][0]
            casts = forecast.get("casts", [])

            # Get tomorrow's weather (index 1) for weekend planning
            if len(casts) >= 2:
                tomorrow = casts[1]
                condition = tomorrow.get("dayweather", "晴")
                temp_low = tomorrow.get("nighttemp", "10")
                temp_high = tomorrow.get("daytemp", "20")
                temperature = f"{temp_low}-{temp_high}°C"
            else:
                condition = "晴"
                temperature = "10-20°C"

            suggestion = self._weather_suggestion(condition)

            return {
                "city": city,
                "temperature": temperature,
                "condition": condition,
                "suggestion": suggestion,
            }

        except Exception as e:
            logger.error("Weather API failed, using mock: %s", e)
            return self._mock_weather(city)

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    def _weather_suggestion(self, condition: str) -> str:
        """Generate weather-based suggestion."""
        if "雨" in condition:
            return "有雨，建议带伞，优先室内活动"
        if "雪" in condition:
            return "有雪，注意保暖，路面可能湿滑"
        if "阴" in condition or "多云" in condition:
            return "多云，温度适宜，适合户外活动"
        if "晴" in condition:
            return "天气晴好，非常适合户外活动"
        return "建议关注天气变化，灵活安排"

    def _mock_weather(self, city: str) -> dict[str, Any]:
        """Return mock weather data."""
        return {
            "city": city,
            "temperature": "7-15°C",
            "condition": "多云",
            "suggestion": "建议穿薄外套，适合户外活动",
        }
