# BrandMind Architectural Decision Records (`docs/DECISIONS.md`)

This document records key technical and architectural decisions, alternatives evaluated, trade-offs, and defense justifications for the DEPI Capstone evaluation panel.

---

## ADR-001: RLVNT as Primary Demonstration Brand over Lumora
- **Date:** November 20, 2026
- **Status:** ACCEPTED
- **Context:** The original capstone brief referenced Lumora (a skincare brand). The project owner selected RLVNT (contemporary streetwear and graphic apparel) with three authoritative PDF source documents.
- **Alternatives Considered:**
  1. Retain Lumora and skin-care hygiene policy exclusions.
  2. Synthetically adapt Lumora into fashion without real brand assets.
  3. Ground BrandMind fully in RLVNT's real streetwear identity, lookbooks, and policy guidelines.
- **Decision:** Ground BrandMind entirely in RLVNT. Strip all skincare, cosmetics, and hygiene exclusions. Use RLVNT's authentic oversized silhouettes, heavy cotton hoodies, and youth-oriented culture.
- **Defense for DEPI:** Demonstrates brand-agnostic software architecture (NFR-2). Applying BrandMind to an authentic Egyptian streetwear label proves real-world commercial viability for Egypt/MENA e-commerce.

---

## ADR-002: Deterministic Policy Engine vs. Autonomous LLM Decision-Making
- **Date:** November 20, 2026
- **Status:** ACCEPTED
- **Context:** E-commerce return and exchange decisions have legal and financial consequences. Probabilistic LLMs suffer from hallucination and prompt injection vulnerability.
- **Alternatives Considered:**
  1. Allow the LLM to decide return eligibility via system prompt instructions.
  2. Implement an autonomous ReAct loop with iterative tool calls.
  3. Implement a pure, side-effect-free Python decision engine where the LLM only extracts facts and narrates the engine's deterministic decision.
- **Decision:** Option 3. Golden Rule G2 enforces strict deterministic Python evaluation.
- **Defense for DEPI:** The LLM is probabilistic; business policies are deterministic. In production e-commerce, automated financial decisions must be 100% auditable, repeatable, and unit-tested. Separating reasoning (LLM) from evaluation (Python) eliminates policy hallucination.

---

## ADR-003: Vector Database Selection (ChromaDB)
- **Date:** November 20, 2026
- **Status:** ACCEPTED
- **Context:** The project operates under zero-infrastructure cost constraints while needing persistent storage and metadata filtering.
- **Alternatives Considered:**
  1. Pinecone / Weaviate / Qdrant Cloud (requires external hosted API credentials, subject to quotas/costs).
  2. In-memory FAISS (lacks native metadata filtering and persistent storage).
  3. ChromaDB PersistentClient (embedded, zero cloud cost, local file persistence, native metadata filtering).
- **Decision:** ChromaDB embedded PersistentClient with explicit cosine space (`hnsw:space: cosine`).
- **Defense for DEPI:** ChromaDB provides zero-cost local persistence, runs on consumer hardware, supports strict metadata filtering by `brand_id`, and requires no network overhead or external infrastructure.

---

## ADR-004: Multilingual Embeddings for Egyptian Arabic & English
- **Date:** November 20, 2026
- **Status:** ACCEPTED
- **Context:** Customer messages in Egypt arrive in English, Modern Standard Arabic (MSA), Egyptian Arabic, and Franco-Arabic. The default `all-MiniLM-L6-v2` is English-centric.
- **Alternatives Considered:**
  1. `all-MiniLM-L6-v2` (high speed, but poor recall on colloquial Egyptian Arabic).
  2. `paraphrase-multilingual-MiniLM-L12-v2` (strong bilingual performance, lightweight 384-dim).
  3. `intfloat/multilingual-e5-small` (strong multilingual semantics, requires query/doc prefixes).
- **Decision:** Use `paraphrase-multilingual-MiniLM-L12-v2` as the default embedding model, keeping model selection configurable via `config/settings.yaml`.
- **Defense for DEPI:** Egyptian Arabic customer service requires semantic alignment across English catalog terms ("hoodie", "drop", "return") and colloquial Arabic queries ("عايز أرجع الهودي"). Multilingual Sentence Transformers bridge this cross-lingual gap locally without API costs.

---

## ADR-005: Pydantic V2 as System-Wide Interface Contract
- **Date:** November 20, 2026
- **Status:** ACCEPTED
- **Context:** To ensure clean separation between the 6 architectural layers and enable modular development, all cross-module data must adhere to strict schemas.
- **Alternatives Considered:**
  1. Plain Python dictionaries (untyped, prone to runtime key errors, no data validation).
  2. Standard library `@dataclass` (typed, but lacks runtime coercion, serialization, and regex validation).
  3. Pydantic V2 models (`src/schemas.py`).
- **Decision:** Standardize all inputs, tool payloads, and turn outputs on Pydantic V2 (`BaseModel`).
- **Defense for DEPI:** Pydantic provides runtime validation, automatic type coercion, native JSON schema export for LLM structured output, and seamless integration with FastAPI.
