"""Gemini 2.5 Flash client for all BrandMind customer-facing generation."""

import logging
import os
import time
from typing import Optional

import yaml

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # pragma: no cover - environment may provide variables directly
    pass

logger = logging.getLogger(__name__)
GEMINI_MODEL = "gemini-2.5-flash"
_GOOGLE_ALIASES = {"google", "gemini"}


class LLMClient:
    """A single-provider client that refuses alternate providers and models."""

    def __init__(self, config_path: str = "config/settings.yaml"):
        self.config_path = config_path
        llm_cfg = self._read_llm_config()
        configured_provider = str(llm_cfg.get("provider", "google")).strip().lower()
        requested_provider = (os.getenv("LLM_PROVIDER") or "").strip().lower()
        if configured_provider not in _GOOGLE_ALIASES or (
            requested_provider and requested_provider not in _GOOGLE_ALIASES
        ):
            raise ValueError("BrandMind only supports Google Gemini for response generation.")

        configured_model = str(llm_cfg.get("model", GEMINI_MODEL)).strip()
        requested_model = (os.getenv("LLM_MODEL") or "").strip()
        if configured_model != GEMINI_MODEL or (requested_model and requested_model != GEMINI_MODEL):
            raise ValueError(f"BrandMind requires the {GEMINI_MODEL} model.")

        self.provider = "google"
        self.api_key = os.getenv("GEMINI_API_KEY", "").strip()
        self.model_name = GEMINI_MODEL
        self.retry_attempts = max(1, int(llm_cfg.get("retry_attempts", 3)))
        self.backoff_factor = float(llm_cfg.get("backoff_factor", 2.0))
        self.max_output_tokens = int(llm_cfg.get("max_output_tokens", 1024))
        self._client = None

    def _read_llm_config(self) -> dict:
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                return (yaml.safe_load(f) or {}).get("llm", {}) or {}
        except (OSError, yaml.YAMLError):
            return {}

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    @property
    def label(self) -> str:
        return f"{self.provider}:{self.model_name}"

    def _get_client(self):
        if self._client is None:
            if not self.api_key:
                raise ValueError("Gemini is not configured. Set GEMINI_API_KEY in the API environment.")
            from google import genai

            self._client = genai.Client(api_key=self.api_key)
        return self._client

    def _call_once(self, prompt: str, temperature: float, max_output_tokens: Optional[int] = None) -> str:
        generation_config = {"temperature": temperature}
        if max_output_tokens is not None:
            generation_config["max_output_tokens"] = max_output_tokens
        response = self._get_client().models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=generation_config,
        )
        text = (getattr(response, "text", None) or "").strip()
        if not text:
            raise RuntimeError("Gemini returned an empty response")
        return text

    def generate(
        self,
        prompt: str,
        temperature: float = 0.3,
        max_output_tokens: Optional[int] = None,
    ) -> str:
        """Generate with Gemini, retrying transient API failures without any fallback."""
        last_error: Optional[Exception] = None
        for attempt in range(self.retry_attempts):
            try:
                return self._call_once(prompt, temperature, max_output_tokens)
            except ValueError:
                raise
            except Exception as exc:
                last_error = exc
                logger.warning("Gemini call failed (attempt %d/%d): %s", attempt + 1, self.retry_attempts, exc)
                if attempt < self.retry_attempts - 1:
                    time.sleep(self.backoff_factor ** attempt)
        raise RuntimeError(f"Gemini call failed after {self.retry_attempts} attempts: {last_error}") from last_error
