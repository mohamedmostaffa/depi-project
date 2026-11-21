"""
BrandMind — FastAPI Router
REST API endpoints for product search, order lookup, policy validation, and chat.
"""

from datetime import date
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from src.schemas import (
    CustomerTurnInput,
    Decision,
    EligibilityResult,
    OrderItem,
    ProductItem,
    TurnResponse,
    EscalationRecord,
)
from src.tools.catalog_tool import CatalogTool
from src.tools.order_tool import OrderTool
from src.tools.return_tool import ReturnTool
from src.tools.escalation_tool import EscalationTool

router = APIRouter()

catalog_tool = CatalogTool()
order_tool = OrderTool()
return_tool = ReturnTool()
escalation_tool = EscalationTool()


# ==============================================================================
# Request/Response Models for Endpoints
# ==============================================================================

class ReturnCheckRequest(BaseModel):
    brand_id: str = "rlvnt"
    product_id: Optional[str] = None
    order_id: Optional[str] = None
    condition: Optional[str] = None
    reason: Optional[str] = None
    request_type: str = "return"
    purchase_date: Optional[date] = None
    today: Optional[date] = None


class ReturnSubmitRequest(BaseModel):
    brand_id: str = "rlvnt"
    order_id: str
    product_id: str
    reason: str
    condition: str
    pickup_address: str


class ReturnSubmitResponse(BaseModel):
    status: str
    return_request_id: str
    brand_id: str
    message: str


class EscalateRequest(BaseModel):
    session_id: str
    brand_id: str = "rlvnt"
    reason: str
    customer_message: str
    summary: Optional[str] = None


# ==============================================================================
# Endpoint Implementations
# ==============================================================================

@router.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "BrandMind AI Customer Agent API",
        "brand": "rlvnt",
        "version": "0.1.0",
    }


@router.get("/products/{product_id}", response_model=ProductItem)
def get_product(product_id: str, brand_id: str = Query(default="rlvnt")):
    item = catalog_tool.get_product(product_id, brand_id)
    if not item:
        raise HTTPException(status_code=404, detail=f"Product '{product_id}' not found for brand '{brand_id}'")
    return item


@router.get("/products", response_model=List[ProductItem])
def search_products(
    query: Optional[str] = None,
    category: Optional[str] = None,
    size: Optional[str] = None,
    color: Optional[str] = None,
    max_price: Optional[float] = None,
    brand_id: str = Query(default="rlvnt"),
):
    return catalog_tool.search_products(
        query=query,
        category=category,
        size=size,
        color=color,
        max_price=max_price,
        brand_id=brand_id,
    )


@router.get("/orders/{order_id}", response_model=OrderItem)
def get_order(order_id: str, brand_id: str = Query(default="rlvnt")):
    order = order_tool.get_order_status(order_id, brand_id)
    if not order:
        raise HTTPException(status_code=404, detail=f"Order '{order_id}' not found for brand '{brand_id}'")
    return order


@router.post("/returns/check", response_model=EligibilityResult)
def check_return(req: ReturnCheckRequest):
    facts = {
        "product_id": req.product_id,
        "order_id": req.order_id,
        "condition": req.condition,
        "reason": req.reason,
        "request_type": req.request_type,
        "purchase_date": req.purchase_date,
    }
    return return_tool.check_eligibility(facts=facts, brand_id=req.brand_id, today=req.today)


@router.post("/returns/request", response_model=ReturnSubmitResponse)
def submit_return(req: ReturnSubmitRequest):
    # Simulated return submission
    import uuid
    req_id = f"RET-{uuid.uuid4().hex[:8].upper()}"
    return ReturnSubmitResponse(
        status="SUBMITTED",
        return_request_id=req_id,
        brand_id=req.brand_id,
        message="Simulated return request received. A courier will be assigned upon approval.",
    )


@router.post("/escalate", response_model=EscalationRecord)
def escalate(req: EscalateRequest):
    return escalation_tool.escalate(
        session_id=req.session_id,
        brand_id=req.brand_id,
        reason=req.reason,
        customer_message=req.customer_message,
        conversation_summary=req.summary,
    )
