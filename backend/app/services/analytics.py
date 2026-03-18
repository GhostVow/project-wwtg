"""Simple event tracking for MVP. Logs to file + stdout.

TODO(M5): migrate to proper analytics (PostHog/Mixpanel).
"""

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Default log directory (relative to project root)
_LOG_DIR = Path(os.environ.get("ANALYTICS_LOG_DIR", "logs"))
_LOG_FILE = _LOG_DIR / "analytics.jsonl"


class AnalyticsService:
    """File-based event tracking for MVP."""

    def __init__(self, log_file: Path | str | None = None) -> None:
        self._log_file = Path(log_file) if log_file else _LOG_FILE
        self._log_file.parent.mkdir(parents=True, exist_ok=True)

    async def track(
        self,
        event: str,
        session_id: str = "",
        properties: dict[str, Any] | None = None,
    ) -> None:
        """Track an event.

        Events:
        - session_start: new session created
        - message_sent: user sent a message
        - intent_parsed: intent extraction completed
        - plans_generated: plans were generated (with count)
        - plan_selected: user selected a plan (with plan_id)
        - plan_rejected: user rejected plans (with rejection_count)
        - plan_detail_viewed: user viewed plan detail
        - error: an error occurred
        """
        record: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": event,
            "session_id": session_id,
            "properties": properties or {},
        }
        line = json.dumps(record, ensure_ascii=False)
        logger.info("analytics | %s", line)
        try:
            with open(self._log_file, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except OSError as exc:
            logger.warning("Failed to write analytics event: %s", exc)


# Module-level singleton
analytics = AnalyticsService()
