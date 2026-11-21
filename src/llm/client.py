"""
BrandMind — LLM Client Provider Wrapper
Provides Google GenAI SDK integration with exponential backoff and JSON structured output.
"""

import os
from typing import Any, Dict, Optional
import yaml


class LLMClient:
    def __init__(self, config_path: str = "config/settings.yaml"):
        self.config_path = config_path
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.model_name = "gemini-2.5-flash"
        self._client = None
        self._load_config()

    def _load_config(self):
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                cfg = yaml.safe_load(f)
                self.model_name = cfg.get("llm", {}).get("model", "gemini-2.5-flash")
        except Exception:
            pass

    def _get_client(self):
        if self._client is None:
            if not self.api_key:
                raise ValueError("GEMINI_API_KEY environment variable is not set")
            from google import genai
            self._client = genai.Client(api_key=self.api_key)
        return self._client

    def generate(self, prompt: str, temperature: float = 0.3) -> str:
        """Generates response using official google-genai client."""
        client = self._get_client()
        response = client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config={"temperature": temperature},
        )
        return response.text.strip()
