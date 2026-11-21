"""
Unit Tests for Semantic Chunker & Knowledge Processing
Phase 3 Quality Gate Tests
"""

import json
from pathlib import Path
import pytest

from src.ingestion.chunker import SemanticChunker, KnowledgeChunk


def test_chunker_generates_valid_chunks():
    """Verify chunker processes documents and writes valid JSONL records."""
    chunker = SemanticChunker(brand_id="rlvnt")
    chunks = chunker.process_and_save()

    assert len(chunks) >= 12, "Should generate at least 12 semantic chunks"
    
    output_path = Path("data/processed/rlvnt/chunks.jsonl")
    assert output_path.exists(), "chunks.jsonl must exist"

    with open(output_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
        assert len(lines) == len(chunks)
        for line in lines:
            data = json.loads(line)
            assert data["brand_id"] == "rlvnt"
            assert "chunk_id" in data
            assert "source_file" in data
            assert "source_page" in data
            assert "section" in data
            assert len(data["content"]) > 100
            assert data["content"].startswith("Brand: RLVNT")


def test_chunker_contains_critical_policy_clauses():
    """Verify that essential operational policy clauses are present in the chunks."""
    chunker = SemanticChunker(brand_id="rlvnt")
    chunks = chunker.process_and_save()

    all_text = " ".join(c.content.lower() for c in chunks)
    assert "14 days" in all_text, "Return window must be present in chunks"
    assert "unworn" in all_text, "Condition requirements must be present"
    assert "tags attached" in all_text, "Tag requirement must be present"
    assert "100% cotton" in all_text, "Fabric details must be present"
    assert "oversized" in all_text, "Silhouette details must be present"
