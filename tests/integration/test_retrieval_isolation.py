"""
Integration Tests for RAG Retrieval, Brand Isolation & Refusal Threshold
Phase 4 & Phase 5 Quality Gate Tests
"""

import pytest

from src.retrieval.hybrid_retriever import HybridRetriever
from src.retrieval.vector_store import VectorStore


@pytest.fixture(scope="module")
def retriever():
    store = VectorStore(persist_dir="./chroma_db")
    return HybridRetriever(vector_store=store)


def test_retrieval_english_policy_query(retriever):
    """Verify English return policy query retrieves the official returns chunk."""
    res = retriever.retrieve(query="What is your return window and policy?", brand_id="rlvnt", k=4)
    assert res.is_covered is True
    assert len(res.chunks) > 0
    assert res.top_similarity >= 0.35

    content_blob = " ".join(c.content.lower() for c in res.chunks)
    assert "14 days" in content_blob
    assert "unworn" in content_blob


def test_retrieval_egyptian_arabic_exchange_query(retriever):
    """Verify Egyptian Arabic query retrieves the relevant exchange and return chunk."""
    res = retriever.retrieve(query="عايز أبدل مقاس الهودي بمقاس تاني", brand_id="rlvnt", k=4)
    assert res.is_covered is True
    assert len(res.chunks) > 0
    assert res.top_similarity >= 0.35

    top_chunk = res.chunks[0]
    assert top_chunk.brand_id == "rlvnt"
    assert "exchange" in top_chunk.content.lower() or "return" in top_chunk.content.lower() or "hoodie" in top_chunk.content.lower()


def test_zero_cross_brand_leakage(retriever):
    """Verify that querying for a different brand returns ZERO chunks (Golden Rule G7)."""
    res = retriever.retrieve(query="return policy", brand_id="non_existent_brand", k=4)
    assert len(res.chunks) == 0
    assert res.is_covered is False


def test_out_of_domain_refusal_threshold(retriever):
    """Verify that unrelated out-of-domain queries trigger threshold refusal."""
    res = retriever.retrieve(
        query="What is the chemical composition of volcanic basalt rocks?",
        brand_id="rlvnt",
        k=4
    )
    # The top similarity for unrelated queries is ~0.05, well below calibrated threshold of 0.30
    assert res.is_covered is False
    assert res.top_similarity < 0.30
