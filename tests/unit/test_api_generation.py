import pytest
from fastapi import HTTPException

from src.agents.orchestrator import GeminiGenerationError
from src.api import routes


def test_chat_endpoint_returns_503_without_customer_reply(monkeypatch):
    observed = {}
    monkeypatch.setattr(
        routes.orchestrator,
        "handle_turn",
        lambda **kwargs: (observed.update(kwargs), (_ for _ in ()).throw(GeminiGenerationError()))[1],
    )
    with pytest.raises(HTTPException) as raised:
        routes.chat_turn(routes.ChatRequest(session_id="caller-value", message="Hello"), session={"session_hash": "server-session"})
    assert raised.value.status_code == 503
    assert "No AI response was generated" in raised.value.detail
    assert observed["session_id"] == "server-session"


def test_return_submission_message_is_generated_by_gemini(monkeypatch):
    monkeypatch.setattr(routes.orchestrator, "generate_customer_message", lambda *_args, **_kwargs: "Gemini return reply")
    response = routes.submit_return(routes.ReturnSubmitRequest(
        order_id="RLVNT-1001",
        product_id="RLVNT-HD-01",
        reason="Size issue",
        condition="Unworn",
        pickup_address="Test address",
    ))
    assert response.message == "Gemini return reply"


def test_return_submission_returns_503_when_gemini_fails(monkeypatch):
    monkeypatch.setattr(
        routes.orchestrator,
        "generate_customer_message",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(GeminiGenerationError()),
    )
    with pytest.raises(HTTPException) as raised:
        routes.submit_return(routes.ReturnSubmitRequest(
            order_id="RLVNT-1001",
            product_id="RLVNT-HD-01",
            reason="Size issue",
            condition="Unworn",
            pickup_address="Test address",
        ))
    assert raised.value.status_code == 503
    assert "No customer response was generated" in raised.value.detail
