"""Smoke tests: verify core services can be imported and instantiated."""

from app.services.llm_service import LLMService
from app.services.chat_service import ChatService
from app.services.plan_service import PlanService
from app.services.data_service import DataService
from app.services.weather_service import WeatherService
from app.services.map_service import MapService


class TestServiceImports:
    """Ensure all core services import without errors."""

    def test_llm_service_instantiation(self) -> None:
        svc = LLMService(api_key="test")
        assert svc is not None
        # Verify _get_client doesn't raise NameError
        client = svc._get_client()
        assert client is not None

    def test_plan_service_instantiation(self) -> None:
        llm = LLMService(api_key="test")
        svc = PlanService(llm=llm)
        assert svc is not None

    def test_chat_service_instantiation(self) -> None:
        svc = ChatService()
        assert svc is not None

    def test_data_service_instantiation(self) -> None:
        svc = DataService()
        assert svc is not None

    def test_weather_service_instantiation(self) -> None:
        svc = WeatherService()
        assert svc is not None

    def test_map_service_instantiation(self) -> None:
        svc = MapService()
        assert svc is not None
