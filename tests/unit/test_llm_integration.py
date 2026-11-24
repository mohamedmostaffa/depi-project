"""Orchestrator <-> LLM wiring, with a fake LLM (no network). Offline canned replies are disabled by design."""
from datetime import date

import pytest

from src.agents.orchestrator import AgentOrchestrator, GeminiGenerationError
from src.schemas import ActionType
from src.tools.dispatcher import ToolDispatcher
from src.tools.escalation_tool import EscalationTool

TODAY = date(2026, 11, 20)
EXCHANGE_MSG = "عايز أبدل مقاس الهودي في أوردر RLVNT-1001 علشان واسع، وهو مش ملبوس وبالتيكت"


class FakeLive:
    provider, label = "google", "google:fake-model"

    def __init__(self, reply="FAKE_LLM_REPLY", error=None):
        self.reply, self.error, self.prompts = reply, error, []

    def generate(self, prompt, temperature=0.3):
        self.prompts.append(prompt)
        if self.error:
            raise RuntimeError(self.error)
        return self.reply


def make(live, tmp_path):
    dispatcher = ToolDispatcher(escalation_tool=EscalationTool(str(tmp_path / "escalations.jsonl")))
    o = AgentOrchestrator(dispatcher=dispatcher, audit_file=str(tmp_path / "audit.jsonl"))
    o.live_llm = live
    return o


def test_reply_comes_from_the_llm_and_is_labelled(tmp_path):
    r = make(FakeLive(), tmp_path).handle_turn("rlvnt", "s", "What is your return policy?", today=TODAY)
    assert r.reply == "FAKE_LLM_REPLY" and r.transparency.generator == "llm:google:fake-model"


def test_policy_decision_is_put_in_the_prompt_not_decided_by_the_llm(tmp_path):
    live = FakeLive()
    r = make(live, tmp_path).handle_turn("rlvnt", "s", EXCHANGE_MSG, today=TODAY)
    prompt = live.prompts[0]
    assert r.transparency.policy_decision.decision == "eligible"
    assert "Outcome: eligible" in prompt and "You MUST explain this exact decision" in prompt
    assert "<customer_message>" in prompt            # customer text is delimited as data (G3)
    assert "AI assistant" in prompt                  # first turn: AI disclosure instruction


def test_tool_results_reach_the_prompt(tmp_path):
    live = FakeLive()
    make(live, tmp_path).handle_turn("rlvnt", "s", "Where is my order RLVNT-1001?", today=TODAY)
    assert "<tool_results>" in live.prompts[0] and "RLVNT-1001" in live.prompts[0]


def test_conversation_history_is_sent_on_later_turns(tmp_path):
    live = FakeLive()
    o = make(live, tmp_path)
    o.handle_turn("rlvnt", "s", "Where is my order RLVNT-1001?", today=TODAY)
    o.handle_turn("rlvnt", "s", "What is your return policy?", today=TODAY)
    assert "Where is my order RLVNT-1001?" in live.prompts[1] and "ongoing conversation" in live.prompts[1]


def test_llm_failure_raises_instead_of_sending_a_canned_reply(tmp_path):
    with pytest.raises(GeminiGenerationError):
        make(FakeLive(error="429 rate limit"), tmp_path).handle_turn("rlvnt", "s", "What is your return policy?", today=TODAY)


def test_audit_records_are_not_added_to_prompt_context(tmp_path):
    audit = tmp_path / "audit.jsonl"
    audit.write_text('{"assistant_reply":"SECRET_OLD_AUDIT_REPLY"}\\n', encoding="utf-8")
    live = FakeLive()
    make(live, tmp_path).handle_turn("rlvnt", "fresh-session", "What is your return policy?", today=TODAY)
    assert "SECRET_OLD_AUDIT_REPLY" not in live.prompts[0]


def test_new_session_has_no_other_session_history(tmp_path):
    live = FakeLive()
    orchestrator = make(live, tmp_path)
    orchestrator.handle_turn("rlvnt", "old-session", "SECRET_OLD_SESSION_MESSAGE", today=TODAY)
    live.prompts.clear()
    orchestrator.handle_turn("rlvnt", "new-session", "What is your return policy?", today=TODAY)
    assert "SECRET_OLD_SESSION_MESSAGE" not in live.prompts[0]


def test_audit_trace_is_still_appended_after_success(tmp_path):
    audit = tmp_path / "audit.jsonl"
    orchestrator = make(FakeLive(), tmp_path)
    orchestrator.audit_path = audit
    orchestrator.handle_turn("rlvnt", "s", "What is your return policy?", today=TODAY)
    assert "FAKE_LLM_REPLY" in audit.read_text(encoding="utf-8")


def test_escalation_is_deterministic_but_gemini_words_the_message(tmp_path):
    live = FakeLive(reply="GEMINI_HANDOFF")
    r = make(live, tmp_path).handle_turn("rlvnt", "s", "I got a rash from the hoodie, I will sue you", today=TODAY)
    assert r.action_type == ActionType.ESCALATE and r.transparency.is_escalated
    assert r.transparency.tools_executed[0].tool_name == "escalate_to_human"   # logged by code, not by the LLM
    assert r.reply == "GEMINI_HANDOFF" and r.transparency.generator == "llm:google:fake-model"
    assert "ESCALATION REASON" in live.prompts[0]


def test_escalation_handoff_still_happens_but_no_reply_when_gemini_is_down(tmp_path):
    with pytest.raises(GeminiGenerationError) as raised:
        make(FakeLive(error="503"), tmp_path).handle_turn("rlvnt", "s", "عايز اكلم حد من خدمة العملا", today=TODAY)
    assert raised.value.escalation_succeeded


def test_no_forced_greeting_or_auto_emoji_in_grounded_template(tmp_path):
    live = FakeLive()
    make(live, tmp_path).handle_turn("rlvnt", "s", "What is your return policy?", today=TODAY)
    prompt = live.prompts[0]
    assert "Do not use automatic emojis, greetings, slang, or canned introductions" in prompt
    assert "يا صاحبي" in prompt  # listed only as vocabulary to avoid, not as response language
    assert "Do not add emojis unless the customer used one" in prompt
