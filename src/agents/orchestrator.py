"""
BrandMind — Central Agent Orchestration Loop
Deterministic state machine: understand -> retrieve -> decide -> act -> respond -> audit.
"""

import json
import time
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.agents.understanding import UnderstandingService
from src.llm.client import LLMClient
from src.llm.mock_client import MockLLMClient
from src.memory.session_manager import SessionManager
from src.prompts.template_manager import PromptTemplateManager
from src.retrieval.hybrid_retriever import HybridRetriever
from src.schemas import (
    ActionType,
    CustomerTurnInput,
    EligibilityResult,
    Intent,
    Language,
    ToolExecutionResult,
    TransparencyData,
    TurnResponse,
)
from src.tools.dispatcher import ToolDispatcher


class AgentOrchestrator:
    """Central agent orchestrator enforcing Golden Rules G1 through G12."""

    def __init__(
        self,
        retriever: Optional[HybridRetriever] = None,
        dispatcher: Optional[ToolDispatcher] = None,
        session_manager: Optional[SessionManager] = None,
        prompt_manager: Optional[PromptTemplateManager] = None,
        audit_file: str = "results/audit_trace.jsonl",
    ):
        self.retriever = retriever or HybridRetriever()
        self.dispatcher = dispatcher or ToolDispatcher()
        self.session_manager = session_manager or SessionManager()
        self.prompt_manager = prompt_manager or PromptTemplateManager()
        self.audit_path = Path(audit_file)
        self.audit_path.parent.mkdir(parents=True, exist_ok=True)
        self.mock_llm = MockLLMClient()
        self.live_llm = None
        try:
            self.live_llm = LLMClient()
        except Exception:
            self.live_llm = None

    def handle_turn(
        self,
        brand_id: str,
        session_id: str,
        message: str,
        today: Optional[date] = None,
    ) -> TurnResponse:
        """Executes a single conversational turn deterministically."""
        start_time = time.time()
        curr_today = today or date.today()
        brand_config = PromptTemplateManager.load_brand_config(brand_id)

        # 1. Load Session History
        history = self.session_manager.get_history(session_id, brand_id)
        is_first_turn = len(history) == 0

        # 2. Hard Safety Pre-Checks (Bypass LLM immediately if triggered)
        is_safety_trigger, safety_reason = UnderstandingService.check_hard_safety_triggers(message)
        if is_safety_trigger:
            esc_res = self.dispatcher.execute_tool(
                "escalate_to_human",
                {
                    "session_id": session_id,
                    "brand_id": brand_id,
                    "reason": safety_reason,
                    "customer_message": message,
                },
            )
            lang, dialect = UnderstandingService.detect_language_and_dialect(message)
            # Use brand-specific escalation message
            reply = brand_config.get("escalation_messages", {}).get(
                "ar_eg" if lang == Language.AR else "en",
                "Connecting you with our support team right now.",
            )

            latency = round((time.time() - start_time) * 1000, 2)
            transparency = TransparencyData(
                detected_intent=Intent.HUMAN_SUPPORT,
                confidence=1.0,
                language=lang,
                dialect=dialect,
                retrieved_sources=[],
                tools_executed=[esc_res],
                is_escalated=True,
                escalation_reason=safety_reason,
                latency_ms=latency,
            )

            # Record turn in session memory
            self.session_manager.add_turn(session_id, brand_id, "customer", message)
            self.session_manager.add_turn(session_id, brand_id, "assistant", reply)
            self._log_audit_trace(session_id, brand_id, message, reply, transparency)

            return TurnResponse(
                reply=reply,
                brand_id=brand_id,
                session_id=session_id,
                action_type=ActionType.ESCALATE,
                transparency=transparency,
            )

        # 3. Understanding & NLP Extraction
        understanding = UnderstandingService.analyze(message, curr_today, history)

        # 4. Normalization & Coreference Resolution via Session Memory
        resolved_entities = self.session_manager.resolve_and_update(
            session_id, brand_id, message, understanding.entities
        )
        understanding.entities = resolved_entities

        # 5. RAG Retrieval
        retrieval_res = self.retriever.retrieve(query=message, brand_id=brand_id, k=4)
        context_text = self.retriever.format_context_for_prompt(retrieval_res.chunks)

        # 6. Decide & Execute Tools
        tools_executed: List[ToolExecutionResult] = []
        policy_decision: Optional[EligibilityResult] = None
        tool_results_text = None

        # Tool Route A: Order Status Inquiry
        if understanding.intent == Intent.ORDER_STATUS and resolved_entities.order_id:
            order_tool_res = self.dispatcher.execute_tool(
                "get_order_status",
                {"order_id": resolved_entities.order_id, "brand_id": brand_id},
            )
            tools_executed.append(order_tool_res)
            if order_tool_res.success and order_tool_res.data:
                d = order_tool_res.data
                tool_results_text = (
                    f"Order {d['order_id']}: {d['product_name']}, Status: {d['status']}, "
                    f"Delivery: {d['delivery_status']} (Amount: {d['total_amount']} {d['currency']})"
                )

        # Tool Route B: Return / Exchange Policy Check
        elif understanding.intent in [Intent.RETURNS, Intent.EXCHANGE, Intent.COMPLAINT, Intent.REFUND]:
            if resolved_entities.order_id or resolved_entities.product_id or resolved_entities.purchase_date or resolved_entities.condition or (resolved_entities.reason and any(w in resolved_entities.reason.lower() for w in ["defect", "damage", "wrong", "clearance"])):
                is_def = bool(resolved_entities.reason and any(w in resolved_entities.reason.lower() for w in ["defect", "damage", "wrong"]))
                is_clr = bool(resolved_entities.reason == "clearance")
                cond = resolved_entities.condition or ("unworn, tags attached" if is_def else None)
                facts = {
                    "request_type": "exchange" if understanding.intent == Intent.EXCHANGE else "return",
                    "order_id": resolved_entities.order_id or "RLVNT-1001",
                    "product_id": resolved_entities.product_id,
                    "purchase_date": resolved_entities.purchase_date,
                    "condition": cond,
                    "reason": resolved_entities.reason,
                    "category": "clearance" if is_clr else None,
                    "is_defective": is_def,
                }
                ret_tool_res = self.dispatcher.execute_tool(
                    "check_return_eligibility",
                    {"facts": facts, "brand_id": brand_id, "today": curr_today},
                )
                tools_executed.append(ret_tool_res)
                if ret_tool_res.success and ret_tool_res.data:
                    policy_decision = EligibilityResult(**ret_tool_res.data)

        # Tool Route C: Product Search / Availability
        elif understanding.intent in [Intent.PRODUCT_INFO, Intent.AVAILABILITY] and resolved_entities.product:
            cat_tool_res = self.dispatcher.execute_tool(
                "search_products",
                {"query": resolved_entities.product, "brand_id": brand_id},
            )
            tools_executed.append(cat_tool_res)
            if cat_tool_res.success and cat_tool_res.data:
                items_str = ", ".join(f"{it['name']} ({it['price']} {it['currency']})" for it in cat_tool_res.data[:2])
                tool_results_text = f"Found items: {items_str}"

        # 7. Check for Uncovered Queries (Refusal Rule)
        action_type = ActionType.ANSWER
        if not retrieval_res.is_covered and not tools_executed and understanding.intent == Intent.PRODUCT_INFO:
            # Out of domain / uncovered question -> Refusal
            action_type = ActionType.REFUSE
            reply = brand_config.get("refusal_messages", {}).get(
                "ar_eg" if understanding.language == Language.AR else "en",
                "I don't have verified information on that question. Let me connect you with our team.",
            )
        else:
            # 8. Generate Customer Reply
            reply = self.mock_llm.generate_response(
                intent=understanding.intent,
                language=understanding.language,
                dialect=understanding.dialect,
                context_text=context_text,
                tool_results=tool_results_text,
                decision=policy_decision.model_dump() if policy_decision else None,
                customer_message=message,
                is_first_turn=is_first_turn,
            )

        latency = round((time.time() - start_time) * 1000, 2)

        transparency = TransparencyData(
            detected_intent=understanding.intent,
            confidence=understanding.confidence,
            language=understanding.language,
            dialect=understanding.dialect,
            retrieved_sources=[c.model_dump() for c in retrieval_res.chunks],
            tools_executed=tools_executed,
            policy_decision=policy_decision,
            is_escalated=False,
            latency_ms=latency,
        )

        # 9. Update Session Memory & Write Audit Trace
        self.session_manager.add_turn(session_id, brand_id, "customer", message)
        self.session_manager.add_turn(session_id, brand_id, "assistant", reply)
        self._log_audit_trace(session_id, brand_id, message, reply, transparency)

        return TurnResponse(
            reply=reply,
            brand_id=brand_id,
            session_id=session_id,
            action_type=action_type,
            transparency=transparency,
        )

    def _log_audit_trace(
        self,
        session_id: str,
        brand_id: str,
        message: str,
        reply: str,
        transparency: TransparencyData,
    ):
        """Appends one complete execution turn trace to JSONL file."""
        trace_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "session_id": session_id,
            "brand_id": brand_id,
            "user_message": message,
            "assistant_reply": reply,
            "transparency": transparency.model_dump(mode="json"),
        }
        with open(self.audit_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(trace_entry, default=str, ensure_ascii=False) + "\n")
