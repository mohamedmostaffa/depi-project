"""
BrandMind — FastAPI Router
REST API endpoints for product search, order lookup, policy validation, and chat.
"""

from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
import base64
import binascii
import os
import re
import threading
import logging
import shutil
import time
import uuid
import secrets
import hashlib
import hmac
from pathlib import Path
from fastapi import APIRouter, HTTPException, Query, Header, Depends, Request, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from src.schemas import (
    CustomerTurnInput,
    Decision,
    EligibilityResult,
    OrderItem,
    ProductItem,
    TurnResponse,
)
from src.tools.catalog_tool import CatalogTool
from src.tools.order_tool import OrderTool
from src.tools.return_tool import ReturnTool
from src.tools.escalation_tool import EscalationTool
from src.agents.orchestrator import AgentOrchestrator, GeminiGenerationError
from src.conversations.store import ConversationStore

router = APIRouter()
logger = logging.getLogger(__name__)

catalog_tool = CatalogTool()
order_tool = OrderTool()
return_tool = ReturnTool()
escalation_tool = EscalationTool()
orchestrator = AgentOrchestrator()
conversation_store = ConversationStore()
_ATTACHMENTS_DIR = Path(os.getenv("BRANDMIND_ATTACHMENTS_DIR", "results/attachments"))
_ALLOWED_ATTACHMENT_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp", "application/pdf"}
_conversation_locks: Dict[str, threading.RLock] = {}
_locks_guard = threading.Lock()
_DEV_ADMIN_TOKEN = secrets.token_urlsafe(32)
_ADMIN_LOGIN_ATTEMPTS: Dict[str, List[float]] = {}
_ADMIN_LOGIN_LOCK = threading.Lock()


def _conversation_lock(conversation_id: str):
    with _locks_guard:
        return _conversation_locks.setdefault(conversation_id, threading.RLock())


def _purge_expired_customer_ignored():
    expired_ids = conversation_store.purge_expired_archived()
    for conversation_id in expired_ids:
        shutil.rmtree(_ATTACHMENTS_DIR / conversation_id, ignore_errors=True)


def _save_message_attachments(conversation_id: str, attachments: List[Any]):
    if not attachments:
        return []
    decoded = []
    total_size = 0
    extensions = {"image/jpeg": ".jpg", "image/png": ".png", "image/gif": ".gif",
                  "image/webp": ".webp", "application/pdf": ".pdf"}
    for item in attachments:
        if item.media_type not in _ALLOWED_ATTACHMENT_TYPES:
            raise HTTPException(status_code=415, detail="Attach a JPG, PNG, GIF, WEBP image, or PDF.")
        try:
            raw = base64.b64decode(item.data, validate=True)
        except (binascii.Error, ValueError):
            raise HTTPException(status_code=400, detail=f"Invalid attachment data for {item.name}.")
        if not raw or len(raw) > 5 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="Each attachment must be smaller than 5 MB.")
        total_size += len(raw)
        if total_size > 10 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="Attachments must total 10 MB or less.")
        decoded.append((item, raw))
    directory = _ATTACHMENTS_DIR / conversation_id
    directory.mkdir(parents=True, exist_ok=True)
    result = []
    for item, raw in decoded:
        attachment_id = uuid.uuid4().hex
        safe_name = item.name.replace("\\", "/").rsplit("/", 1)[-1]
        destination = directory / f"{attachment_id}{extensions[item.media_type]}"
        destination.write_bytes(raw)
        result.append({"id": attachment_id, "name": safe_name, "media_type": item.media_type,
                       "size": len(raw), "url": f"/conversations/{conversation_id}/attachments/{attachment_id}"})
    return result


def _expected_admin_token():
    expected = os.getenv("BRANDMIND_ADMIN_TOKEN")
    if not expected:
        if os.getenv("ENVIRONMENT", "development").lower() == "production":
            return None
        expected = _DEV_ADMIN_TOKEN
    return expected


def require_admin(authorization: Optional[str] = Header(default=None)):
    expected = _expected_admin_token()
    if expected is None:
        raise HTTPException(status_code=503, detail="Admin authentication is not configured")
    if authorization != f"Bearer {expected}":
        raise HTTPException(status_code=401, detail="Admin sign-in required")
    return True


CUSTOMER_COOKIE = "brandmind_customer_session"


def customer_session_settings():
    days = max(1, min(int(os.getenv("BRANDMIND_CUSTOMER_SESSION_TTL_DAYS", "30")), 365))
    production = os.getenv("ENVIRONMENT", "development").lower() == "production"
    same_site = os.getenv("BRANDMIND_CUSTOMER_COOKIE_SAMESITE", "lax").lower()
    if same_site not in {"lax", "strict", "none"}:
        raise HTTPException(status_code=500, detail="Invalid customer cookie SameSite setting")
    secure = production or same_site == "none"
    return days, same_site, secure


def _allowed_origins():
    raw = os.getenv("BRANDMIND_CORS_ORIGINS")
    if raw is not None:
        return [value.strip().rstrip("/") for value in raw.split(",") if value.strip()]
    if os.getenv("ENVIRONMENT", "development").lower() == "production":
        return []
    return ["http://localhost:3000", "http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:5174", "http://127.0.0.1:5174", "http://localhost:8501"]


def _check_customer_origin(request: Request):
    origin = request.headers.get("origin", "").rstrip("/")
    if not origin or origin not in _allowed_origins() or request.headers.get("sec-fetch-site") == "cross-site":
        raise HTTPException(status_code=403, detail="Request origin is not allowed")


def _customer_session(request: Request):
    raw = request.cookies.get(CUSTOMER_COOKIE)
    if not raw or len(raw) > 256:
        raise HTTPException(status_code=401, detail="Customer session required")
    session_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    session = conversation_store.get_customer_session(session_hash)
    if not session or datetime.fromisoformat(session["expires_at"]) <= datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Customer session required")
    return session


def require_customer_session(request: Request):
    return _customer_session(request)


def require_customer_write(request: Request, x_csrf_token: Optional[str] = Header(default=None)):
    _check_customer_origin(request)
    session = _customer_session(request)
    if not x_csrf_token or not hmac.compare_digest(x_csrf_token, session["csrf_token"]):
        raise HTTPException(status_code=403, detail="CSRF validation failed")
    return session


def require_owned_conversation(conversation_id: str, session=Depends(require_customer_session)):
    if not conversation_store.belongs_to_customer_session(conversation_id, session["session_hash"]):
        raise HTTPException(status_code=404, detail="Conversation not found")
    return session


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


class ChatRequest(BaseModel):
    brand_id: str = "rlvnt"
    session_id: Optional[str] = None
    message: str
    today: Optional[date] = None


class ConversationCreateRequest(BaseModel):
    brand_id: str = "rlvnt"
    customer_name: str = "Guest"
    email: str = ""
    order_id: str = ""


class AdminLoginRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=254)
    password: str = Field(..., min_length=1, max_length=256)


class AttachmentRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    media_type: str = Field(..., max_length=100)
    data: str = Field(..., min_length=1, max_length=7 * 1024 * 1024)


class MessageRequest(BaseModel):
    content: str = Field(default="", max_length=4000)
    attachments: List[AttachmentRequest] = Field(default_factory=list, max_length=4)


class HandoffRequest(BaseModel):
    assigned_to: str = "Support Team"


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


@router.post("/chat", response_model=TurnResponse)
def chat_turn(req: ChatRequest, session=Depends(require_customer_write)):
    """Processes customer turn through the complete BrandMind agent orchestration pipeline."""
    try:
        response = orchestrator.handle_turn(
            brand_id=req.brand_id,
            session_id=session["session_hash"],
            message=req.message,
            today=req.today,
        )
        return response
    except GeminiGenerationError:
        raise HTTPException(
            status_code=503,
            detail="Gemini 2.5 Flash is temporarily unavailable. No AI response was generated.",
        )
    except Exception:
        logger.exception("Chat orchestration failed; no customer response was generated.")
        raise HTTPException(status_code=500, detail="The AI request could not be completed. No response was generated.")


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
    import uuid
    req_id = f"RET-{uuid.uuid4().hex[:8].upper()}"
    try:
        message = orchestrator.generate_customer_message(
            "return_submission.j2",
            {
                "brand": orchestrator.prompt_manager.load_brand_config(req.brand_id),
                "status": "SUBMITTED (simulated; pending review)",
                "return_request_id": req_id,
                "order_id": req.order_id,
                "product_id": req.product_id,
                "reason": req.reason,
                "condition": req.condition,
            },
        )
    except GeminiGenerationError:
        raise HTTPException(
            status_code=503,
            detail="Gemini 2.5 Flash is temporarily unavailable. No customer response was generated.",
        )
    return ReturnSubmitResponse(
        status="SUBMITTED",
        return_request_id=req_id,
        brand_id=req.brand_id,
        message=message,
    )


@router.post("/escalate")
def escalate(req: EscalateRequest, session=Depends(require_customer_write)):
    # This legacy endpoint has no conversation record to own. Use an event ID,
    # not the customer session digest, in its persistent escalation log.
    record = escalation_tool.escalate(
        session_id=f"api-escalation-{uuid.uuid4().hex}",
        brand_id=req.brand_id,
        reason=req.reason,
        customer_message=req.customer_message,
        conversation_summary=req.summary,
    )
    return {"status": record.status, "brand_id": record.brand_id, "reason": record.reason,
            "escalated_at": record.escalated_at}


# Customer guest sessions use a random cookie secret; only its SHA-256 digest is stored.
@router.post("/customer/session")
def create_or_get_customer_session(request: Request, response: Response):
    _check_customer_origin(request)
    days, same_site, secure = customer_session_settings()
    raw = request.cookies.get(CUSTOMER_COOKIE)
    session_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest() if raw and len(raw) <= 256 else ""
    session = conversation_store.get_customer_session(session_hash) if session_hash else None
    now = datetime.now(timezone.utc)
    if not session or datetime.fromisoformat(session["expires_at"]) <= now:
        raw = secrets.token_urlsafe(32)
        session_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        csrf_token = secrets.token_urlsafe(32)
        expires = now + timedelta(days=days)
        conversation_store.create_customer_session(session_hash, csrf_token, now.isoformat(), expires.isoformat())
        session = {"csrf_token": csrf_token, "expires_at": expires.isoformat()}
    else:
        expires = datetime.fromisoformat(session["expires_at"])
    response.set_cookie(CUSTOMER_COOKIE, raw, max_age=days * 86400, expires=expires,
                        httponly=True, secure=secure, samesite=same_site, path="/api/v1")
    return {"csrf_token": session["csrf_token"], "expires_at": session["expires_at"]}


@router.get("/customer/conversations")
def customer_conversations(session=Depends(require_customer_session)):
    _purge_expired_customer_ignored()
    return conversation_store.customer_conversations(session["session_hash"])


@router.post("/conversations/{conversation_id}/ignore")
def customer_ignore_conversation(conversation_id: str, session=Depends(require_customer_write)):
    with _conversation_lock(conversation_id):
        if not conversation_store.belongs_to_customer_session(conversation_id, session["session_hash"]):
            raise HTTPException(status_code=404, detail="Conversation not found")
        return conversation_store.set_status(conversation_id, "ignored", "", ignored_by_customer=True)


@router.post("/conversations")
def create_conversation(req: ConversationCreateRequest, session=Depends(require_customer_write)):
    return conversation_store.create(req.brand_id, req.customer_name, req.email, req.order_id,
                                     customer_session_id=session["session_hash"])


@router.get("/conversations/{conversation_id}")
def get_conversation(conversation_id: str, _session=Depends(require_owned_conversation)):
    item = conversation_store.get(conversation_id)
    if not item:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return item


@router.get("/conversations/{conversation_id}/messages")
def get_messages(conversation_id: str, after_id: int = 0, _session=Depends(require_owned_conversation)):
    if not conversation_store.get(conversation_id):
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation_store.messages(conversation_id, after_id)


@router.get("/conversations/{conversation_id}/attachments/{attachment_id}")
def get_conversation_attachment(conversation_id: str, attachment_id: str, _session=Depends(require_owned_conversation)):
    if not conversation_store.get(conversation_id):
        raise HTTPException(status_code=404, detail="Conversation not found")
    attachment = next((item for message in conversation_store.messages(conversation_id)
                       for item in message.get("attachments", []) if item.get("id") == attachment_id), None)
    if not attachment:
        raise HTTPException(status_code=404, detail="Attachment not found")
    suffixes = {"image/jpeg": ".jpg", "image/png": ".png", "image/gif": ".gif",
                "image/webp": ".webp", "application/pdf": ".pdf"}
    path = _ATTACHMENTS_DIR / conversation_id / f"{attachment_id}{suffixes.get(attachment['media_type'], '')}"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Attachment file is missing")
    return FileResponse(path, media_type=attachment["media_type"], filename=attachment["name"],
                        content_disposition_type="inline" if attachment["media_type"].startswith("image/") else "attachment")


@router.post("/conversations/{conversation_id}/messages")
def customer_message(conversation_id: str, req: MessageRequest, session=Depends(require_customer_write)):
    if not conversation_store.belongs_to_customer_session(conversation_id, session["session_hash"]):
        raise HTTPException(status_code=404, detail="Conversation not found")
    return _process_customer_message(conversation_id, req)


def _record_customer_order(conversation_id: str, brand_id: str, message: str):
    order_match = re.search(r"\b((?:RLVNT|ORDR?|ORDER)[-_ ]\d{3,8})\b", message, re.IGNORECASE)
    if not order_match:
        return
    order_id = order_match.group(1).upper()
    conversation_store.set_order_id(conversation_id, order_id)
    if order_tool.get_order_status(order_id, brand_id):
        customer_name = order_tool.get_customer_name(order_id, brand_id)
        if customer_name:
            conversation_store.set_customer_name(conversation_id, customer_name)


def _process_customer_message(conversation_id: str, req: MessageRequest):
    if not req.content.strip() and not req.attachments:
        raise HTTPException(status_code=422, detail="Write a message or attach a file.")
    with _conversation_lock(conversation_id):
        conv = conversation_store.get(conversation_id)
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")
        saved_attachments = _save_message_attachments(conversation_id, req.attachments)
        message_content = req.content.strip()
        model_content = message_content or "The customer attached: " + ", ".join(item["name"] for item in saved_attachments)
        if conv["status"] in {"human_active", "waiting", "ignored"}:
            conversation_store.add_message(conversation_id, "customer", message_content, attachments=saved_attachments)
            _record_customer_order(conversation_id, conv["brand_id"], req.content)
            orchestrator.session_manager.add_turn(conversation_id, conv["brand_id"], "customer", model_content)
            return {"status": conv["status"], "reply": None}
        if conv["status"] == "resolved":
            conversation_store.set_status(conversation_id, "ai_active", "")
        # Restore durable context after an API restart. Within a running process,
        # the orchestrator already owns this session's turns and entity memory.
        if not orchestrator.session_manager.get_history(conversation_id, conv["brand_id"]):
            for msg in conversation_store.messages(conversation_id):
                role = "customer" if msg["role"] == "customer" else "assistant"
                orchestrator.session_manager.add_turn(conversation_id, conv["brand_id"], role, msg["content"])
        # The order reference already associated with this customer conversation
        # is useful context; the order tool will verify it before stating details.
        if conv.get("order_id"):
            orchestrator.session_manager.remember_order_id(
                conversation_id, conv["brand_id"], conv["order_id"]
            )
        conversation_store.add_message(conversation_id, "customer", message_content, attachments=saved_attachments)
        _record_customer_order(conversation_id, conv["brand_id"], req.content)
        try:
            turn = orchestrator.handle_turn(conv["brand_id"], conversation_id, model_content)
        except GeminiGenerationError as exc:
            if exc.escalation_succeeded:
                conversation_store.set_status(conversation_id, "waiting", "")
            logger.warning("Gemini unavailable for conversation %s; no assistant reply was stored.", conversation_id)
            raise HTTPException(
                status_code=503,
                detail="Gemini 2.5 Flash is temporarily unavailable. No AI response was generated.",
            )
        except Exception:
            logger.exception("Conversation generation failed for %s; no assistant reply was stored.", conversation_id)
            raise HTTPException(status_code=500, detail="The AI request could not be completed. No response was generated.")
        transparency = turn.transparency.model_dump(mode="json")
        conversation_store.add_message(conversation_id, "assistant", turn.reply, transparency)
        if turn.transparency.is_escalated:
            conversation_store.set_status(conversation_id, "waiting")
        return {"status": conversation_store.get(conversation_id)["status"], "reply": turn.reply,
                "transparency": transparency}


@router.post("/admin/login")
def admin_login(credentials: AdminLoginRequest, request: Request):
    configured_email = os.getenv("BRANDMIND_ADMIN_EMAIL", "").strip().casefold()
    configured_password = os.getenv("BRANDMIND_ADMIN_PASSWORD", "")
    if not configured_email or not configured_password or _expected_admin_token() is None:
        raise HTTPException(status_code=503, detail="Support sign-in is not configured")
    if os.getenv("ENVIRONMENT", "development").lower() == "production" and len(configured_password) < 12:
        raise HTTPException(status_code=503, detail="Set a stronger support password before production")

    client_ip = request.client.host if request.client else "unknown"
    now = time.monotonic()
    with _ADMIN_LOGIN_LOCK:
        attempts = [stamp for stamp in _ADMIN_LOGIN_ATTEMPTS.get(client_ip, []) if now - stamp < 900]
        _ADMIN_LOGIN_ATTEMPTS[client_ip] = attempts
        if len(attempts) >= 5:
            raise HTTPException(status_code=429, detail="Too many sign-in attempts. Try again in 15 minutes.")

    valid_email = hmac.compare_digest(credentials.email.strip().casefold(), configured_email)
    valid_password = hmac.compare_digest(credentials.password, configured_password)
    if not (valid_email and valid_password):
        with _ADMIN_LOGIN_LOCK:
            _ADMIN_LOGIN_ATTEMPTS.setdefault(client_ip, []).append(now)
        raise HTTPException(status_code=401, detail="Email or password is incorrect")

    with _ADMIN_LOGIN_LOCK:
        _ADMIN_LOGIN_ATTEMPTS.pop(client_ip, None)
    return {"access_token": _expected_admin_token(), "token_type": "bearer"}


@router.get("/admin/conversations", dependencies=[Depends(require_admin)])
def admin_conversations(status: str = "all", query: str = "", brand_id: str = "rlvnt"):
    _purge_expired_customer_ignored()
    return conversation_store.list(brand_id=brand_id, status=status, query=query)


@router.get("/admin/stats", dependencies=[Depends(require_admin)])
def admin_stats(brand_id: str = "rlvnt"):
    return conversation_store.stats(brand_id)


@router.get("/admin/analytics", dependencies=[Depends(require_admin)])
def admin_analytics(brand_id: str = "rlvnt"):
    return conversation_store.analytics(brand_id)


@router.get("/admin/conversations/{conversation_id}/messages", dependencies=[Depends(require_admin)])
def admin_messages(conversation_id: str, after_id: int = 0):
    if not conversation_store.get(conversation_id):
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation_store.messages(conversation_id, after_id)


@router.get("/admin/conversations/{conversation_id}/attachments/{attachment_id}", dependencies=[Depends(require_admin)])
def admin_conversation_attachment(conversation_id: str, attachment_id: str):
    if not conversation_store.get(conversation_id):
        raise HTTPException(status_code=404, detail="Conversation not found")
    attachment = next((item for message in conversation_store.messages(conversation_id)
                       for item in message.get("attachments", []) if item.get("id") == attachment_id), None)
    if not attachment:
        raise HTTPException(status_code=404, detail="Attachment not found")
    suffixes = {"image/jpeg": ".jpg", "image/png": ".png", "image/gif": ".gif",
                "image/webp": ".webp", "application/pdf": ".pdf"}
    path = _ATTACHMENTS_DIR / conversation_id / f"{attachment_id}{suffixes.get(attachment['media_type'], '')}"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Attachment file is missing")
    return FileResponse(path, media_type=attachment["media_type"], filename=attachment["name"],
                        content_disposition_type="inline" if attachment["media_type"].startswith("image/") else "attachment")


@router.get("/admin/conversations/{conversation_id}", dependencies=[Depends(require_admin)])
def admin_conversation(conversation_id: str):
    item = conversation_store.get(conversation_id)
    if not item:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return item


@router.get("/admin/conversations/{conversation_id}/order", dependencies=[Depends(require_admin)])
def admin_order(conversation_id: str):
    conv = conversation_store.get(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if not conv["order_id"]:
        return None
    order = order_tool.get_order_status(conv["order_id"], conv["brand_id"])
    if not order:
        return None
    details = order.model_dump(mode="json")
    details["customer_name"] = order_tool.get_customer_name(conv["order_id"], conv["brand_id"])
    return details


@router.post("/admin/conversations/{conversation_id}/messages", dependencies=[Depends(require_admin)])
def admin_reply(conversation_id: str, req: MessageRequest):
    if not req.content.strip() and not req.attachments:
        raise HTTPException(status_code=422, detail="Write a message or attach a file.")
    with _conversation_lock(conversation_id):
        conv = conversation_store.get(conversation_id)
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")
        if conv["status"] != "human_active":
            raise HTTPException(status_code=409, detail="Take over the conversation before replying")
        saved_attachments = _save_message_attachments(conversation_id, req.attachments)
        message_content = req.content.strip()
        msg = conversation_store.add_message(conversation_id, "admin", message_content, attachments=saved_attachments)
        if message_content:
            orchestrator.session_manager.add_turn(conversation_id, conv["brand_id"], "assistant", message_content)
        return msg


@router.post("/admin/conversations/{conversation_id}/takeover", dependencies=[Depends(require_admin)])
def admin_takeover(conversation_id: str, req: HandoffRequest = HandoffRequest()):
    with _conversation_lock(conversation_id):
        conv = conversation_store.get(conversation_id)
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")
        if conv.get("status") in {"resolved", "ignored"}:
            raise HTTPException(status_code=409, detail="Archived conversations are read-only")
        return conversation_store.set_status(conversation_id, "human_active", req.assigned_to)


@router.post("/admin/conversations/{conversation_id}/return-to-ai", dependencies=[Depends(require_admin)])
def return_to_ai(conversation_id: str):
    with _conversation_lock(conversation_id):
        conv = conversation_store.get(conversation_id)
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")
        if conv.get("status") in {"resolved", "ignored"}:
            raise HTTPException(status_code=409, detail="Archived conversations are read-only")
        return conversation_store.set_status(conversation_id, "ai_active", "")


@router.post("/admin/conversations/{conversation_id}/resolve", dependencies=[Depends(require_admin)])
def resolve_conversation(conversation_id: str):
    if not conversation_store.get(conversation_id):
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation_store.set_status(conversation_id, "resolved", "")


@router.post("/admin/conversations/{conversation_id}/ignore", dependencies=[Depends(require_admin)])
def ignore_conversation(conversation_id: str):
    with _conversation_lock(conversation_id):
        if not conversation_store.get(conversation_id):
            raise HTTPException(status_code=404, detail="Conversation not found")
        return conversation_store.set_status(conversation_id, "ignored", "")
