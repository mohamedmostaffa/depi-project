"""
BrandMind — Short-Term Session Memory & Coreference Manager
Maintains sliding conversation windows and resolves cross-turn conversational references.
"""

from typing import Dict, List, Optional
from datetime import datetime, timezone

from src.schemas import ConversationTurn, ExtractedEntities


class SessionState:
    def __init__(self, session_id: str, brand_id: str, window_size: int = 8):
        self.session_id = session_id
        self.brand_id = brand_id
        self.window_size = window_size
        self.turns: List[ConversationTurn] = []
        self.tracked_entities: Dict[str, Optional[str]] = {
            "product": None,
            "product_id": None,
            "order_id": None,
            "size": None,
            "color": None,
        }
        self.last_active = datetime.now(timezone.utc)

    def add_turn(self, role: str, content: str):
        self.turns.append(ConversationTurn(role=role, content=content))
        # Keep sliding window bounded
        if len(self.turns) > self.window_size * 2:
            self.turns = self.turns[-(self.window_size * 2):]
        self.last_active = datetime.now(timezone.utc)

    def update_entities(self, extracted: ExtractedEntities):
        """Updates tracked session entities if new non-null values are observed."""
        if extracted.product:
            self.tracked_entities["product"] = extracted.product
        if extracted.product_id:
            self.tracked_entities["product_id"] = extracted.product_id
        if extracted.order_id:
            self.tracked_entities["order_id"] = extracted.order_id
        if extracted.size:
            self.tracked_entities["size"] = extracted.size
        if extracted.color:
            self.tracked_entities["color"] = extracted.color

    def resolve_coreference(self, user_text: str, extracted: ExtractedEntities) -> ExtractedEntities:
        """Resolves pronouns and demonstratives ('it', 'this', 'the black one', 'ده') using session state."""
        import re
        tokens = set(re.findall(r'\b\w+\b', user_text.lower()))
        text_lower = user_text.lower()

        pronoun_triggers_en = {"it", "this", "that", "item", "piece", "one"}
        pronoun_triggers_ar = ["ده", "دي", "القطعة", "الهودي", "السويت شيرت", "المقاس ده", "أبدلها", "أرجعه", "أبدله"]

        has_pronoun_en = bool(tokens.intersection(pronoun_triggers_en))
        has_pronoun_ar = any(p in text_lower for p in pronoun_triggers_ar)

        if (has_pronoun_en or has_pronoun_ar) and not extracted.product:
            if self.tracked_entities["product"]:
                extracted.product = self.tracked_entities["product"]
                if self.tracked_entities["product_id"] and not extracted.product_id:
                    extracted.product_id = self.tracked_entities["product_id"]

        if not extracted.order_id and self.tracked_entities["order_id"]:
            order_reference_terms = (
                "order", "أوردر", "اوردر", "طلب", "return", "exchange", "swap", "refund",
                "ارجاع", "إرجاع", "ارجع", "أرجع", "ترجيع", "استرجاع", "تبديل",
                "استبدال", "أبدل", "ابدل", "أبدله", "ارجعه",
            )
            if any(term in text_lower for term in order_reference_terms):
                extracted.order_id = self.tracked_entities["order_id"]

        return extracted


class SessionManager:
    """Manages active customer conversational sessions in memory."""

    def __init__(self, default_window_size: int = 8):
        self.default_window_size = default_window_size
        self._sessions: Dict[str, SessionState] = {}

    def get_or_create_session(self, session_id: str, brand_id: str) -> SessionState:
        if session_id not in self._sessions:
            self._sessions[session_id] = SessionState(
                session_id=session_id,
                brand_id=brand_id,
                window_size=self.default_window_size,
            )
        return self._sessions[session_id]

    def add_turn(self, session_id: str, brand_id: str, role: str, content: str):
        session = self.get_or_create_session(session_id, brand_id)
        session.add_turn(role, content)

    def remember_order_id(self, session_id: str, brand_id: str, order_id: str):
        """Attach a conversation's supplied order reference to its session context.

        The order tool still verifies the exact ID before any order facts are used.
        """
        if order_id:
            session = self.get_or_create_session(session_id, brand_id)
            session.tracked_entities["order_id"] = order_id.strip().upper()

    def get_history(self, session_id: str, brand_id: str) -> List[ConversationTurn]:
        session = self.get_or_create_session(session_id, brand_id)
        return session.turns

    def resolve_and_update(
        self, session_id: str, brand_id: str, user_text: str, extracted: ExtractedEntities
    ) -> ExtractedEntities:
        session = self.get_or_create_session(session_id, brand_id)
        resolved = session.resolve_coreference(user_text, extracted)
        session.update_entities(resolved)
        return resolved
