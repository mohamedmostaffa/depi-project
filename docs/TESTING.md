# BrandMind Testing & Quality Assurance Plan (`docs/TESTING.md`)

**Project:** BrandMind × RLVNT  
**Testing Framework:** `pytest` (Pytest 9.2.0)  
**Pass Rate:** **100.0% Pass Rate** across Unit, Integration, Security, Evaluation, and UI suites.  
**Last Verified:** November 21, 2026

---

## 1. Test Architecture & Directory Structure

```
tests/
├── unit/
│   ├── test_schemas.py              # Pydantic V2 interface contract validation (5 tests)
│   ├── test_data_validation.py      # Structured catalog & policy consistency (4 tests)
│   ├── test_policy_engine.py        # Deterministic policy rules & day boundary tests (15 tests)
│   ├── test_tools.py                # 4 registered database tools & dispatcher (8 tests)
│   ├── test_memory.py               # Session memory sliding window & bilingual coreference (9 tests)
│   └── test_streamlit_app.py        # Streamlit UI turn execution & Arabic RTL helpers (2 tests)
├── integration/
│   ├── test_retrieval_isolation.py  # ChromaDB brand isolation (0% cross-brand leakage) (4 tests)
│   ├── test_api.py                  # FastAPI REST endpoints & HTTP contract verification (8 tests)
│   └── test_orchestrator.py         # End-to-end multi-turn pipeline integration (4 tests)
├── security/
│   ├── test_prompt_injection.py     # Delimiter breakout & system prompt protection (3 tests)
│   └── test_safety_escalation.py    # 100% recall on medical, legal & billing triggers (5 tests)
└── evaluation/
    └── test_evaluation_runner.py    # Benchmark runner, baselines & metric calculations (6 tests)
```

---

## 2. Comprehensive Test Execution Results

| Test Category | Test File | Scenarios | Passed | Failed | Status |
|---|---|---|---|---|---|
| **Unit Testing** | `tests/unit/test_schemas.py` | 5 | 5 | 0 | **PASSED** |
| | `tests/unit/test_data_validation.py` | 4 | 4 | 0 | **PASSED** |
| | `tests/unit/test_policy_engine.py` | 15 | 15 | 0 | **PASSED** |
| | `tests/unit/test_tools.py` | 8 | 8 | 0 | **PASSED** |
| | `tests/unit/test_memory.py` | 9 | 9 | 0 | **PASSED** |
| | `tests/unit/test_streamlit_app.py` | 2 | 2 | 0 | **PASSED** |
| **Integration Testing** | `tests/integration/test_retrieval_isolation.py` | 4 | 4 | 0 | **PASSED** |
| | `tests/integration/test_api.py` | 8 | 8 | 0 | **PASSED** |
| | `tests/integration/test_orchestrator.py` | 4 | 4 | 0 | **PASSED** |
| **Security & Safety** | `tests/security/test_prompt_injection.py` | 3 | 3 | 0 | **PASSED** |
| | `tests/security/test_safety_escalation.py` | 5 | 5 | 0 | **PASSED** |
| **Evaluation Suite** | `tests/evaluation/test_evaluation_runner.py` | 6 | 6 | 0 | **PASSED** |
| **TOTAL** | **Full System Test Suite** | **73** | **73** | **0** | **100.0% PASS** |

---

## 3. Test Execution Commands

### Run Full System Test Suite
```bash
py -m pytest tests/ -v
```

### Run Policy Engine Boundary Tests (Gate M4)
```bash
py -m pytest tests/unit/test_policy_engine.py -v
```

### Run Security & Prompt Injection Suite (Gate M5)
```bash
py -m pytest tests/security/ -v
```

### Run Evaluation Suite (Gate M6)
```bash
py -m pytest tests/evaluation/ -v
```

### Run 75-Scenario Stratified Benchmark
```bash
py -m src.evaluation.runner
```
