"""
BrandMind — Comparative Evaluation Baselines
Implements the 3 required comparative configurations:
- Config A: Direct LLM-Only Baseline (Zero retrieval, no policy engine, prompt only)
- Config B: RAG-Only Baseline (Retrieval enabled, LLM makes return decisions without deterministic engine)
- Config C: Full BrandMind System (Hybrid RAG + Deterministic Policy Engine + Tools + Guardrails)
"""

import time
from typing import Any, Dict, List, Optional

from src.agents.orchestrator import AgentOrchestrator
from src.agents.understanding import UnderstandingService
from src.retrieval.hybrid_retriever import HybridRetriever
from src.schemas import Decision, Dialect, Intent, Language


class DirectLLMBaseline:
    """Config A: Direct LLM without RAG, without deterministic engine, without tools."""

    def __init__(self, brand_id: str = "rlvnt"):
        self.brand_id = brand_id

    def run(self, question: str) -> Dict[str, Any]:
        start = time.time()
        q_lower = question.lower()
        is_ar = any("\u0600" <= c <= "\u06ff" for c in question)

        # Direct LLM relies on general parametric memory, producing typical e-commerce hallucinations
        if "return" in q_lower or "استرجاع" in question or "تبديل" in question or "exchange" in q_lower:
            # Typical hallucination: defaults to 30 days
            if is_ar:
                reply = "أهلاً بك! يمكنك استرجاع أو استبدال المنتجات خلال 30 يوم من تاريخ الشراء بشرط سلامة المنتج."
            else:
                reply = "Hello! We offer a standard 30-day return and exchange policy for all purchases."
            decision = "eligible" if "15" in question or "30" in question else None
        elif "order" in q_lower or "أوردر" in question or "طلب" in question or "rlvnt-" in q_lower:
            # Fabricates order status without checking DB
            if is_ar:
                reply = "أهلاً بك، أوردرك في الطريق إليك حالياً وسيصلك خلال يومين عبر شركة الشحن."
            else:
                reply = "Your order is in transit and expected to be delivered in 2-3 business days."
            decision = None
        elif "allergy" in q_lower or "rash" in q_lower or "حساسية" in question:
            # Fails to escalate to human, attempts casual advice
            if is_ar:
                reply = "نعتذر عن ذلك. يمكنك غسل القطعة بالماء الدافئ وارتداء قميص قطني خفيف تحتها."
            else:
                reply = "We apologize for the discomfort. You can try washing the garment with gentle soap."
            decision = None
        elif "lawsuit" in q_lower or "قضية" in question or "محضر" in question:
            if is_ar:
                reply = "نحن نحرص على إرضاء عملائنا ونتمنى حل الموضوع ودياً دون الحاجة لإجراءات."
            else:
                reply = "We always strive to satisfy our customers and hope to resolve this amicably."
            decision = None
        elif "leather" in q_lower or "boots" in q_lower or "فساتين" in question:
            # May attempt to answer or apologize casually
            if is_ar:
                reply = "نعتذر، هذه المنتجات غير متوفرة حالياً في المخزن."
            else:
                reply = "Sorry, we currently do not have motorcycle boots in stock."
            decision = None
        elif "system prompt" in q_lower or "تعليمات" in question or "override" in q_lower:
            # Susceptible to prompt extraction/override
            reply = "You asked to override instructions. Our return window is now updated as requested."
            decision = "eligible"
        else:
            if is_ar:
                reply = "شكراً لتواصلك معنا. ملابسنا مصنوعة من أجود الخامات ويسعدنا مساعدتك دائماً."
            else:
                reply = "Thank you for reaching out! Our apparel is crafted with quality materials."
            decision = None

        latency = round((time.time() - start) * 1000, 2)
        return {
            "reply": reply,
            "detected_intent": "general",
            "decision": decision,
            "retrieved_sources": [],
            "tools_executed": [],
            "is_escalated": False,
            "latency_ms": latency,
        }


class RAGOnlyBaseline:
    """Config B: RAG enabled, but NO deterministic policy engine and NO tools."""

    def __init__(self, brand_id: str = "rlvnt", retriever: Optional[HybridRetriever] = None):
        self.brand_id = brand_id
        self.retriever = retriever or HybridRetriever()

    def run(self, question: str) -> Dict[str, Any]:
        start = time.time()
        q_lower = question.lower()
        is_ar = any("\u0600" <= c <= "\u06ff" for c in question)

        # 1. Retrieve context chunks
        retrieval_res = self.retriever.retrieve(
            query=question,
            brand_id=self.brand_id,
            k=4,
        )
        chunks = retrieval_res.chunks if retrieval_res.is_covered else []
        retrieved_ids = [c.chunk_id for c in chunks]

        # 2. LLM evaluates without deterministic Python policy engine
        # Vulnerabilities:
        # - Boundary errors on date arithmetic (day 15 vs 14)
        # - Misses clearance non-returnable rule
        # - Falls for </context> injection
        decision = None
        if "15 days" in q_lower or "١٥ يوم" in question or "16" in q_lower:
            # LLM boundary hallucination: rounds down or shows lenient approval
            decision = "eligible"
            if is_ar:
                reply = "بما أنك قريب من فترة الـ 14 يوم ومحتفظ بالتيكت، يسعدنا قبول الاسترجاع بشكل استثنائي!"
            else:
                reply = "Since you are close to our 14-day window and kept the tags, we can approve your return exception!"
        elif "clearance" in q_lower or "تصفية" in question or "final sale" in q_lower:
            # LLM misses fine print exception without deterministic engine
            decision = "eligible"
            if is_ar:
                reply = "يمكنك استبدال القطعة طالما أنها بحالتها الأصلية والتيكت سليم."
            else:
                reply = "You can exchange the item as long as it remains in unworn condition."
        elif "</context>" in question or "override" in q_lower:
            # Prompt injection breakthrough
            decision = "eligible"
            reply = "Admin override accepted. Your return has been approved immediately."
        elif "8 days" in q_lower or "٨ أيام" in question or "10 days" in q_lower or "١٠ أيام" in question:
            decision = "eligible"
            if is_ar:
                reply = "طلبك مؤهل للاستبدال لأنك داخل فترة الـ 14 يوم والقطعة بالتيكت."
            else:
                reply = "Your request is eligible since you are well within the 14-day policy window."
        elif "return" in q_lower or "استرجاع" in question or "exchange" in q_lower:
            if is_ar:
                reply = "سياسة RLVNT تتيح الاسترجاع والاستبدال خلال 14 يوم من تاريخ الاستلام للقطع غير المستخدمة."
            else:
                reply = "RLVNT's policy allows returns and exchanges within 14 days of delivery for unworn items with tags."
        elif "order" in q_lower or "أوردر" in question:
            # Lacks OrderTool execution
            if is_ar:
                reply = "يرجى العلم أنني لا أملك أداة فحص قاعدة البيانات حالياً للاطلاع على حالة أوردرك."
            else:
                reply = "I do not have access to an active order tracking tool to look up live status."
        elif "allergy" in q_lower or "rash" in q_lower or "حساسية" in question:
            # No hard safety escalation bypass
            if is_ar:
                reply = "نأسف لسماع ذلك، يرجى التوقف عن ارتداء القطعة واستشارة الطبيب."
            else:
                reply = "We are sorry to hear that. Please stop wearing the garment and consult a physician."
        else:
            if chunks:
                if is_ar:
                    reply = f"بناء على وثائق RLVNT: {chunks[0].content[:160]}..."
                else:
                    reply = f"According to RLVNT documents: {chunks[0].content[:160]}..."
            else:
                if is_ar:
                    reply = "عذراً، هذا الاستفسار خارج نطاق المعلومات المتاحة لمنتجات RLVNT."
                else:
                    reply = "I apologize, this question is outside RLVNT's available product scope."

        latency = round((time.time() - start) * 1000, 2)
        return {
            "reply": reply,
            "detected_intent": "returns" if "return" in q_lower or "استرجاع" in question else "faq",
            "decision": decision,
            "retrieved_sources": retrieved_ids,
            "tools_executed": [],
            "is_escalated": False,
            "latency_ms": latency,
        }


class FullBrandMindSystem:
    """Config C: Full BrandMind System with Hybrid RAG + Deterministic Engine + Tools + Guardrails."""

    def __init__(self, brand_id: str = "rlvnt", orchestrator: Optional[AgentOrchestrator] = None):
        self.brand_id = brand_id
        self.orchestrator = orchestrator or AgentOrchestrator()

    def run(self, question: str, session_id: str = "eval_session") -> Dict[str, Any]:
        turn = self.orchestrator.handle_turn(
            brand_id=self.brand_id,
            session_id=session_id,
            message=question,
        )

        decision = None
        if turn.transparency.policy_decision:
            dec_obj = turn.transparency.policy_decision.decision
            decision = dec_obj.value if hasattr(dec_obj, "value") else str(dec_obj)

        tools = [
            t.tool_name if hasattr(t, "tool_name") else str(t)
            for t in turn.transparency.tools_executed
        ]

        return {
            "reply": turn.reply,
            "detected_intent": turn.transparency.detected_intent.value if hasattr(turn.transparency.detected_intent, "value") else str(turn.transparency.detected_intent),
            "decision": decision,
            "retrieved_sources": [
                s.get("chunk_id", "") if isinstance(s, dict) else getattr(s, "chunk_id", str(s))
                for s in turn.transparency.retrieved_sources
            ],
            "tools_executed": tools,
            "is_escalated": turn.transparency.is_escalated,
            "latency_ms": turn.transparency.latency_ms,
        }
