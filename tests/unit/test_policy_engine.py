"""
Comprehensive Unit Tests for Deterministic Policy Engine
Phase 9 Critical Quality Gate — 100% Deterministic Pass Requirement
"""

from datetime import date, timedelta
import pytest

from src.policies.engine import PolicyEngine
from src.schemas import Decision


@pytest.fixture
def rlvnt_policy():
    return {
        "policy_id": "POL-RET-01",
        "brand_id": "rlvnt",
        "allowed_days": 14,
        "non_returnable_categories": ["Clearance", "Altered Garments"],
        "acceptable_conditions": ["unworn", "unwashed", "tags attached"],
    }


@pytest.fixture
def catalog():
    return {
        "RLVNT-HD-01": {"name": "Lionel Messi Hoodie", "category": "Hoodies"},
        "RLVNT-CLR-01": {"name": "Archive Tee", "category": "Clearance"},
    }


@pytest.fixture
def orders():
    return {
        "RLVNT-1001": {
            "order_id": "RLVNT-1001",
            "brand_id": "rlvnt",
            "product_id": "RLVNT-HD-01",
            "delivery_date": "2026-11-10",
            "order_date": "2026-11-08",
        },
        "OTHER-9999": {
            "order_id": "OTHER-9999",
            "brand_id": "other_brand",
            "product_id": "OTHER-PROD",
            "delivery_date": "2026-11-10",
        },
    }


def test_exact_boundary_day_14(rlvnt_policy, catalog):
    """Test Case: Exactly on the boundary (day 14) -> ELIGIBLE."""
    today = date(2026, 11, 20)
    purchase_date = today - timedelta(days=14)

    facts = {
        "product_id": "RLVNT-HD-01",
        "purchase_date": purchase_date,
        "condition": "unworn, tags attached",
    }
    result = PolicyEngine.evaluate(facts, rlvnt_policy, today, catalog)
    assert result.decision == Decision.ELIGIBLE
    assert result.reason_code == "ELIGIBLE_RETURN"
    assert any("Elapsed 14 days is within 14 days window" in trace for trace in result.rule_trace)


def test_one_day_outside_boundary_day_15(rlvnt_policy, catalog):
    """Test Case: Exactly one day outside the window (day 15) -> NOT_ELIGIBLE."""
    today = date(2026, 11, 20)
    purchase_date = today - timedelta(days=15)

    facts = {
        "product_id": "RLVNT-HD-01",
        "purchase_date": purchase_date,
        "condition": "unworn, tags attached",
    }
    result = PolicyEngine.evaluate(facts, rlvnt_policy, today, catalog)
    assert result.decision == Decision.NOT_ELIGIBLE
    assert result.reason_code == "OUTSIDE_WINDOW"
    assert "Return window exceeded" in result.reason_text


def test_day_zero(rlvnt_policy, catalog):
    """Test Case: Purchased on the exact current day (day 0) -> ELIGIBLE."""
    today = date(2026, 11, 20)
    facts = {
        "product_id": "RLVNT-HD-01",
        "purchase_date": today,
        "condition": "unworn",
    }
    result = PolicyEngine.evaluate(facts, rlvnt_policy, today, catalog)
    assert result.decision == Decision.ELIGIBLE


def test_future_purchase_date(rlvnt_policy, catalog):
    """Test Case: Purchase date is in the future -> NOT_ELIGIBLE (INVALID_PURCHASE_DATE)."""
    today = date(2026, 11, 20)
    future_date = today + timedelta(days=3)

    facts = {
        "product_id": "RLVNT-HD-01",
        "purchase_date": future_date,
        "condition": "unworn",
    }
    result = PolicyEngine.evaluate(facts, rlvnt_policy, today, catalog)
    assert result.decision == Decision.NOT_ELIGIBLE
    assert result.reason_code == "INVALID_PURCHASE_DATE"


def test_missing_purchase_date(rlvnt_policy, catalog):
    """Test Case: Purchase date is missing and order cannot resolve it -> NEEDS_INFO."""
    today = date(2026, 11, 20)
    facts = {
        "product_id": "RLVNT-HD-01",
        "condition": "unworn",
    }
    result = PolicyEngine.evaluate(facts, rlvnt_policy, today, catalog)
    assert result.decision == Decision.NEEDS_INFO
    assert "purchase_date" in result.missing_fields


def test_missing_condition_when_not_defective(rlvnt_policy, catalog):
    """Test Case: Condition is missing and item is not defective -> NEEDS_INFO."""
    today = date(2026, 11, 20)
    facts = {
        "product_id": "RLVNT-HD-01",
        "purchase_date": today - timedelta(days=5),
    }
    result = PolicyEngine.evaluate(facts, rlvnt_policy, today, catalog)
    assert result.decision == Decision.NEEDS_INFO
    assert "item_condition" in result.missing_fields


def test_missing_product_and_order_id(rlvnt_policy):
    """Test Case: Neither product nor order id supplied -> NEEDS_INFO."""
    today = date(2026, 11, 20)
    facts = {"condition": "unworn"}
    result = PolicyEngine.evaluate(facts, rlvnt_policy, today)
    assert result.decision == Decision.NEEDS_INFO
    assert "product_or_order_id" in result.missing_fields


def test_excluded_category_clearance(rlvnt_policy, catalog):
    """Test Case: Final sale clearance item -> NOT_ELIGIBLE (EXCLUDED_CATEGORY)."""
    today = date(2026, 11, 20)
    facts = {
        "product_id": "RLVNT-CLR-01",
        "purchase_date": today - timedelta(days=3),
        "condition": "unworn, tags attached",
    }
    result = PolicyEngine.evaluate(facts, rlvnt_policy, today, catalog)
    assert result.decision == Decision.NOT_ELIGIBLE
    assert result.reason_code == "EXCLUDED_CATEGORY"
    assert "final sale" in result.reason_text


def test_bad_condition_washed_or_worn(rlvnt_policy, catalog):
    """Test Case: Garment has been washed or tags removed -> NOT_ELIGIBLE (BAD_CONDITION)."""
    today = date(2026, 11, 20)
    for bad_cond in ["washed and worn once", "perfume smell", "missing tag", "stained collar"]:
        facts = {
            "product_id": "RLVNT-HD-01",
            "purchase_date": today - timedelta(days=4),
            "condition": bad_cond,
        }
        result = PolicyEngine.evaluate(facts, rlvnt_policy, today, catalog)
        assert result.decision == Decision.NOT_ELIGIBLE
        assert result.reason_code == "BAD_CONDITION"


def test_defective_item_exception(rlvnt_policy, catalog):
    """Test Case: Defective or damaged item override -> ELIGIBLE (100% brand coverage)."""
    today = date(2026, 11, 20)
    facts = {
        "product_id": "RLVNT-HD-01",
        "purchase_date": today - timedelta(days=20),  # Even outside normal window
        "reason": "Arrived with manufacturing defect in zipper",
        "is_defective": True,
    }
    result = PolicyEngine.evaluate(facts, rlvnt_policy, today, catalog)
    assert result.decision == Decision.ELIGIBLE
    assert result.reason_code == "DEFECTIVE_OR_WRONG_ITEM"
    assert "100% covered by RLVNT" in result.reason_text


def test_exchange_request_type(rlvnt_policy, catalog):
    """Test Case: Request type exchange notes customer-covered return shipping."""
    today = date(2026, 11, 20)
    facts = {
        "request_type": "exchange",
        "product_id": "RLVNT-HD-01",
        "purchase_date": today - timedelta(days=7),
        "condition": "unworn with tags",
        "reason": "need a smaller size",
    }
    result = PolicyEngine.evaluate(facts, rlvnt_policy, today, catalog)
    assert result.decision == Decision.ELIGIBLE
    assert result.reason_code == "ELIGIBLE_EXCHANGE"
    assert "standard exchange return courier fee" in result.reason_text


def test_order_lookup_resolution(rlvnt_policy, catalog, orders):
    """Test Case: Facts provide order_id, engine auto-resolves delivery date and product."""
    today = date(2026, 11, 20)
    facts = {
        "order_id": "RLVNT-1001",
        "condition": "unworn, original packaging",
    }
    result = PolicyEngine.evaluate(facts, rlvnt_policy, today, catalog, orders)
    assert result.decision == Decision.ELIGIBLE
    assert "Rule 1 [Order Lookup]: Verified order 'RLVNT-1001'" in result.rule_trace


def test_wrong_brand_isolation(rlvnt_policy, catalog, orders):
    """Test Case: Order belongs to a different brand -> NOT_ELIGIBLE (WRONG_BRAND)."""
    today = date(2026, 11, 20)
    facts = {
        "order_id": "OTHER-9999",
        "condition": "unworn",
    }
    result = PolicyEngine.evaluate(facts, rlvnt_policy, today, catalog, orders)
    assert result.decision == Decision.NOT_ELIGIBLE
    assert result.reason_code == "WRONG_BRAND"


def test_unknown_order_not_found(rlvnt_policy, catalog, orders):
    """Test Case: Non-existent order id -> NEEDS_INFO (ORDER_NOT_FOUND)."""
    today = date(2026, 11, 20)
    facts = {
        "order_id": "NON-EXISTENT-ORDER",
        "condition": "unworn",
    }
    result = PolicyEngine.evaluate(facts, rlvnt_policy, today, catalog, orders)
    assert result.decision == Decision.NEEDS_INFO
    assert result.reason_code == "ORDER_NOT_FOUND"


def test_all_reason_texts_non_empty(rlvnt_policy, catalog):
    """Verify that every decision branch outputs non-empty reason_text and rule_trace."""
    today = date(2026, 11, 20)
    test_cases = [
        {"product_id": "RLVNT-HD-01", "purchase_date": today, "condition": "unworn"},
        {"product_id": "RLVNT-HD-01", "purchase_date": today - timedelta(days=20), "condition": "unworn"},
        {"product_id": "RLVNT-CLR-01", "purchase_date": today, "condition": "unworn"},
        {"product_id": "RLVNT-HD-01", "purchase_date": today, "condition": "washed"},
    ]
    for facts in test_cases:
        res = PolicyEngine.evaluate(facts, rlvnt_policy, today, catalog)
        assert res.reason_text.strip() != "", "reason_text must never be empty"
        assert len(res.rule_trace) > 0, "rule_trace must never be empty"
