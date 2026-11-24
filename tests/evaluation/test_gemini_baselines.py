import csv
import json
from pathlib import Path
from types import SimpleNamespace

from src.evaluation.baselines import DirectLLMBaseline, FullBrandMindSystem, RAGOnlyBaseline
from src.evaluation.runner import EvaluationBenchmarkRunner


class FakeGemini:
    provider = "google"
    model_name = "gemini-test-model"
    is_configured = True
    max_output_tokens = 1024

    def __init__(self):
        self.prompts = []

    def generate(self, prompt, temperature=0.3, max_output_tokens=None):
        self.prompts.append((prompt, temperature, max_output_tokens))
        return "Gemini generated response"


class FakeRetriever:
    def __init__(self):
        self.calls = []

    def retrieve(self, query, brand_id, k):
        self.calls.append((query, brand_id, k))
        chunk = SimpleNamespace(
            chunk_id="chunk-1",
            source_file="policy.pdf",
            source_page=3,
            section="Returns",
            similarity_score=0.91,
            content="RLVNT accepts return requests within 14 days of delivery.",
        )
        return SimpleNamespace(chunks=[chunk], top_similarity=0.91, is_covered=True)

    @staticmethod
    def format_context_for_prompt(chunks):
        return "\n".join(chunk.content for chunk in chunks)


def test_direct_baseline_calls_gemini_without_rag_or_tools():
    client = FakeGemini()
    result = DirectLLMBaseline(llm_client=client).run("What is RLVNT's return window?")

    prompt, temperature, max_tokens = client.prompts[0]
    assert "What is RLVNT's return window?" in prompt
    assert "REFERENCE CONTEXT" not in prompt
    assert temperature == 0.3
    assert max_tokens == 1024
    assert result["reply"] == "Gemini generated response"
    assert result["generator"] == "llm:google:gemini-test-model"
    assert result["retrieved_sources"] == []
    assert result["tools_executed"] == []
    assert result["generation_latency_ms"] >= 0


def test_rag_only_uses_retrieval_context_and_gemini_without_business_tools():
    client = FakeGemini()
    retriever = FakeRetriever()
    baseline = RAGOnlyBaseline(retriever=retriever, llm_client=client)
    result = baseline.run("What is RLVNT's return window?")

    prompt, temperature, max_tokens = client.prompts[0]
    assert "14 days of delivery" in prompt
    assert "What is RLVNT's return window?" in prompt
    assert temperature == 0.3
    assert max_tokens == 1024
    assert retriever.calls == [("What is RLVNT's return window?", "rlvnt", 4)]
    assert result["retrieved_sources"][0]["chunk_id"] == "chunk-1"
    assert result["retrieval_top_similarity"] == 0.91
    assert result["retrieval_latency_ms"] >= 0
    assert result["generation_latency_ms"] >= 0
    assert result["tools_executed"] == []
    assert not hasattr(baseline, "dispatcher")


def test_gemini_failure_is_recorded_without_substitute_reply():
    client = FakeGemini()

    def fail(*args, **kwargs):
        raise RuntimeError("provider failure that should not leak")

    client.generate = fail
    baseline = DirectLLMBaseline(llm_client=client)
    result = EvaluationBenchmarkRunner._run_config(baseline, "config_a", "question", {})
    assert result["status"] == "error"
    assert result["reply"] == ""
    assert result["generation_latency_ms"] >= 0
    assert "provider failure that should not leak" not in result["error"]


def test_full_config_delegates_to_orchestrator_and_records_timing():
    client = FakeGemini()
    retriever = FakeRetriever()

    class FakeOrchestrator:
        def __init__(self):
            self.live_llm = client
            self.retriever = retriever

        def handle_turn(self, brand_id, session_id, message):
            self.retriever.retrieve(message, brand_id, 4)
            self.live_llm.generate("production prompt", temperature=0.3)
            source = {"chunk_id": "chunk-1", "source_file": "policy.pdf", "source_page": 3,
                      "section": "Returns", "similarity_score": 0.91}
            transparency = SimpleNamespace(
                policy_decision=None,
                tools_executed=[],
                detected_intent=SimpleNamespace(value="returns"),
                retrieved_sources=[source],
                is_escalated=False,
                generator="llm:google:gemini-test-model",
            )
            return SimpleNamespace(reply="Gemini generated response", transparency=transparency)

    result = FullBrandMindSystem(orchestrator=FakeOrchestrator()).run("return question", "eval-id")
    assert result["reply"] == "Gemini generated response"
    assert result["model_name"] == "gemini-test-model"
    assert result["generator"] == "llm:google:gemini-test-model"
    assert result["retrieved_sources"][0]["chunk_id"] == "chunk-1"
    assert result["generation_latency_ms"] >= 0
    assert result["retrieval_latency_ms"] >= 0


def test_runner_exports_independent_csvs_with_manual_columns(tmp_path):
    dataset = [{
        "id": "EVAL-1", "language": "en", "category": "answerable", "question": "A shared question",
        "expected_intent": "product_info", "expected_tool": None, "expected_decision": None,
        "expected_escalation": False, "gold_chunk_ids": [], "ground_truth_fact": "",
    }]
    dataset_path = tmp_path / "dataset.json"
    dataset_path.write_text(json.dumps(dataset), encoding="utf-8")
    client_a, client_b = FakeGemini(), FakeGemini()
    shared_retriever = FakeRetriever()
    # Config C is tested above against an orchestrator-shaped dependency; the
    # runner test supplies all three so no production components are constructed.
    class Recorder:
        def __init__(self, result):
            self.questions = []
            self.result = result

        def run(self, question, **kwargs):
            self.questions.append(question)
            return dict(self.result)

    a = Recorder(DirectLLMBaseline(llm_client=client_a).run("seed"))
    b = Recorder(RAGOnlyBaseline(retriever=shared_retriever, llm_client=client_b).run("seed"))
    c = Recorder({
        "reply": "full response", "generator": "llm:google:gemini-test-model", "provider": "google",
        "model_name": "gemini-test-model", "detected_intent": "product_info", "decision": None,
        "retrieved_sources": [], "tools_executed": [], "is_escalated": False,
        "retrieval_latency_ms": 1, "generation_latency_ms": 2, "total_latency_ms": 3, "latency_ms": 3,
        "status": "ok", "error": "", "correctness": "", "hallucination": "",
        "policy_compliance": "", "safety": "", "response_quality": "", "overall_verdict": "",
        "evaluator_notes": "",
    })
    # Replace seed rows with a representative generated row per config.
    a.result["reply"] = "direct response"
    b.result["reply"] = "rag response"
    paths = {key: tmp_path / f"{key}.csv" for key in ("a", "b", "c")}
    runner = EvaluationBenchmarkRunner(
        dataset_path=str(dataset_path),
        output_summary_path=str(tmp_path / "summary.json"),
        output_report_path=str(tmp_path / "unused-report.md"),
        output_traces_path=str(tmp_path / "traces.jsonl"),
        gemini_csv_path=str(paths["a"]), rag_csv_path=str(paths["b"]), full_csv_path=str(paths["c"]),
        config_a=a, config_b=b, config_c=c,
    )
    runner.run_benchmark()

    assert a.questions == b.questions == c.questions == ["A shared question"]
    expected_manual = {
        "correctness", "hallucination", "policy_compliance", "safety", "response_quality",
        "overall_verdict", "evaluator_notes",
    }
    for path, expected_reply in ((paths["a"], "direct response"), (paths["b"], "rag response"),
                                 (paths["c"], "full response")):
        with path.open(encoding="utf-8-sig", newline="") as f:
            rows = list(csv.DictReader(f))
        assert len(rows) == 1
        assert rows[0]["customer_question"] == "A shared question"
        assert rows[0]["reply"] == expected_reply
        assert expected_manual.issubset(rows[0])


def test_runner_stops_remote_calls_after_quota_error_and_exports_failure_rows(tmp_path):
    dataset = [
        {"id": f"EVAL-{n}", "language": "en", "category": "answerable", "question": f"Question {n}",
         "expected_intent": "product_info", "expected_tool": None, "expected_decision": None,
         "expected_escalation": False, "gold_chunk_ids": [], "ground_truth_fact": ""}
        for n in (1, 2)
    ]
    dataset_path = tmp_path / "dataset.json"
    dataset_path.write_text(json.dumps(dataset), encoding="utf-8")

    class QuotaErrorConfig:
        model_name = "gemini-test-model"
        calls = 0

        def run(self, question, **kwargs):
            self.calls += 1
            raise RuntimeError("429 RESOURCE_EXHAUSTED")

    class MustNotRun:
        model_name = "gemini-test-model"
        calls = 0

        def run(self, question, **kwargs):
            self.calls += 1
            raise AssertionError("quota circuit breaker should skip later calls")

    a, b, c = QuotaErrorConfig(), MustNotRun(), MustNotRun()
    runner = EvaluationBenchmarkRunner(
        dataset_path=str(dataset_path),
        output_summary_path=str(tmp_path / "summary.json"),
        output_report_path=str(tmp_path / "unused.md"),
        output_traces_path=str(tmp_path / "traces.jsonl"),
        gemini_csv_path=str(tmp_path / "a.csv"), rag_csv_path=str(tmp_path / "b.csv"),
        full_csv_path=str(tmp_path / "c.csv"), config_a=a, config_b=b, config_c=c,
    )
    runner.run_benchmark()

    assert a.calls == 1
    assert b.calls == c.calls == 0
    for path in (tmp_path / "a.csv", tmp_path / "b.csv", tmp_path / "c.csv"):
        with path.open(encoding="utf-8-sig", newline="") as f:
            rows = list(csv.DictReader(f))
        assert len(rows) == 2
        assert all(row["status"] == "error" for row in rows)
        assert "429" in rows[0]["error"]
