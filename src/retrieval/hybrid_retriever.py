"""
BrandMind — Hybrid RAG Retriever & Threshold Refusal System
Retrieves top-k chunks, calculates calibrated similarity, and enforces refusal on uncovered queries.
"""

from typing import List, Optional
import yaml

from src.retrieval.vector_store import VectorStore
from src.schemas import RetrievalResult, RetrievedChunk


class HybridRetriever:
    def __init__(
        self,
        vector_store: Optional[VectorStore] = None,
        config_path: str = "config/settings.yaml",
    ):
        self.vector_store = vector_store or VectorStore()
        self.config_path = config_path
        self.similarity_threshold = 0.65
        self.top_k = 4
        self._load_config()

    def _load_config(self):
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                cfg = yaml.safe_load(f)
                ret_cfg = cfg.get("retrieval", {})
                self.similarity_threshold = float(ret_cfg.get("similarity_threshold", 0.65))
                self.top_k = int(ret_cfg.get("top_k", 4))
        except Exception:
            pass

    def retrieve(
        self,
        query: str,
        brand_id: str,
        k: Optional[int] = None,
    ) -> RetrievalResult:
        """Retrieves top-k chunks and evaluates similarity against the refusal threshold."""
        if not brand_id:
            raise ValueError("brand_id is mandatory for retrieval")

        limit = k or self.top_k
        chunks = self.vector_store.query(query_text=query, brand_id=brand_id, top_k=limit)

        top_score = chunks[0].similarity_score if chunks else 0.0
        is_covered = bool(chunks and top_score >= self.similarity_threshold)

        return RetrievalResult(
            query=query,
            brand_id=brand_id,
            chunks=chunks,
            is_covered=is_covered,
            top_similarity=top_score,
        )

    @staticmethod
    def format_context_for_prompt(chunks: List[RetrievedChunk]) -> str:
        """Formats retrieved chunks into clean, cited reference text for the generator."""
        if not chunks:
            return "No verified brand documents available for this query."

        formatted_parts = []
        for idx, chunk in enumerate(chunks, 1):
            source_citation = f"[S{idx}: {chunk.source_file} (Page {chunk.source_page}) | {chunk.section}]"
            formatted_parts.append(f"{source_citation}\n{chunk.content}")

        return "\n\n".join(formatted_parts)
