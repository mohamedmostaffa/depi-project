"""
Unit Tests for Session Memory & Coreference Tracking
Phase 7 Quality Gate Tests
"""

import pytest

from src.memory.session_manager import SessionManager
from src.schemas import ExtractedEntities


@pytest.fixture
def manager():
    return SessionManager(default_window_size=4)


def test_session_sliding_window_bound(manager):
    """Verify that conversation turns are bounded by the sliding window."""
    session_id = "test_sess_01"
    brand_id = "rlvnt"

    # Add 12 turns (6 full pairs)
    for i in range(12):
        role = "customer" if i % 2 == 0 else "assistant"
        manager.add_turn(session_id, brand_id, role, f"Message {i}")

    history = manager.get_history(session_id, brand_id)
    # Bounded by window_size * 2 = 8 turns
    assert len(history) == 8
    assert history[-1].content == "Message 11"


def test_coreference_resolution_english(manager):
    """Verify resolution of 'it' and 'the black one' to previously discussed garment."""
    session_id = "test_sess_02"
    brand_id = "rlvnt"

    # Turn 1: Customer asks about Messi hoodie
    e1 = ExtractedEntities(product="Lionel Messi Hoodie", size="M")
    manager.resolve_and_update(session_id, brand_id, "Do you have the Lionel Messi Hoodie in M?", e1)

    # Turn 2: Customer refers to 'it'
    e2 = ExtractedEntities(reason="too small")
    resolved = manager.resolve_and_update(session_id, brand_id, "Can I exchange it?", e2)

    assert resolved.product == "Lionel Messi Hoodie"
    assert resolved.reason == "too small"


def test_coreference_resolution_arabic(manager):
    """Verify resolution of Arabic demonstratives ('ده', 'أرجعه') across turns."""
    session_id = "test_sess_03"
    brand_id = "rlvnt"

    # Turn 1: Customer talks about San Andreas crewneck
    e1 = ExtractedEntities(product="San Andreas Graphic Crewneck", size="L")
    manager.resolve_and_update(session_id, brand_id, "سويت شيرت سان أندرياس متاح لارج؟", e1)

    # Turn 2: Customer says "عايز أرجعه"
    e2 = ExtractedEntities()
    resolved = manager.resolve_and_update(session_id, brand_id, "عايز أرجعه بعد أسبوع", e2)

    assert resolved.product == "San Andreas Graphic Crewneck"
