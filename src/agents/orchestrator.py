"""
BrandMind — Central Agent Orchestration Loop
Deterministic state machine: understand -> retrieve -> decide -> act -> respond -> audit.
"""

import json
import logging
import time
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.agents.smalltalk import is_small_talk
from src.agents.understanding import UnderstandingService
from src.llm.client import LLMClient
from src.memory.session_manager import SessionManager
from src.prompts.template_manager import PromptTemplateManager
from src.retrieval.hybrid_retriever import HybridRetriever
from src.schemas import (
    ActionType,
    CustomerTurnInput,
    Dialect,
    EligibilityResult,
    Intent,
    Language,
    ToolExecutionResult,
    TransparencyData,
    TurnResponse,
)
from src.tools.dispatcher import ToolDispatcher

logger = logging.getLogger(__name__)


class GeminiGenerationError(RuntimeError):
    """Safe application-level error raised when Gemini cannot generate a reply."""

    def __init__(self, *, escalation_succeeded: bool = False):
        super().__init__("Gemini response generation is unavailable.")
        self.escalation_succeeded = escalation_succeeded


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
        """Use Gemini 2.5 Flash as the only customer-facing response generator."""
        self.retriever = retriever or HybridRetriever()
        self.dispatcher = dispatcher or ToolDispatcher()
        self.session_manager = session_manager or SessionManager()
        self.prompt_manager = prompt_manager or PromptTemplateManager()
        self.audit_path = Path(audit_file)
        self.audit_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self.live_llm = LLMClient()
        except Exception as exc:
            raise RuntimeError("Gemini 2.5 Flash could not be initialized.") from exc
        if self.live_llm.provider != "google":
            raise RuntimeError("Only Google Gemini is supported for customer response generation.")

    def _llm_reply(self, template_name: str, ctx: Dict[str, Any]) -> str:
        """Generate a non-empty customer-facing response with Gemini or raise safely."""
        try:
            prompt = self.prompt_manager.render(template_name, ctx)
            reply = self.live_llm.generate(prompt, temperature=0.3)
            if not isinstance(reply, str) or not reply.strip():
                raise ValueError("Gemini returned an empty response")
            return reply.strip()
        except Exception as exc:
            logger.exception("Gemini generation failed; no canned fallback will be sent.")
            raise GeminiGenerationError() from exc

    def generate_customer_message(self, template_name: str, context: Dict[str, Any]) -> str:
        """Generate a Gemini-authored message for a verified non-chat tool result."""
        return self._llm_reply(template_name, context)

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
        if UnderstandingService.is_human_support_request(message):
            is_safety_trigger = True
            safety_reason = "Customer explicitly requested a human support agent"
        elif UnderstandingService.is_handoff_confirmation(message, history):
            is_safety_trigger = True
            safety_reason = "Customer accepted the offer to connect with human support"
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
            self.session_manager.add_turn(session_id, brand_id, "customer", message)
            generator = f"llm:{self.live_llm.label}"
            try:
                reply = self._llm_reply(
                    "escalation.j2",
                    {
                        "brand": brand_config,
                        "escalation_reason": safety_reason,
                        "customer_message": message,
                        "escalation_succeeded": esc_res.success,
                        "escalation_status": (esc_res.data or {}).get("status", "") if esc_res.success and isinstance(esc_res.data, dict) else "",
                    },
                )
            except GeminiGenerationError as exc:
                exc.escalation_succeeded = esc_res.success
                raise

            latency = round((time.time() - start_time) * 1000, 2)
            transparency = TransparencyData(
                detected_intent=Intent.HUMAN_SUPPORT,
                confidence=1.0,
                language=lang,
                dialect=dialect,
                retrieved_sources=[],
                tools_executed=[esc_res],
                is_escalated=esc_res.success,
                escalation_reason=safety_reason,
                memory_context_messages=0,
                latency_ms=latency,
                generator=generator,
            )

            # Record only Gemini's generated response; the customer turn was added above.
            self.session_manager.add_turn(session_id, brand_id, "assistant", reply)
            self._log_audit_trace(session_id, brand_id, message, reply, transparency)

            return TurnResponse(
                reply=reply,
                brand_id=brand_id,
                session_id=session_id,
                action_type=ActionType.ESCALATE,
                transparency=transparency,
            )

        # 2b. Greeting / thanks / goodbye only: no retrieval, no tools, just a natural reply in the brand voice
        if is_small_talk(message):
            lang, dialect = UnderstandingService.detect_language_and_dialect(message)
            response_language = (
                "English" if lang == Language.EN else
                "Egyptian Arabic" if dialect == Dialect.EGYPTIAN else
                "Franco-Arabic" if dialect == Dialect.FRANCO else
                "Arabic"
            )
            reply = self._llm_reply(
                "smalltalk.j2",
                {
                    "brand": brand_config,
                    "customer_message": message,
                    "response_language": response_language,
                    "history": list(history)[-8:],
                    "is_first_turn": is_first_turn,
                    "max_sentences": 2,
                },
            )
            transparency = TransparencyData(
                detected_intent=Intent.SMALL_TALK,
                confidence=1.0,
                language=lang,
                dialect=dialect,
                retrieved_sources=[],
                tools_executed=[],
                policy_decision=None,
                is_escalated=False,
                memory_context_messages=len(list(history)[-8:]),
                latency_ms=round((time.time() - start_time) * 1000, 2),
                generator=f"llm:{self.live_llm.label}",
            )
            self.session_manager.add_turn(session_id, brand_id, "customer", message)
            self.session_manager.add_turn(session_id, brand_id, "assistant", reply)
            self._log_audit_trace(session_id, brand_id, message, reply, transparency)
            return TurnResponse(
                reply=reply,
                brand_id=brand_id,
                session_id=session_id,
                action_type=ActionType.ANSWER,
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
            else:
                # A failed lookup is still verified tool output. Pass the exact ID
                # and not-found result to Gemini so it can explain the outcome in
                # the customer's language instead of treating the ID as a FAQ.
                tool_results_text = (
                    f"Order lookup completed. No order was found with the exact ID "
                    f"{resolved_entities.order_id} for brand {brand_id}. Do not infer or "
                    "substitute another order number. Ask the customer to verify the ID."
                )

        # Tool Route B: Return / Exchange Policy Check
        elif understanding.intent in [Intent.RETURNS, Intent.EXCHANGE, Intent.COMPLAINT, Intent.REFUND]:
            if resolved_entities.order_id or resolved_entities.product_id or resolved_entities.purchase_date or resolved_entities.condition or (resolved_entities.reason and any(w in resolved_entities.reason.lower() for w in ["defect", "damage", "wrong", "clearance"])):
                is_def = bool(resolved_entities.reason and any(w in resolved_entities.reason.lower() for w in ["defect", "damage", "wrong"]))
                is_clr = bool(resolved_entities.reason == "clearance")
                cond = resolved_entities.condition or ("unworn, tags attached" if is_def else None)
                facts = {
                    "request_type": "exchange" if understanding.intent == Intent.EXCHANGE else "return",
                    "order_id": resolved_entities.order_id,
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
        generator = f"llm:{self.live_llm.label}"
        if not retrieval_res.is_covered and not tools_executed and understanding.intent == Intent.PRODUCT_INFO:
            # Uncovered questions still require a Gemini-generated refusal.
            action_type = ActionType.REFUSE
            reply = self._llm_reply("refusal.j2", {"brand": brand_config, "customer_message": message})
        else:
            # Gemini narrates only verified retrieved facts and tool observations.
            reply = self._llm_reply(
                "grounded_generation.j2",
                {
                    "brand": brand_config,
                    "context_text": context_text,
                    "tool_results": tool_results_text,
                    "decision": policy_decision.model_dump(mode="json") if policy_decision else None,
                    "history": list(history)[-8:],
                    "customer_message": message,
                    "is_first_turn": is_first_turn,
                    "max_sentences": 3,
                },
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
            memory_context_messages=len(list(history)[-8:]),
            latency_ms=latency,
            generator=generator,
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
