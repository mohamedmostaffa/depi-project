"""
Integration Tests for Central Agent Orchestrator
Phase 12 Quality Gate Tests
"""

from datetime import date
from pathlib import Path
import pytest

from src.agents.orchestrator import AgentOrchestrator
from src.schemas import ActionType, Intent
from src.tools.dispatcher import ToolDispatcher
from src.tools.escalation_tool import EscalationTool


@pytest.fixture
def orchestrator(tmp_path):
    dispatcher = ToolDispatcher(escalation_tool=EscalationTool(str(tmp_path / "escalations.jsonl")))
    return AgentOrchestrator(dispatcher=dispatcher, audit_file=str(tmp_path / "test_audit.jsonl"))


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
    assert resp.transparency.generator.startswith("llm:")   # reply wording comes from the LLM, so it is not string-matched
    assert resp.transparency.retrieved_sources
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
    assert resp.transparency.tools_executed[0].data["status"] or resp.transparency.tools_executed[0].data["delivery_status"]


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
    assert "eligible" in resp.reply.lower()   # the stub LLM echoes the policy outcome that was put in the prompt


def test_audit_trace_file_written(orchestrator):
    """Verify full JSONL execution audit trace is persisted."""
    orchestrator.handle_turn(
        brand_id="rlvnt",
        session_id="audit-trace-test",
        message="What is your return policy?",
        today=date(2026, 11, 20),
    )
    audit_path = orchestrator.audit_path
    assert audit_path.exists()
    assert audit_path.stat().st_size > 0
