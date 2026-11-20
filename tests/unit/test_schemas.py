"""
Unit Tests for BrandMind Pydantic Schemas & Interface Contracts
Phase 1 Foundation Validation
"""

from datetime import date
import pytest
from pydantic import ValidationError

from src.schemas import (
    CustomerTurnInput,
    ConversationTurn,
    UnderstandingResult,
    ExtractedEntities,
    Language,
    Dialect,
    Intent,
    Sentiment,
    Decision,
    EligibilityResult,
    ProductItem,
    TurnResponse,
    TransparencyData,
    ActionType,
)


def test_customer_turn_input_valid():
    """Verify CustomerTurnInput succeeds with valid inputs."""
    data = CustomerTurnInput(
        brand_id="rlvnt",
        session_id="sess_12345",
        message="Can I exchange my hoodie for a different size?",
        history=[
            ConversationTurn(role="customer", content="Hello"),
            ConversationTurn(role="assistant", content="Welcome to RLVNT!"),
        ],
    )
    assert data.brand_id == "rlvnt"
    assert data.session_id == "sess_12345"
    assert len(data.history) == 2


def test_customer_turn_input_invalid():
    """Verify CustomerTurnInput fails when required fields are missing or empty."""
    with pytest.raises(ValidationError):
        CustomerTurnInput(brand_id="", session_id="sess_1", message="")


def test_understanding_result_structure():
    """Verify UnderstandingResult handles all 9 intents and structured entities."""
    for intent in Intent:
        result = UnderstandingResult(
            language=Language.AR,
            dialect=Dialect.EGYPTIAN,
            intent=intent,
            entities=ExtractedEntities(
                product="Lionel Messi Hoodie",
                size="L",
                color="Black",
                purchase_date=date(2026, 11, 10),
            ),
            sentiment=Sentiment.NEUTRAL,
            confidence=0.98,
        )
        assert result.intent == intent
        assert result.entities.product == "Lionel Messi Hoodie"
        assert result.entities.size == "L"


def test_eligibility_result_contract():
    """Verify EligibilityResult complies with deterministic rule engine requirements."""
    res = EligibilityResult(
        decision=Decision.NOT_ELIGIBLE,
        reason_code="OUTSIDE_WINDOW",
        reason_text="Return window exceeded 14 days from delivery.",
        missing_fields=[],
        rule_trace=["Check Completeness: PASS", "Check Window: FAIL (18 > 14)"],
    )
    assert res.decision == Decision.NOT_ELIGIBLE
    assert res.reason_code == "OUTSIDE_WINDOW"
    assert len(res.rule_trace) == 2


def test_turn_response_serialization():
    """Verify TurnResponse correctly embeds transparency data and serializes to dict/json."""
    transparency = TransparencyData(
        detected_intent=Intent.EXCHANGE,
        confidence=0.95,
        language=Language.EN,
        dialect=Dialect.EN,
        retrieved_sources=[{"source_file": "policies.pdf", "source_page": 5}],
        tools_executed=[],
        policy_decision=EligibilityResult(
            decision=Decision.ELIGIBLE,
            reason_code="ELIGIBLE",
            reason_text="Item is eligible for size exchange.",
        ),
        is_escalated=False,
        latency_ms=125.4,
    )

    response = TurnResponse(
        reply="Your hoodie is eligible for an exchange within our 14-day window.",
        brand_id="rlvnt",
        session_id="sess_12345",
        action_type=ActionType.ANSWER,
        transparency=transparency,
    )

    dumped = response.model_dump()
    assert dumped["brand_id"] == "rlvnt"
    assert dumped["transparency"]["detected_intent"] == "exchange"
    assert dumped["transparency"]["policy_decision"]["decision"] == "eligible"
