"""
Unit Tests for Understanding & NLP Layer
Phase 8 Quality Gate Tests
"""

from datetime import date, timedelta
import pytest

from src.agents.understanding import UnderstandingService
from src.schemas import Dialect, Intent, Language, Sentiment


def test_arabic_digit_normalization():
    """Verify Eastern Arabic-Indic digits are correctly mapped to Western ASCII."""
    raw = "طلب رقم RLVNT-١٠٠٢ من ١٠ أيام مقاس L"
    norm = UnderstandingService.normalize_text(raw)
    assert "RLVNT-1002" in norm
    assert "من 10 أيام" in norm


def test_relative_date_resolution():
    """Verify relative date phrases compute deterministic calendar dates via code."""
    today = date(2026, 11, 20)

    # 10 days ago
    d1, text1 = UnderstandingService.resolve_relative_dates("I bought this 10 days ago", today)
    assert d1 == date(2026, 11, 10)
    assert text1 == "10 days ago"

    # من ١٠ أيام (with Arabic digits)
    d2, text2 = UnderstandingService.resolve_relative_dates("اشتريت الهودي من ١٠ أيام", today)
    assert d2 == date(2026, 11, 10)

    # 2 weeks ago
    d3, _ = UnderstandingService.resolve_relative_dates("من أسبوعين تقريباً", today)
    assert d3 == date(2026, 11, 6)


def test_dialect_detection():
    """Verify detection of English, Egyptian Arabic, MSA, and Franco-Arabic."""
    lang1, dia1 = UnderstandingService.detect_language_and_dialect("Can I exchange this hoodie?")
    assert lang1 == Language.EN
    assert dia1 == Dialect.EN

    lang2, dia2 = UnderstandingService.detect_language_and_dialect("عايز أبدل المقاس علشان واسع أوي كده")
    assert lang2 == Language.AR
    assert dia2 == Dialect.EGYPTIAN

    lang3, dia3 = UnderstandingService.detect_language_and_dialect("هل يمكنني استبدال هذا المقاس؟")
    assert lang3 == Language.AR
    assert dia3 == Dialect.MSA

    lang4, dia4 = UnderstandingService.detect_language_and_dialect("3ayez a3mel return ll hoodie")
    assert lang4 == Language.AR
    assert dia4 == Dialect.FRANCO


def test_hard_safety_escalation_triggers():
    """Verify that human requests, medical, and legal complaints trigger escalation."""
    triggers = [
        "I want to talk to a human agent right now",
        "عايز أكلم بني آدم في خدمة العملاء",
        "I got a bad allergic rash from this material",
        "هرفع قضية في حماية المستهلك وهكلم محامي",
        "This is a total fraud and scam, chargeback incoming",
    ]
    for t in triggers:
        triggered, reason = UnderstandingService.check_hard_safety_triggers(t)
        assert triggered is True, f"Failed to trigger on: {t}"
        assert reason is not None


def test_intent_and_entity_extraction():
    """Verify end-to-end understanding output matching Pydantic schema."""
    today = date(2026, 11, 20)
    msg = "عايز أبدل هودي ميسي مقاس L في أوردر RLVNT-1001 عشان واسع"

    result = UnderstandingService.analyze(msg, today)
    assert result.language == Language.AR
    assert result.dialect == Dialect.EGYPTIAN
    assert result.intent == Intent.EXCHANGE
    assert result.entities.product == "Lionel Messi 100% Cotton Signature Hoodie"
    assert result.entities.size == "L"
    assert result.entities.order_id == "RLVNT-1001"
    assert result.entities.reason == "size too large"
    assert result.requires_human is False
