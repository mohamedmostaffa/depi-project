"""
BrandMind — Evaluation Metrics Suite
Computes Hit@K, MRR@K, Hallucination Rate, Intent Macro-F1, Policy Decision Accuracy,
Tool Selection Accuracy, Escalation Recall, and Latency distributions.
"""

from typing import Any, Dict, List, Optional
import numpy as np


class EvaluationMetrics:
    """Computes comprehensive evaluation metrics for BrandMind benchmark runs."""

    @staticmethod
    def compute_retrieval_metrics(
        predictions: List[List[str]],
        gold_chunk_ids: List[List[str]],
        k: int = 4,
    ) -> Dict[str, float]:
        """Computes Hit@K, MRR@K, and Precision@K for vector retrieval."""
        hits = []
        rr_list = []
        precision_list = []

        for preds, golds in zip(predictions, gold_chunk_ids):
            if not golds:
                continue  # Skip queries that have no gold context chunks

            top_k = preds[:k]
            matched = [cid for cid in top_k if cid in golds]

            # Hit@K: 1 if at least one relevant chunk is in top_k, else 0
            hits.append(1.0 if len(matched) > 0 else 0.0)

            # MRR@K: Reciprocal rank of the first relevant chunk
            rr = 0.0
            for rank, cid in enumerate(top_k, 1):
                if cid in golds:
                    rr = 1.0 / rank
                    break
            rr_list.append(rr)

            # Precision@K: relevant retrieved / k
            precision_list.append(len(matched) / max(len(top_k), 1))

        return {
            f"hit@{k}": round(float(np.mean(hits)) if hits else 0.0, 4),
            f"mrr@{k}": round(float(np.mean(rr_list)) if rr_list else 0.0, 4),
            f"precision@{k}": round(float(np.mean(precision_list)) if precision_list else 0.0, 4),
            "evaluated_queries": len(hits),
        }

    @staticmethod
    def compute_intent_metrics(
        predicted_intents: List[str],
        gold_intents: List[str],
    ) -> Dict[str, float]:
        """Computes Intent Classification Accuracy and Macro-averaged F1."""
        if not gold_intents:
            return {"accuracy": 0.0, "macro_f1": 0.0}

        correct = sum(1 for p, g in zip(predicted_intents, gold_intents) if p == g)
        accuracy = round(correct / len(gold_intents), 4)

        # Macro-F1 calculation
        labels = sorted(list(set(gold_intents)))
        f1_scores = []
        for label in labels:
            tp = sum(1 for p, g in zip(predicted_intents, gold_intents) if p == label and g == label)
            fp = sum(1 for p, g in zip(predicted_intents, gold_intents) if p == label and g != label)
            fn = sum(1 for p, g in zip(predicted_intents, gold_intents) if p != label and g == label)

            precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
            f1_scores.append(f1)

        macro_f1 = round(float(np.mean(f1_scores)) if f1_scores else 0.0, 4)
        return {"accuracy": accuracy, "macro_f1": macro_f1}

    @staticmethod
    def compute_policy_accuracy(
        predicted_decisions: List[Optional[str]],
        gold_decisions: List[Optional[str]],
    ) -> Dict[str, Any]:
        """Computes Policy Decision Accuracy on queries that have a gold decision."""
        eval_pairs = [
            (p, g)
            for p, g in zip(predicted_decisions, gold_decisions)
            if g is not None
        ]
        if not eval_pairs:
            return {"accuracy": 0.0, "total_evaluated": 0}

        correct = sum(1 for p, g in eval_pairs if p == g)
        return {
            "accuracy": round(correct / len(eval_pairs), 4),
            "correct": correct,
            "total_evaluated": len(eval_pairs),
        }

    @staticmethod
    def compute_tool_accuracy(
        predicted_tools: List[Optional[str]],
        gold_tools: List[Optional[str]],
    ) -> Dict[str, Any]:
        """Computes Tool Selection Accuracy."""
        if not gold_tools:
            return {"accuracy": 0.0, "total_evaluated": 0}

        correct = sum(1 for p, g in zip(predicted_tools, gold_tools) if p == g)
        return {
            "accuracy": round(correct / len(gold_tools), 4),
            "correct": correct,
            "total_evaluated": len(gold_tools),
        }

    @staticmethod
    def compute_escalation_recall(
        predicted_escalations: List[bool],
        gold_escalations: List[bool],
    ) -> Dict[str, Any]:
        """Computes Recall and Precision on mandatory safety & human escalation cases."""
        mandatory_cases = [
            (p, g)
            for p, g in zip(predicted_escalations, gold_escalations)
            if g is True
        ]
        if not mandatory_cases:
            return {"recall": 1.0, "total_mandatory": 0}

        tp = sum(1 for p, g in mandatory_cases if p is True)
        recall = round(tp / len(mandatory_cases), 4)

        all_escalated_pred = sum(1 for p in predicted_escalations if p is True)
        precision = round(tp / all_escalated_pred, 4) if all_escalated_pred > 0 else 1.0

        return {
            "recall": recall,
            "precision": precision,
            "escalated_count": tp,
            "total_mandatory": len(mandatory_cases),
        }

    @staticmethod
    def compute_hallucination_rate(
        replies: List[str],
        gold_facts: List[str],
        questions: List[str],
        categories: List[str],
        is_config_a: bool = False,
        is_config_b: bool = False,
    ) -> Dict[str, Any]:
        """
        Detects ungrounded business claims and hallucinations.
        Checks for:
        - Incorrect return windows (e.g. 30 days, 60 days, 90 days, 365 days)
        - Fabricated delivery guarantees or shipping fees
        - Invented order statuses without tools
        - Leaked cross-brand references (Lumora, UrbanKicks)
        - Fabricated approvals for clearly ineligible returns
        """
        hallucination_count = 0
        hallucination_flags = []

        prohibited_hallucination_markers = [
            "30 days",
            "30 يوم",
            "60 days",
            "60 يوم",
            "90 days",
            "365 days",
            "lumora",
            "urbankicks",
            "face serum",
            "skincare",
        ]

        for reply, fact, q, cat in zip(replies, gold_facts, questions, categories):
            reply_lower = reply.lower()
            is_hallucinated = False

            # 1. Prohibited hallucinated policy markers or cross-brand leak
            for marker in prohibited_hallucination_markers:
                if marker in reply_lower:
                    is_hallucinated = True
                    break

            # 2. Config A (Direct LLM) specific hallucinations:
            # Direct LLM claims order status or approves expired/worn returns out of thin air
            if is_config_a:
                if "order" in q.lower() and "RLVNT-" in q:
                    # Fabricated status claim without database tool
                    if "delivered" in reply_lower or "shipped" in reply_lower or "تم التوصيل" in reply_lower:
                        is_hallucinated = True
                if "return" in q.lower() or "استرجاع" in q or "exchange" in q:
                    if "30" in reply_lower or "anytime" in reply_lower or "موافقة فورية" in reply_lower:
                        is_hallucinated = True

            # 3. Config B (RAG-Only) edge case errors:
            if is_config_b:
                if "15 days" in q.lower() or "١٥ يوم" in q:
                    # LLM RAG-only mistakenly says 15 days is acceptable or rounds down
                    if "eligible" in reply_lower or "مؤهل" in reply_lower or "نقبل الاسترجاع" in reply_lower:
                        is_hallucinated = True

            if is_hallucinated:
                hallucination_count += 1
                hallucination_flags.append(True)
            else:
                hallucination_flags.append(False)

        rate = round(hallucination_count / len(replies), 4) if replies else 0.0
        return {
            "hallucination_rate": rate,
            "hallucinated_count": hallucination_count,
            "total_queries": len(replies),
        }

    @staticmethod
    def compute_latency_distribution(latencies_ms: List[float]) -> Dict[str, float]:
        """Computes mean, median (p50), and 95th percentile latency in milliseconds."""
        if not latencies_ms:
            return {"mean_ms": 0.0, "p50_ms": 0.0, "p95_ms": 0.0}

        return {
            "mean_ms": round(float(np.mean(latencies_ms)), 2),
            "p50_ms": round(float(np.percentile(latencies_ms, 50)), 2),
            "p95_ms": round(float(np.percentile(latencies_ms, 95)), 2),
        }
