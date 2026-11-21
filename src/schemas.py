"""
BrandMind — Core Pydantic Schemas & Interface Contracts
Single Source of Truth for System Interfaces
"""

from datetime import date, datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field, field_validator


# ==============================================================================
# 1. Enums for Typed Classifications
# ==============================================================================

class Language(str, Enum):
    EN = "en"
    AR = "ar"


class Dialect(str, Enum):
    EN = "en"
    MSA = "msa"
    EGYPTIAN = "egyptian"
    MIXED = "mixed"
    FRANCO = "franco"


class Intent(str, Enum):
    SHIPPING = "shipping"
    RETURNS = "returns"
    EXCHANGE = "exchange"
    REFUND = "refund"
    PAYMENT = "payment"
    PRODUCT_INFO = "product_info"
    AVAILABILITY = "availability"
    ORDER_STATUS = "order_status"
    COMPLAINT = "complaint"
    HUMAN_SUPPORT = "human_support"


class Sentiment(str, Enum):
    NEUTRAL = "neutral"
    FRUSTRATED = "frustrated"
    ANGRY = "angry"


class Decision(str, Enum):
    ELIGIBLE = "eligible"
    NOT_ELIGIBLE = "not_eligible"
    NEEDS_INFO = "needs_info"


class ActionType(str, Enum):
    ANSWER = "answer"
    REFUSE = "refuse"
    ESCALATE = "escalate"


# ==============================================================================
# 2. Conversational Input & Session Schemas
# ==============================================================================

class ConversationTurn(BaseModel):
    role: str = Field(..., description="'customer' or 'assistant'")
    content: str = Field(..., min_length=1)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CustomerTurnInput(BaseModel):
    brand_id: str = Field(..., min_length=1, description="Unique identifier for the brand (e.g. 'rlvnt')")
    session_id: str = Field(..., min_length=1, description="Unique conversation session ID")
    message: str = Field(..., min_length=1, description="Raw text message from customer")
    history: List[ConversationTurn] = Field(default_factory=list, description="Recent conversation turns")


# ==============================================================================
# 3. Understanding & NLP Extraction Schemas
# ==============================================================================

class ExtractedEntities(BaseModel):
    product: Optional[str] = Field(default=None, description="Mentioned garment or design name")
    product_id: Optional[str] = Field(default=None, description="Specific SKU or item ID if known")
    order_id: Optional[str] = Field(default=None, description="Order identifier (e.g. RLVNT-1042)")
    purchase_date: Optional[date] = Field(default=None, description="Explicit ISO purchase/delivery date")
    purchase_date_text: Optional[str] = Field(default=None, description="Relative or unparsed date string")
    size: Optional[str] = Field(default=None, description="Size (S, M, L, XL, XXL, etc.)")
    color: Optional[str] = Field(default=None, description="Color (Black, White, Crimson, etc.)")
    condition: Optional[str] = Field(default=None, description="Garment condition (unworn, washed, tags attached)")
    reason: Optional[str] = Field(default=None, description="Stated reason for return/exchange")


class UnderstandingResult(BaseModel):
    language: Language = Field(default=Language.EN)
    dialect: Dialect = Field(default=Dialect.EN)
    intent: Intent = Field(..., description="Classified intent from the 9 supported classes")
    entities: ExtractedEntities = Field(default_factory=ExtractedEntities)
    sentiment: Sentiment = Field(default=Sentiment.NEUTRAL)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    requires_human: bool = Field(default=False, description="Flagged by hard safety rules")


# ==============================================================================
# 4. Retrieval & Knowledge Schemas
# ==============================================================================

class RetrievedChunk(BaseModel):
    chunk_id: str
    brand_id: str
    source_file: str
    source_page: int
    document_type: str
    section: str
    content: str
    similarity_score: float = Field(..., ge=0.0, le=1.0)


class RetrievalResult(BaseModel):
    query: str
    brand_id: str
    chunks: List[RetrievedChunk] = Field(default_factory=list)
    is_covered: bool = Field(default=True, description="False if top score < similarity_threshold")
    top_similarity: float = Field(default=0.0)


# ==============================================================================
# 5. Deterministic Policy Engine Schemas
# ==============================================================================

class EligibilityResult(BaseModel):
    decision: Decision
    reason_code: str = Field(..., description="Machine-readable code (e.g. OUTSIDE_WINDOW, ELIGIBLE)")
    reason_text: str = Field(..., description="Authoritative natural explanation for the customer")
    missing_fields: List[str] = Field(default_factory=list, description="Fields required if NEEDS_INFO")
    rule_trace: List[str] = Field(default_factory=list, description="Ordered audit trail of evaluated rules")


class PolicyRuleSet(BaseModel):
    policy_id: str
    brand_id: str
    policy_type: str
    allowed_days: int = Field(..., ge=0)
    acceptable_conditions: List[str]
    non_returnable_categories: List[str]
    fee_applies: bool = False
    fee_amount: Optional[float] = None
    free_exchange: bool = False


# ==============================================================================
# 6. Tool Execution Schemas
# ==============================================================================

class ProductItem(BaseModel):
    product_id: str
    brand_id: str
    name: str
    category: str
    price: float
    currency: str = "EGP"
    sizes: List[str]
    colors: List[str]
    description: str
    stock: int = Field(default=0, ge=0)
    returnable: bool = True


class OrderItem(BaseModel):
    order_id: str
    brand_id: str
    customer_id: str
    product_id: str
    product_name: str
    order_date: date
    delivery_date: Optional[date] = None
    status: str
    delivery_status: str
    total_amount: float
    currency: str = "EGP"


class ToolCall(BaseModel):
    tool_name: str
    arguments: Dict[str, Any]
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ToolExecutionResult(BaseModel):
    tool_name: str
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class EscalationRecord(BaseModel):
    session_id: str
    brand_id: str
    reason: str
    customer_message: str
    conversation_summary: Optional[str] = None
    escalated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: str = "PENDING_HUMAN_REVIEW"


# ==============================================================================
# 7. Customer Response & Transparency Audit Payload
# ==============================================================================

class TransparencyData(BaseModel):
    detected_intent: Intent
    confidence: float
    language: Language
    dialect: Dialect
    retrieved_sources: List[Dict[str, Any]] = Field(default_factory=list)
    tools_executed: List[ToolExecutionResult] = Field(default_factory=list)
    policy_decision: Optional[EligibilityResult] = None
    is_escalated: bool = False
    escalation_reason: Optional[str] = None
    latency_ms: float = 0.0


class TurnResponse(BaseModel):
    reply: str = Field(..., description="Natural customer-facing message")
    brand_id: str
    session_id: str
    action_type: ActionType = ActionType.ANSWER
    transparency: TransparencyData
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
