"""Tests for AnalyticsService."""

import json
import tempfile
from pathlib import Path

import pytest

from app.services.analytics import AnalyticsService


@pytest.fixture
def analytics_service(tmp_path: Path) -> AnalyticsService:
    return AnalyticsService(log_file=tmp_path / "test_analytics.jsonl")


@pytest.mark.asyncio
async def test_track_writes_to_file(analytics_service: AnalyticsService) -> None:
    """track() should append a JSON line to the log file."""
    await analytics_service.track("test_event", session_id="sess-1", properties={"key": "val"})
    content = analytics_service._log_file.read_text()
    lines = [l for l in content.strip().split("\n") if l]
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["event"] == "test_event"
    assert record["session_id"] == "sess-1"
    assert record["properties"]["key"] == "val"


@pytest.mark.asyncio
async def test_event_format_has_required_fields(analytics_service: AnalyticsService) -> None:
    """Each event must have timestamp, event, session_id, properties."""
    await analytics_service.track("session_start", session_id="s2")
    content = analytics_service._log_file.read_text()
    record = json.loads(content.strip())
    for field in ("timestamp", "event", "session_id", "properties"):
        assert field in record, f"Missing required field: {field}"
    # timestamp should be ISO format
    assert "T" in record["timestamp"]


@pytest.mark.asyncio
async def test_multiple_events_append(analytics_service: AnalyticsService) -> None:
    """Multiple events should result in multiple lines."""
    await analytics_service.track("event_a", session_id="s1")
    await analytics_service.track("event_b", session_id="s1")
    lines = [l for l in analytics_service._log_file.read_text().strip().split("\n") if l]
    assert len(lines) == 2
