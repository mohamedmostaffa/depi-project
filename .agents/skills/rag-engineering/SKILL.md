---
name: rag-engineering
description: Multilingual embeddings, ChromaDB configuration with cosine distance, metadata filtering, chunking strategies, and similarity threshold calibration.
---

# RAG Engineering Skill

## Purpose
This skill defines standards for embedding generation, vector indexing, persistent ChromaDB storage, brand isolation, semantic retrieval, and similarity threshold calibration.

## When to Activate
- Ingesting chunks into the vector store (`chroma_db/`).
- Configuring embedding models (`paraphrase-multilingual-MiniLM-L12-v2` or `multilingual-e5-small`).
- Implementing or tuning the `retrieve(query, brand_id, k)` retrieval pipeline.
- Calibrating similarity refusal thresholds on answerable vs. unanswerable query sets.

## Technical Instructions
1. **ChromaDB Configuration:**
   - Always initialize `chromadb.PersistentClient(path=...)`.
   - Explicitly configure collection distance as cosine: `metadata={"hnsw:space": "cosine"}`.
   - Note: Chroma returns cosine *distance* ($d \in [0, 2]$); convert to cosine *similarity* ($s = 1 - d$) before threshold evaluation.
2. **Metadata Filtering & Isolation:**
   - Every collection query MUST include `where={"brand_id": brand_id}`.
   - Never perform cross-brand vector searches. Target: 0% data leakage.
3. **Chunking Principles:**
   - Chunks must follow logical policy boundaries (single FAQ entry, distinct care step, or policy clause).
   - Target size: 200–400 tokens with 10–15% overlap.
   - Prepend every chunk with contextual metadata: `Brand: {brand_name} | Doc: {doc_name} | Section: {section_title}`.
4. **Threshold Refusal:**
   - If `top_similarity < SIMILARITY_THRESHOLD`, flag retrieval as `uncovered` to trigger explicit refusal/escalation.

## Testing & Validation Checklist
- [ ] Unit test: Verify cross-brand retrieval yields 0 results when querying Brand A for Brand B's data.
- [ ] Unit test: Verify cosine similarity conversion logic.
- [ ] Benchmark: Gold chunk retrieval in top-4 $\ge 85\%$.
