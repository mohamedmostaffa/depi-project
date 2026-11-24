"""
Unit Tests for Agent Tools & Tool Dispatcher
Phase 10 Quality Gate Tests
"""

from datetime import date
import pytest

from src.tools.dispatcher import ToolDispatcher
from src.tools.catalog_tool import CatalogTool
from src.tools.order_tool import OrderTool
from src.tools.return_tool import ReturnTool
from src.tools.escalation_tool import EscalationTool


@pytest.fixture
def dispatcher(tmp_path):
    return ToolDispatcher(escalation_tool=EscalationTool(str(tmp_path / "escalations.jsonl")))


def test_search_products_tool(dispatcher):
    """Verify search_products retrieves matching verified items."""
    res = dispatcher.execute_tool(
        "search_products",
        {"query": "Messi", "brand_id": "rlvnt"}
    )
    assert res.success is True
    assert len(res.data) > 0
    assert "Messi" in res.data[0]["name"]
    assert res.data[0]["brand_id"] == "rlvnt"


def test_search_products_filter_category_and_size(dispatcher):
    """Verify search_products respects category and size filters."""
    res = dispatcher.execute_tool(
        "search_products",
        {"category": "Hoodies", "size": "XL", "brand_id": "rlvnt"}
    )
    assert res.success is True
    assert len(res.data) > 0
    for item in res.data:
        assert item["category"] == "Hoodies"
        assert "XL" in item["sizes"]


def test_get_order_status_valid(dispatcher):
    """Verify get_order_status retrieves an existing order."""
    res = dispatcher.execute_tool(
        "get_order_status",
        {"order_id": "RLVNT-1001", "brand_id": "rlvnt"}
    )
    assert res.success is True
    assert res.data["order_id"] == "RLVNT-1001"
    assert res.data["delivery_status"] == "DELIVERED"
    assert res.data["currency"] == "EGP"


def test_get_order_status_not_found(dispatcher):
    """Verify get_order_status fails gracefully for non-existent orders."""
    res = dispatcher.execute_tool(
        "get_order_status",
        {"order_id": "NON-EXISTENT", "brand_id": "rlvnt"}
    )
    assert res.success is False
    assert "not found" in res.error.lower()


def test_check_return_eligibility_tool(dispatcher):
    """Verify check_return_eligibility executes policy engine via tool dispatcher."""
    today = date(2026, 11, 20)
    facts = {
        "order_id": "RLVNT-1001",
        "condition": "unworn, tags attached",
        "request_type": "return",
    }
    res = dispatcher.execute_tool(
        "check_return_eligibility",
        {"facts": facts, "brand_id": "rlvnt", "today": today}
    )
    assert res.success is True
    assert res.data["decision"] == "eligible"
    assert res.data["reason_code"] == "ELIGIBLE_RETURN"


def test_escalate_to_human_tool(dispatcher):
    """Verify escalate_to_human persists escalation record."""
    res = dispatcher.execute_tool(
        "escalate_to_human",
        {
            "session_id": "test_sess_esc",
            "brand_id": "rlvnt",
            "reason": "Customer dispute regarding damaged shipment",
            "customer_message": "Item arrived with a broken zipper",
        }
    )
    assert res.success is True
    assert res.data["session_id"] == "test_sess_esc"
    assert res.data["status"] == "PENDING_HUMAN_REVIEW"
