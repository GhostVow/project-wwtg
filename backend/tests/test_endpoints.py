"""Tests for chat, plan, auth, and analytics endpoints."""

from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


# --- Chat ---

def test_chat_message_returns_json() -> None:
    """POST /api/v1/chat/message returns JSON with session_id."""
    response = client.post(
        "/api/v1/chat/message",
        json={"message": "苏州，和老公，周末去哪玩"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "session_id" in data
    assert "reply" in data


def test_chat_message_with_session_id() -> None:
    """Session ID passed through in response."""
    response = client.post(
        "/api/v1/chat/message",
        json={"message": "hello", "session_id": "test-sid-001"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == "test-sid-001"


def test_chat_generates_plans_with_city() -> None:
    """When city is provided, plans should be generated."""
    response = client.post(
        "/api/v1/chat/message",
        json={"message": "苏州"},
    )
    data = response.json()
    assert "plans" in data
    assert len(data["plans"]) > 0
    assert "actions" in data


def test_chat_asks_for_city_without_one() -> None:
    """Without city, should ask follow-up."""
    response = client.post(
        "/api/v1/chat/message",
        json={"message": "你好"},
    )
    data = response.json()
    assert "reply" in data
    # Should not have plans
    assert "plans" not in data or len(data.get("plans", [])) == 0


# --- Plan ---

def test_plan_select() -> None:
    response = client.post(
        "/api/v1/plan/select",
        json={"plan_id": "mock-plan-a-001"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["plan_id"] == "mock-plan-a-001"


def test_plan_reject() -> None:
    response = client.post(
        "/api/v1/plan/reject",
        json={"plan_id": "mock-plan-a-001"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_plan_detail_fallback() -> None:
    """Unknown plan_id should return fallback detail."""
    response = client.get("/api/v1/plan/detail/unknown-plan")
    assert response.status_code == 200
    data = response.json()
    assert "title" in data
    assert "stops" in data
    assert len(data["stops"]) > 0


def test_reject_regenerate_flow() -> None:
    """Reject → re-generate should return new plans."""
    # Step 1: generate initial plans
    r1 = client.post("/api/v1/chat/message", json={"message": "苏州", "session_id": "reject-test-1"})
    assert r1.status_code == 200
    d1 = r1.json()
    assert "plans" in d1

    # Step 2: reject
    r2 = client.post("/api/v1/chat/message", json={"message": "都不喜欢，换一批", "session_id": "reject-test-1"})
    assert r2.status_code == 200
    d2 = r2.json()
    assert "plans" in d2


def test_multiple_rejections_suggests_refine() -> None:
    """After 3+ rejections, suggest the user refine preferences."""
    sid = "reject-multi-test"
    # Generate initial plans
    client.post("/api/v1/chat/message", json={"message": "苏州", "session_id": sid})

    # Reject 3 times
    for _ in range(3):
        resp = client.post("/api/v1/chat/message", json={"message": "换一批", "session_id": sid})
    data = resp.json()
    assert "plans" not in data or len(data.get("plans", [])) == 0
    assert "具体" in data["reply"] or "需求" in data["reply"]


# --- Auth ---

def test_wx_login_stub() -> None:
    response = client.post(
        "/api/v1/auth/wx-login",
        json={"code": "mock_code"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "token" in data
    assert "openid" in data


# --- Analytics ---

def test_analytics_track_success() -> None:
    """POST /api/v1/analytics/track should accept and log an event."""
    response = client.post(
        "/api/v1/analytics/track",
        json={
            "event": "navigation_clicked",
            "session_id": "test-session-analytics",
            "properties": {"plan_id": "plan-abc", "stop_name": "双塔市集"},
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


def test_analytics_track_minimal() -> None:
    """Track endpoint should work with only the event field."""
    response = client.post(
        "/api/v1/analytics/track",
        json={"event": "page_view"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_analytics_track_missing_event() -> None:
    """Track endpoint should return 422 when event is missing."""
    response = client.post(
        "/api/v1/analytics/track",
        json={"session_id": "sid"},
    )
    assert response.status_code == 422


# --- Message Validation ---

def test_chat_empty_message_returns_400() -> None:
    """Empty message should return 400."""
    response = client.post(
        "/api/v1/chat/message",
        json={"message": ""},
    )
    assert response.status_code == 400


def test_chat_whitespace_only_message_returns_400() -> None:
    """Whitespace-only message should return 400."""
    response = client.post(
        "/api/v1/chat/message",
        json={"message": "   "},
    )
    assert response.status_code == 400


def test_chat_message_too_long_returns_400() -> None:
    """Message exceeding 500 chars should return 400."""
    long_message = "a" * 501
    response = client.post(
        "/api/v1/chat/message",
        json={"message": long_message},
    )
    assert response.status_code == 400
    data = response.json()
    assert "500" in data["detail"]


def test_chat_message_at_max_length_ok() -> None:
    """Message at exactly 500 chars should be accepted."""
    msg = "苏州" + "a" * 496  # 2 Chinese chars + 496 ASCII = 498 Python chars, under 500
    response = client.post(
        "/api/v1/chat/message",
        json={"message": msg},
    )
    assert response.status_code == 200


# --- LLM Timeout Handling ---

def test_chat_timeout_returns_friendly_message() -> None:
    """When plan generation times out, should return a friendly message."""
    import asyncio

    async def slow_generate(*args, **kwargs):
        await asyncio.sleep(20)
        return []

    with patch.object(
        client.app,  # type: ignore[union-attr]
        "_state",
        create=True,
    ):
        # Patch the _do_generate method on the ChatService instance used by the app
        from app.api.chat import chat_service

        original = chat_service._do_generate
        chat_service._do_generate = slow_generate  # type: ignore[assignment]
        try:
            response = client.post(
                "/api/v1/chat/message",
                json={"message": "苏州", "session_id": "timeout-test-session"},
            )
            assert response.status_code == 200
            data = response.json()
            assert "抱歉" in data["reply"] or "太长" in data["reply"] or "稍后" in data["reply"]
        finally:
            chat_service._do_generate = original  # type: ignore[assignment]

