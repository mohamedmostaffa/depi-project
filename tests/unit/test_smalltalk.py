from datetime import date

import pytest

from src.agents.orchestrator import AgentOrchestrator
from src.agents.smalltalk import is_small_talk
from src.schemas import Intent
from src.tools.dispatcher import ToolDispatcher
from src.tools.escalation_tool import EscalationTool


@pytest.mark.parametrize("msg", [
    "السلام عليكم", "السلام عليكم ورحمة الله وبركاته", "سلام عليكم", "اهلا يا باشا", "أهلاً", "مساء الخير", "هااااي",
    "hi", "Hello!", "hiiii 👋", "hey there", "good morning", "thanks a lot", "thank you so much", "شكرا ليك",
    "تسلم", "bye", "مع السلامة",
])
def test_pure_greetings_are_small_talk(msg):
    assert is_small_talk(msg)


@pytest.mark.parametrize("msg", [
    "", "   ", "hi where is my order RLVNT-1001", "السلام عليكم عايز ارجع الهودي", "thanks, but I want to return it",
    "What is your return policy?", "hello what are your shipping fees", "عايز ابدل المقاس", "this", "high",
])
def test_messages_with_a_real_request_are_not_small_talk(msg):
    assert not is_small_talk(msg)


@pytest.fixture
def orch(tmp_path):
    dispatcher = ToolDispatcher(escalation_tool=EscalationTool(str(tmp_path / "escalations.jsonl")))
    return AgentOrchestrator(dispatcher=dispatcher, audit_file=str(tmp_path / "a.jsonl"))


def test_greeting_skips_retrieval_and_tools(orch):
    r = orch.handle_turn("rlvnt", "s1", "السلام عليكم", today=date(2026, 11, 20))
    t = r.transparency
    assert t.detected_intent == Intent.SMALL_TALK
    assert t.retrieved_sources == [] and t.tools_executed == [] and t.policy_decision is None
    assert t.generator.startswith("llm:") and r.reply.startswith("TEST_LLM_REPLY")


def test_greeting_prompt_has_no_brand_data(orch, monkeypatch):
    seen = []
    from src.llm.client import LLMClient
    monkeypatch.setattr(LLMClient, "generate", lambda self, p, temperature=0.3: seen.append(p) or "ok")
    orch.handle_turn("rlvnt", "s2", "hi", today=date(2026, 11, 20))
    assert "AUTHORITATIVE BRAND REFERENCE DATA" not in seen[0] and "VERIFIED TOOL RESULTS" not in seen[0]
    assert "AI assistant" in seen[0]           # first turn: discloses it is an AI


def test_greeting_plus_request_still_uses_the_normal_pipeline(orch):
    r = orch.handle_turn("rlvnt", "s3", "hi, where is my order RLVNT-1001?", today=date(2026, 11, 20))
    assert r.transparency.detected_intent == Intent.ORDER_STATUS
    assert [x.tool_name for x in r.transparency.tools_executed] == ["get_order_status"]


def test_safety_check_runs_before_small_talk(orch):
    r = orch.handle_turn("rlvnt", "s4", "hi I got a rash from the hoodie", today=date(2026, 11, 20))
    assert r.transparency.is_escalated
