# BrandMind test guide

Run the current automated suites with:

```powershell
py -m pytest tests/ -v
```

The suite covers Gemini-only provider selection, generated response wiring, failure handling, audit isolation, session memory, RAG, business tools, escalation, prompt safety, evaluation, and FastAPI endpoints. Tests stub Gemini calls so they do not consume API quota.

## Focused suites

```powershell
py -m pytest tests/unit/test_llm_client.py tests/unit/test_llm_integration.py -v
py -m pytest tests/security/ -v
py -m pytest tests/integration/ -v
py -m pytest tests/evaluation/ -v
```

Tests that exercise the production orchestrator write audit traces into pytest's temporary directory. Historical files in `results/` are not test output targets.

For retrieval tests in environments without Hugging Face network access, set `HF_HUB_OFFLINE=1` if the Sentence Transformers model is already cached.
