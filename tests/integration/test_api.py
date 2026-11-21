"""
Integration Tests for FastAPI Microservice Endpoints
Phase 11 Quality Gate Tests
"""

from datetime import date, timedelta
import pytest
from fastapi.testclient import TestClient

from src.api.app import app


@pytest.fixture
def client():
    return TestClient(app)


def test_health_endpoint(client):
    """Verify /health returns 200 and correct status metadata."""
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["brand"] == "rlvnt"


def test_get_product_success(client):
    """Verify /products/{product_id} returns existing verified item."""
    resp = client.get("/products/RLVNT-HD-01")
    assert resp.status_code == 200
    data = resp.json()
    assert data["product_id"] == "RLVNT-HD-01"
    assert "Messi" in data["name"]
    assert data["price"] == 1650.0


def test_get_product_not_found(client):
    """Verify /products/{product_id} returns 404 for non-existent item."""
    resp = client.get("/products/NON-EXISTENT-SKU")
    assert resp.status_code == 404


def test_get_order_status_success(client):
    """Verify /orders/{order_id} returns order details."""
    resp = client.get("/orders/RLVNT-1001")
    assert resp.status_code == 200
    data = resp.json()
    assert data["order_id"] == "RLVNT-1001"
    assert data["delivery_status"] == "DELIVERED"
    assert data["currency"] == "EGP"


def test_get_order_not_found(client):
    """Verify /orders/{order_id} returns 404 for invalid order."""
    resp = client.get("/orders/INVALID-ORDER-999")
    assert resp.status_code == 404


def test_returns_check_endpoint(client):
    """Verify POST /returns/check invokes deterministic policy engine."""
    today = date(2026, 11, 20)
    payload = {
        "brand_id": "rlvnt",
        "order_id": "RLVNT-1001",
        "condition": "unworn, tags attached",
        "request_type": "return",
        "today": today.isoformat(),
    }
    resp = client.post("/returns/check", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["decision"] == "eligible"
    assert data["reason_code"] == "ELIGIBLE_RETURN"


def test_returns_submit_endpoint(client):
    """Verify POST /returns/request generates simulated return ID."""
    payload = {
        "brand_id": "rlvnt",
        "order_id": "RLVNT-1001",
        "product_id": "RLVNT-HD-01",
        "reason": "Size too large",
        "condition": "unworn",
        "pickup_address": "Nasr City, Cairo, Egypt",
    }
    resp = client.post("/returns/request", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "SUBMITTED"
    assert data["return_request_id"].startswith("RET-")


def test_escalate_endpoint(client):
    """Verify POST /escalate creates escalation record."""
    payload = {
        "session_id": "sess_test_api",
        "brand_id": "rlvnt",
        "reason": "Customer angry about delivery delay",
        "customer_message": "Where is my package? It is late!",
    }
    resp = client.post("/escalate", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "PENDING_HUMAN_REVIEW"
    assert data["session_id"] == "sess_test_api"
