# BrandMind × RLVNT — Autonomous AI Customer-Service Architecture
**Digital Egypt Pioneers Initiative (DEPI) | AI & Data Science Capstone Project**

[![Python 3.14](https://img.shields.io/badge/Python-3.14-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com/)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-Vector_Store-orange.svg)](https://www.trychroma.com/)
[![Streamlit](https://img.shields.io/badge/Streamlit-UI_%26_Inspector-FF4B4B.svg)](https://streamlit.io/)
[![Pytest](https://img.shields.io/badge/Tests-73%2F73_Passing_(100%25)-brightgreen.svg)](docs/TESTING.md)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> **"Your brand, always on."**  
> An explainable, deterministic, secure, and evaluated AI customer-service architecture tailored for contemporary Egyptian streetwear brand **RLVNT**.

---

## 1. Executive Summary & Identity

BrandMind is an agentic AI customer-service system built to solve the operational crisis facing direct-to-consumer (DTC) fashion brands across Egypt and the MENA region. 

Unlike generic LLM wrappers that hallucinate policies and gamble with customer refunds, BrandMind enforces a **strict hybrid architecture**:
1. **The LLM extracts facts** and narrates responses in RLVNT's authentic streetwear brand voice.
2. **Pure, unit-tested Python evaluates business rules** (return windows, condition requirements, category exclusions).
3. **Structured database tools** inspect live inventory and synthetic orders.
4. **Bilingual NLP handlers** normalize Egyptian Arabic slang, numerals (`٠-٩` $\to$ `0-9`), and relative dates (`من ١٠ أيام` $\to$ ISO dates).
5. **Deterministic safety pre-checks** guarantee 100% escalation recall on medical complaints, legal disputes, and chargeback claims.

```
                              ┌─────────────────────────────────────────┐
                              │       Customer (Web / Mobile)           │
                              └────────────────────┬────────────────────┘
                                                   │
                                                   ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                   PRESENTATION LAYER (Streamlit)                                        │
│       • Streetwear Dark Theme               • Arabic RTL Support          • Real-Time Inspector Panel   │
└──────────────────────────────────────────────────┬──────────────────────────────────────────────────────┘
                                                   │ HTTP / In-Process
                                                   ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                  API & ORCHESTRATION LAYER (FastAPI)                                    │
│       • /chat        • /products        • /orders/{id}        • /returns/check        • /escalate       │
│                                                                                                         │
│       AgentOrchestrator.handle_turn() State Machine:                                                    │
│       [Safety Pre-Check] ──> [Bilingual NLU] ──> [Sliding Memory] ──> [RAG Retrieval] ──> [Tools] ──> [Jinja2 Generation]
└───────┬───────────────────────────────┬──────────────────────┬───────────────────────────────┬──────────┘
        │                               │                      │                               │
        ▼                               ▼                      ▼                               ▼
┌──────────────────┐          ┌──────────────────┐   ┌──────────────────┐            ┌──────────────────┐
│   NLU & MEMORY   │          │  RETRIEVAL (RAG) │   │  POLICY ENGINE   │            │  DATABASE TOOLS  │
│ • Dialect (EG/AR)│          │ • ChromaDB (HNSW)│   │ • Pure Python    │            │ • Catalog Search │
│ • Numeral Norm   │          │ • Cosine Dist    │   │ • 100% Auditable │            │ • Order Tracking │
│ • Sliding N=8    │          │ • Thresh = 0.30  │   │ • 14-Day Strict  │            │ • Synthetic DB   │
└──────────────────┘          └──────────────────┘   └──────────────────┘            └──────────────────┘
```

---

## 2. Non-Negotiable Engineering Rules (Golden Rules G1–G12)

BrandMind adheres strictly to 12 architectural constraints:

| Rule | Principle | Implementation Mechanism | Test Verification |
|---|---|---|---|
| **G1** | **No Hallucinated Business Facts** | Calibrated cosine similarity threshold (0.30) + Structured database tools | `tests/integration/test_orchestrator.py` |
| **G2** | **Deterministic Policy Decisions** | Pure, side-effect-free Python rule engine (`src/policies/engine.py`) | `tests/unit/test_policy_engine.py` (15/15 pass) |
| **G3** | **Context is Untrusted Data** | Delimited XML tags (`<context>`, `<message>`) preventing prompt injections | `tests/security/test_prompt_injection.py` |
| **G4** | **Tool Honesty** | The agent never claims an action occurred unless a tool returns success | `tests/unit/test_tools.py` (8/8 pass) |
| **G5** | **Escalation is a Valid Outcome** | Immediate human hand-off on safety, medical, legal, and dispute triggers | `tests/security/test_safety_escalation.py` (100% Recall) |
| **G6** | **Config Over Hardcoding** | Brand behavior driven by YAML (`config/rlvnt.yaml`) and vector chunks | `config/settings.yaml`, `config/rlvnt.yaml` |
| **G7** | **Brand Isolation** | Metadata enforcement `where={"brand_id": brand_id}` (0.0% data leakage) | `tests/integration/test_retrieval_isolation.py` |
| **G8** | **Synthetic Data Exclusively** | 50 synthetic orders (`data/structured/orders.csv`) — zero real PII | `data/README.md`, `src/ingestion/generate_orders.py` |
| **G9** | **Measured Claims Only** | All metrics derived from an automated 75-scenario benchmark runner | `docs/EVALUATION_REPORT.md`, `src/evaluation/runner.py` |
| **G10**| **AI Transparency** | The assistant identifies itself as an AI customer agent on initial turn | `src/prompts/templates/system_base.j2` |
| **G11**| **Explainable Architecture** | 10 Architectural Decision Records documenting trade-offs and rationale | `docs/DECISIONS.md` (ADR-001 through ADR-010) |
| **G12**| **Simulated Fulfillment** | Financial transactions and courier dispatch remain strictly simulated | `src/tools/order_tools.py` |

---

## 3. Empirical Evaluation Scorecard (75 Stratified Scenarios)

BrandMind was benchmarked against two baseline configurations across **75 curated scenarios** reflecting authentic Egyptian e-commerce interactions:
- **Config A (Direct LLM Baseline):** Standard prompt without retrieval, policy engine, or tools.
- **Config B (RAG-Only Baseline):** Vector retrieval enabled, but LLM makes return decisions.
- **Config C (Full BrandMind System):** Full hybrid architecture.

| Benchmark Metric | Config A (Direct LLM) | Config B (RAG-Only) | Config C (BrandMind Full) | Status |
|---|---|---|---|---|
| **Policy Decision Accuracy** | 0.0% | 20.0% | **100.0%** (15/15) | **PASSED (G2)** |
| **Safety Escalation Recall** | 0.0% | 0.0% | **100.0%** (10/10) | **PASSED (G5)** |
| **Hallucination Rate** | 28.0% | 0.0% | **0.0%** (0/75) | **PASSED (G1)** |
| **Tool Execution Accuracy** | 56.0% | 56.0% | **89.3%** (67/75) | **PASSED (G4)** |
| **Retrieval Hit@4** | 0.0% | 62.5% | **79.2%** | **PASSED** |
| **Retrieval MRR@4** | 0.000 | 0.457 | **0.535** | **PASSED** |
| **Intent Macro-F1** | N/A | N/A | **0.841** | **PASSED** |
| **Average Latency (ms)** | 0.02 ms | 593.1 ms | **30.7 ms** | **PASSED** |

*Full evaluation methodology and failure mode analysis available in [`docs/EVALUATION_REPORT.md`](docs/EVALUATION_REPORT.md).*

---

## 4. Quick Start & Execution Guide

### 4.1 Prerequisites & Installation
```bash
# Clone the repository
git clone https://github.com/youssefabady-7/Brand-mind2.git
cd Brand-mind2

# Create and activate virtual environment
py -m venv venv
venv\Scripts\activate   # On Windows

# Install dependencies
py -m pip install -r requirements.txt
```

### 4.2 Re-Index Knowledge Base (Optional)
```bash
# Ingests raw PDFs from data/raw/rlvnt/ and indexes into local ChromaDB
py -m src.retrieval.index_kb
```

### 4.3 Launch Streamlit Product UI & Inspector Panel
```bash
py -m streamlit run app/streamlit_app.py
```
*Open `http://localhost:8501` to test the customer chat interface and watch live rule traces in the Technical Inspector side panel.*

### 4.4 Launch FastAPI Microservice
```bash
py -m uvicorn src.api.app:app --host 127.0.0.1 --port 8000 --reload
```
*Interactive Swagger API documentation available at `http://127.0.0.1:8000/docs`.*

### 4.5 Run Complete Test Suite
```bash
# Executes 73 automated tests across unit, integration, security, and UI modules
py -m pytest tests/ -v
```

### 4.6 Execute 75-Scenario Benchmark Runner
```bash
py -m src.evaluation.runner
```

---

## 5. Repository Directory Layout

```
BRANDMIND/
├── .agents/skills/              # 10 specialized agent skill modules
├── app/
│   └── streamlit_app.py         # Streamlit chat interface & real-time technical inspector
├── config/
│   ├── rlvnt.yaml               # Brand identity, tone, and policy configuration
│   └── settings.yaml            # Retrieval thresholds, model weights, and system params
├── data/
│   ├── raw/rlvnt/               # 3 authoritative source PDFs
│   ├── processed/rlvnt/         # 14 semantic chunks (chunks.jsonl)
│   ├── structured/              # products.csv, policies.csv, orders.csv
│   └── evaluation/              # 75-scenario benchmark set (test_end_to_end.json)
├── docs/
│   ├── RLVNT_SOURCE_AUDIT.md    # Complete PDF audit & source-of-truth matrix
│   ├── DECISIONS.md             # ADR-001 through ADR-010 (Architectural Decision Records)
│   ├── EVALUATION_REPORT.md     # Empirical 3-tier comparative benchmark report
│   ├── AWS_BLUEPRINT.md         # Production enterprise cloud architecture & cost model
│   ├── DEMO_SCRIPT.md           # 10-step scripted defense walkthrough
│   ├── DEFENSE_PREP.md          # 23-slide presentation outline & technical Q&A guide
│   ├── PROGRESS.md              # Milestones M0–M6 tracker (All phases complete)
│   └── TESTING.md               # QA test suite execution report (100% pass)
├── results/
│   ├── audit_trace.jsonl        # Immutable execution traces (mode="json")
│   ├── evaluation_summary.json  # Benchmark metrics JSON
│   └── evaluation_traces.jsonl  # 75-scenario prediction traces
├── src/
│   ├── schemas.py               # Pydantic V2 interface contracts & domain models
│   ├── agents/
│   │   ├── orchestrator.py      # handle_turn() central state machine
│   │   └── understanding.py     # Intent, dialect, numeral & relative date NLP
│   ├── policies/
│   │   └── engine.py            # Pure Python deterministic business rule engine
│   ├── retrieval/
│   │   ├── embeddings.py        # Multilingual SentenceTransformer wrapper
│   │   ├── vector_store.py      # Persistent ChromaDB client with brand isolation
│   │   ├── hybrid_retriever.py  # Top-k retrieval & refusal threshold gating
│   │   └── index_kb.py          # Knowledge base indexing script
│   ├── tools/
│   │   ├── catalog_tools.py     # Product search tool
│   │   ├── order_tools.py       # Order tracking & return registration tools
│   │   ├── escalation_tools.py  # Human escalation tool
│   │   └── dispatcher.py        # Central schema-validated tool dispatcher
│   ├── memory/
│   │   └── session_manager.py   # Sliding window memory & coreference tracker
│   ├── prompts/
│   │   ├── template_manager.py  # Jinja2 template manager
│   │   └── templates/           # Layered Jinja2 prompt hierarchy
│   ├── api/
│   │   ├── app.py               # FastAPI application factory
│   │   └── routes.py            # REST API route handlers
│   └── evaluation/
│       ├── baselines.py         # Config A, B, C baseline runner implementations
│       ├── metrics.py           # EvaluationMetrics calculation suite
│       └── runner.py            # Comprehensive benchmark orchestrator
└── tests/                       # 73 automated pytest test cases
```

---

## 6. Author & Academic Attribution

- **Project Lead:** Youssef Abady (DEPI AI & Data Science Scholar)
- **Institution:** Digital Egypt Pioneers Initiative (DEPI)
- **Track:** AI & Data Science Specialist Track
- **Supervision & Review:** DEPI Academic & Industry Evaluation Panel (November 2026)
