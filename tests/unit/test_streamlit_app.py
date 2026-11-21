"""
BrandMind — Automated Tests for Streamlit UI Integration
Verifies that app/streamlit_app.py helper functions and turn execution operate properly.
"""

from app.streamlit_app import execute_chat_turn, is_arabic_text


def test_is_arabic_text():
    assert is_arabic_text("مرحباً بيك في RLVNT") is True
    assert is_arabic_text("Hello, what is your return window?") is False
    assert is_arabic_text("10 days ago") is False
    assert is_arabic_text("الأوردر رقم RLVNT-1001") is True


def test_execute_chat_turn_in_process_fallback():
    turn = execute_chat_turn("What is RLVNT's return window?", backend_mode="In-Process")
    assert "reply" in turn
    assert "transparency" in turn
    assert turn["source"] == "In-Process Agent"
    assert "14" in turn["reply"]
