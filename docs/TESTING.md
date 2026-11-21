# BrandMind Testing & Quality Assurance Plan (`docs/TESTING.md`)

**Project:** BrandMind × RLVNT  
**Testing Framework:** `pytest`  
**Target Coverage:** 100% on deterministic business policies; >90% on API contracts and interfaces.

---

## 1. Test Architecture & Directory Structure

```
tests/
├── unit/
│   ├── test_schemas.py              # Pydantic contract validation tests
│   ├── test_policy_engine.py        # Business policy rule evaluation & boundary checks
│   ├── test_tools.py                # Tool schema validation & mock executions
│   └── test_memory.py               # Session memory sliding window & coreference
├── integration/
│   ├── test_retrieval_isolation.py  # ChromaDB brand isolation (0% cross-brand leakage)
│   ├── test_orchestrator.py         # End-to-end turn flow execution
│   └── test_api.py                  # FastAPI route integration tests
├── security/
│   ├── test_prompt_injection.py     # Delimiter breakout & system prompt protection
│   └── test_safety_escalation.py    # 100% recall on critical safety & legal triggers
└── evaluation/
    └── test_benchmarks.py           # Metric calculation verification
```

---

## 2. Test Execution Commands

### Run Complete Test Suite
```bash
py -m pytest tests/ -v
```

### Run Unit Tests Only
```bash
py -m pytest tests/unit/ -v
```

### Run Security & Red-Team Tests
```bash
py -m pytest tests/security/ -v
```

### Run With Coverage Report
```bash
py -m pytest --cov=src tests/ --cov-report=term-missing
```

---

## 3. Current Test Execution Results (Phase 1 Baseline)

| Test File | Tests Run | Passed | Failed | Status |
|---|---|---|---|---|
| `tests/unit/test_schemas.py` | 5 | 5 | 0 | **VALIDATED** |
| `tests/unit/test_data_validation.py` | 4 | 4 | 0 | **VALIDATED** |
| **Total Unit Tests** | **9** | **9** | **0** | **VALIDATED (100% PASS)** |

*All Phase 1 baseline contract tests pass.*
