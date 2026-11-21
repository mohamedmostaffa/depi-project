"""
Integration Tests for Central Agent Orchestrator
Phase 12 Quality Gate Tests
"""

from datetime import date
from pathlib import Path
import pytest

from src.agents.orchestrator import AgentOrchestrator
from src.schemas import ActionType, Intent


@pytest.fixture
def orchestrator():
    return AgentOrchestrator(audit_file="results/test_audit.jsonl")


def test_orchestrator_general_returns_inquiry(orchestrator):
    """Verify general return policy inquiry returns grounded policy explanation."""
    resp = orchestrator.handle_turn(
        brand_id="rlvnt",
        session_id="sess_orch_01",
        message="What is your return policy?",
        today=date(2026, 11, 20),
    )
    assert resp.action_type == ActionType.ANSWER
    assert resp.transparency.detected_intent == Intent.RETURNS
    assert "14" in resp.reply
    assert resp.transparency.latency_ms > 0


def test_orchestrator_order_status_tool_flow(orchestrator):
    """Verify order status inquiry executes order tool and returns status."""
    resp = orchestrator.handle_turn(
        brand_id="rlvnt",
        session_id="sess_orch_02",
        message="Where is my order RLVNT-1001?",
        today=date(2026, 11, 20),
    )
    assert resp.action_type == ActionType.ANSWER
    assert resp.transparency.detected_intent == Intent.ORDER_STATUS
    assert len(resp.transparency.tools_executed) == 1
    assert resp.transparency.tools_executed[0].tool_name == "get_order_status"
    assert resp.transparency.tools_executed[0].success is True
    assert "DELIVERED" in resp.reply


def test_orchestrator_exchange_decision_flow(orchestrator):
    """Verify exchange request triggers deterministic policy engine and returns ELIGIBLE."""
    today = date(2026, 11, 20)
    resp = orchestrator.handle_turn(
        brand_id="rlvnt",
        session_id="sess_orch_03",
        message="عايز أبدل مقاس الهودي في أوردر RLVNT-1001 علشان واسع، وهو مش ملبوس وبالتيكت",
        today=today,
    )
    assert resp.action_type == ActionType.ANSWER
    assert resp.transparency.detected_intent == Intent.EXCHANGE
    assert resp.transparency.policy_decision is not None
    assert resp.transparency.policy_decision.decision == "eligible"
    assert "مؤهل" in resp.reply


def test_audit_trace_file_written(orchestrator):
    """Verify full JSONL execution audit trace is persisted."""
    audit_path = Path("results/test_audit.jsonl")
    assert audit_path.exists()
    assert audit_path.stat().st_size > 0
