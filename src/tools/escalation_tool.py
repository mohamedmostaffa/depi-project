"""
BrandMind — Tool 4: escalate_to_human
Logs structured escalation tickets for human support review and returns honest hand-off record.
"""

import json
from pathlib import Path
from typing import Optional
from datetime import datetime, timezone

from src.schemas import EscalationRecord


class EscalationTool:
    def __init__(self, log_path: str = "results/escalations.jsonl"):
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def escalate(
        self,
        session_id: str,
        brand_id: str,
        reason: str,
        customer_message: str,
        conversation_summary: Optional[str] = None,
    ) -> EscalationRecord:
        """Creates and persists an escalation record."""
        record = EscalationRecord(
            session_id=session_id,
            brand_id=brand_id,
            reason=reason,
            customer_message=customer_message,
            conversation_summary=conversation_summary,
            escalated_at=datetime.now(timezone.utc),
            status="PENDING_HUMAN_REVIEW",
        )

        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(record.model_dump_json() + "\n")

        return record
