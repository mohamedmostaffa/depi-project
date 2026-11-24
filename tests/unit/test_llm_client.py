import pytest
from src.llm.client import GEMINI_MODEL, LLMClient


def clean(monkeypatch):
    for key in ("GEMINI_API_KEY", "LLM_API_KEY", "LLM_PROVIDER", "LLM_MODEL", "LLM_BASE_URL"):
        monkeypatch.delenv(key, raising=False)


def test_not_configured_without_gemini_key(monkeypatch):
    clean(monkeypatch)
    client = LLMClient()
    assert not client.is_configured
    with pytest.raises(ValueError, match="GEMINI_API_KEY"):
        client.generate("hello")


@pytest.mark.parametrize("provider", ["openai", "groq", "ollama", "openrouter"])
def test_rejects_alternate_provider(monkeypatch, provider):
    clean(monkeypatch)
    monkeypatch.setenv("LLM_PROVIDER", provider)
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    with pytest.raises(ValueError, match="only supports Google Gemini"):
        LLMClient()


def test_rejects_alternate_model(monkeypatch):
    clean(monkeypatch)
    monkeypatch.setenv("LLM_MODEL", "gemini-1.5-flash")
    with pytest.raises(ValueError, match=GEMINI_MODEL):
        LLMClient()


def test_gemini_key_uses_fixed_model_and_returns_sdk_text(monkeypatch):
    clean(monkeypatch)
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    client = LLMClient()

    class Models:
        def generate_content(self, **kwargs):
            assert kwargs["model"] == GEMINI_MODEL
            return type("Response", (), {"text": "Gemini answer"})()

    client._client = type("FakeClient", (), {"models": Models()})()
    assert client.generate("prompt") == "Gemini answer"


def test_retries_then_fails_without_alternate_generator(monkeypatch):
    clean(monkeypatch)
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setattr("src.llm.client.time.sleep", lambda _: None)
    client = LLMClient()
    client.retry_attempts = 2
    calls = {"n": 0}

    def failed(*_args, **_kwargs):
        calls["n"] += 1
        raise RuntimeError("429")

    client._call_once = failed
    with pytest.raises(RuntimeError, match="failed after"):
        client.generate("prompt")
    assert calls["n"] == 2
