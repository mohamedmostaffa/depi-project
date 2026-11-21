"""
Unit Tests for Jinja2 Layered Prompts & Brand Personality
Phase 6 Quality Gate Tests
"""

import pytest

from src.prompts.template_manager import PromptTemplateManager


@pytest.fixture
def manager():
    return PromptTemplateManager()


@pytest.fixture
def rlvnt_brand():
    return PromptTemplateManager.load_brand_config("rlvnt")


def test_system_base_rendering(manager, rlvnt_brand):
    """Verify system_base.j2 compiles and embeds RLVNT streetwear identity."""
    rendered = manager.render("system_base.j2", {"brand": rlvnt_brand, "max_sentences": 4})
    assert "RLVNT" in rendered
    assert "contemporary streetwear" in rendered.lower()
    assert "Zero Hallucination" in rendered
    assert "Egyptian Arabic" in rendered


def test_intent_understanding_rendering(manager):
    """Verify intent_understanding.j2 renders cleanly with recent history."""
    rendered = manager.render(
        "intent_understanding.j2",
        {
            "today": "2026-11-20",
            "history": [{"role": "customer", "content": "Hi"}, {"role": "assistant", "content": "Hey! Welcome to RLVNT"}],
            "customer_message": "Do you have the Messi hoodie in L?",
        },
    )
    assert "INTENT TAXONOMY" in rendered
    assert "Messi hoodie" in rendered
    assert "<customer_message>" in rendered


def test_grounded_generation_rendering(manager, rlvnt_brand):
    """Verify grounded_generation.j2 embeds XML-delimited context and deterministic decision."""
    context = {
        "brand": rlvnt_brand,
        "context_text": "[S1: policies.pdf] Return window is 14 days.",
        "decision": {
            "decision": "eligible",
            "reason_code": "ELIGIBLE",
            "reason_text": "Item is within 14-day window.",
            "missing_fields": [],
        },
        "tool_results": "Order RLVNT-1001 status: DELIVERED",
        "history": [],
        "customer_message": "Can I exchange my hoodie?",
        "max_sentences": 3,
    }
    rendered = manager.render("grounded_generation.j2", context)
    assert "<context>" in rendered
    assert "<decision>" in rendered
    assert "<tool_results>" in rendered
    assert "DETERMINISTIC BUSINESS POLICY DECISION" in rendered
