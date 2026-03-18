"""Analytics endpoints: generic frontend event tracking."""

from typing import Any, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.services.analytics import analytics

router = APIRouter()


class TrackEventRequest(BaseModel):
    """Request body for tracking an analytics event."""

    event: str
    session_id: str = ""
    properties: dict[str, Any] = Field(default_factory=dict)


@router.post("/track")
async def track_event(req: TrackEventRequest) -> dict[str, str]:
    """Track a generic analytics event from the frontend.

    Accepts arbitrary events with optional session_id and properties.
    Used by the mini program to report navigation clicks, UI interactions, etc.
    """
    await analytics.track(
        event=req.event,
        session_id=req.session_id,
        properties=req.properties,
    )
    return {"status": "ok"}
