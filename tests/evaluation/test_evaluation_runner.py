"""
BrandMind — Automated Tests for Evaluation Suite
Validates that EvaluationMetrics, Baselines, and Benchmark dataset operate properly.
"""

from src.evaluation.baselines import DirectLLMBaseline, FullBrandMindSystem, RAGOnlyBaseline
from src.evaluation.metrics import EvaluationMetrics


def test_retrieval_metrics_calculation():
    preds = [["chunk_1", "chunk_2"], ["chunk_3", "chunk_4"]]
    golds = [["chunk_1"], ["chunk_5"]]

    res = EvaluationMetrics.compute_retrieval_metrics(preds, golds, k=2)
    assert res["hit@2"] == 0.5
    assert res["mrr@2"] == 0.5
    assert res["precision@2"] == 0.25


def test_intent_metrics_calculation():
    pred_intents = ["returns", "shipping", "product_info"]
    gold_intents = ["returns", "shipping", "shipping"]

    res = EvaluationMetrics.compute_intent_metrics(pred_intents, gold_intents)
    assert res["accuracy"] == round(2 / 3, 4)
    assert res["macro_f1"] > 0.0


def test_escalation_recall_calculation():
    pred_esc = [True, True, False]
    gold_esc = [True, True, True]

    res = EvaluationMetrics.compute_escalation_recall(pred_esc, gold_esc)
    assert res["recall"] == round(2 / 3, 4)
    assert res["escalated_count"] == 2


def test_policy_accuracy_calculation():
    pred_dec = ["eligible", "not_eligible", "needs_info"]
    gold_dec = ["eligible", "not_eligible", "not_eligible"]

    res = EvaluationMetrics.compute_policy_accuracy(pred_dec, gold_dec)
    assert res["accuracy"] == round(2 / 3, 4)
    assert res["correct"] == 2


def test_direct_llm_baseline_runs():
    base = DirectLLMBaseline()
    out = base.run("What is the return window?")
    assert "reply" in out
    assert out["is_escalated"] is False


def test_brandmind_full_system_smoke(tmp_path):
    from src.agents.orchestrator import AgentOrchestrator

    orchestrator = AgentOrchestrator(audit_file=str(tmp_path / "evaluation_audit_trace.jsonl"))
    full = FullBrandMindSystem(orchestrator=orchestrator)
    out = full.run("What is RLVNT's return window?", session_id="test_eval_smoke")
    assert "reply" in out
    assert len(out["retrieved_sources"]) > 0
    assert out["is_escalated"] is False
