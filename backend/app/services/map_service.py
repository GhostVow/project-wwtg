"""Map service: AMAP (高德) geocoding and navigation links."""

import logging
from typing import Any
from urllib.parse import quote

import httpx

logger = logging.getLogger(__name__)


class MapService:
    """AMAP (高德) map service for geocoding and navigation links."""

    def __init__(self, api_key: str = "") -> None:
        self.api_key = api_key
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=httpx.Timeout(10.0))
        return self._client

    async def geocode(self, address: str, city: str) -> dict[str, Any] | None:
        """Geocode an address to lat/lng.

        Returns:
            {"lat": float, "lng": float, "formatted_address": str} or None
        """
        if not self.api_key:
            return self._mock_geocode(address, city)

        try:
            client = await self._get_client()
            resp = await client.get(
                "https://restapi.amap.com/v3/geocode/geo",
                params={
                    "key": self.api_key,
                    "address": address,
                    "city": city,
                    "output": "JSON",
                },
            )
            resp.raise_for_status()
            data = resp.json()

            if data.get("status") != "1" or not data.get("geocodes"):
                return None

            geo = data["geocodes"][0]
            location = geo.get("location", "")
            if "," not in location:
                return None

            lng_str, lat_str = location.split(",")
            return {
                "lat": float(lat_str),
                "lng": float(lng_str),
                "formatted_address": geo.get("formatted_address", address),
            }
        except Exception as e:
            logger.error("Geocode failed for %s: %s", address, e)
            return None

    def generate_nav_link(self, name: str, lat: float, lng: float) -> str:
        """Generate AMAP navigation deep link."""
        encoded_name = quote(name)
        return f"https://uri.amap.com/marker?position={lng},{lat}&name={encoded_name}"

    async def calculate_walking_distance(
        self, origin: tuple[float, float], destination: tuple[float, float]
    ) -> dict[str, Any]:
        """Calculate walking distance/time between two points.

        Args:
            origin: (lng, lat)
            destination: (lng, lat)

        Returns:
            {"distance": str, "duration": str}
        """
        if not self.api_key:
            return {"distance": "500m", "duration": "约6分钟"}

        try:
            client = await self._get_client()
            resp = await client.get(
                "https://restapi.amap.com/v3/direction/walking",
                params={
                    "key": self.api_key,
                    "origin": f"{origin[0]},{origin[1]}",
                    "destination": f"{destination[0]},{destination[1]}",
                },
            )
            resp.raise_for_status()
            data = resp.json()

            if data.get("status") != "1":
                return {"distance": "未知", "duration": "未知"}

            route = data.get("route", {})
            paths = route.get("paths", [])
            if not paths:
                return {"distance": "未知", "duration": "未知"}

            path = paths[0]
            distance_m = int(path.get("distance", 0))
            duration_s = int(path.get("duration", 0))

            if distance_m >= 1000:
                dist_str = f"{distance_m / 1000:.1f}km"
            else:
                dist_str = f"{distance_m}m"

            duration_min = max(1, duration_s // 60)
            return {"distance": dist_str, "duration": f"约{duration_min}分钟"}

        except Exception as e:
            logger.error("Walking distance calc failed: %s", e)
            return {"distance": "未知", "duration": "未知"}

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    def _mock_geocode(self, address: str, city: str) -> dict[str, Any]:
        """Return mock geocode data."""
        # Some known locations for mock
        known: dict[str, tuple[float, float]] = {
            "双塔市集": (31.316, 120.636),
            "苏州博物馆": (31.322, 120.628),
            "耦园": (31.318, 120.643),
            "平江路": (31.320, 120.635),
        }
        for name, (lat, lng) in known.items():
            if name in address:
                return {"lat": lat, "lng": lng, "formatted_address": f"{city}{address}"}
        return {"lat": 31.30, "lng": 120.60, "formatted_address": f"{city}{address}"}
