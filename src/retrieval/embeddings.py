"""
BrandMind — Multilingual Embedding Service
Generates vector representations using local SentenceTransformers models.
"""

from typing import List, Optional
import numpy as np


class EmbeddingService:
    """Provides vector embeddings using SentenceTransformers with an offline fallback."""

    def __init__(self, model_name: str = "paraphrase-multilingual-MiniLM-L12-v2"):
        self.model_name = model_name
        self._model = None
        self._dimension = 384

    def _load_model(self):
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(self.model_name)
                if hasattr(self._model, "get_embedding_dimension"):
                    self._dimension = self._model.get_embedding_dimension()
                else:
                    self._dimension = self._model.get_sentence_embedding_dimension()
            except Exception as e:
                # If network or model loading fails, log warning and use deterministic deterministic fallback
                print(f"Warning: Failed to load '{self.model_name}': {e}. Using deterministic fallback.")
                self._model = "FALLBACK"

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        self._load_model()
        if self._model != "FALLBACK":
            embeddings = self._model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
            return embeddings.tolist()
        else:
            # Deterministic hash-based normalized vector for testing/offline environments
            results = []
            for t in texts:
                seed = abs(hash(t)) % (2**32)
                rng = np.random.default_rng(seed)
                vec = rng.standard_normal(self._dimension)
                norm = np.linalg.norm(vec)
                results.append((vec / norm).tolist())
            return results

    def embed_query(self, query: str) -> List[float]:
        return self.embed_texts([query])[0]
