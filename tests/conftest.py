"""Test-suite defaults. The project now always answers through Gemini (offline mock mode is disabled),
so tests use a deterministic stub instead of the network: no API key, no quota, no flaky replies."""
import os

os.environ.setdefault("LLM_PROVIDER", "google")
os.environ.setdefault("GEMINI_API_KEY", "test-key-not-used")

import pytest


def _stub_generate(self, prompt, temperature=0.3, max_output_tokens=None):
    facts = [l.strip() for l in prompt.splitlines() if l.startswith(("Outcome:", "Official Reason:"))]
    return "TEST_LLM_REPLY " + " | ".join(facts)


@pytest.fixture(autouse=True)
def stub_llm(monkeypatch, request):
    if request.module.__name__.endswith("test_llm_client"):
        return  # those tests exercise the real client (retries, config) and mock only the network call
    from src.llm.client import LLMClient
    monkeypatch.setattr(LLMClient, "generate", _stub_generate)
