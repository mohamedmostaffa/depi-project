---
name: deterministic-policy-engine
description: Designing, implementing, and unit testing 100% deterministic, side-effect-free Python business rule engines for e-commerce return/exchange eligibility.
---

# Deterministic Policy Engine Skill

## Purpose
This skill governs the pure Python business rules engine that determines return, exchange, and cancellation eligibility. In accordance with Golden Rule G2, the LLM NEVER independently decides eligibility; all decisions are computed deterministically.

## When to Activate
- Authoring or modifying business rules in `src/policies/`.
- Creating unit tests for return windows, garment condition, or category exclusions.
- Auditing policy decision logic and reason string generation.

## Technical Instructions
1. **Purity & Side-Effect Freedom:**
   - The engine must be a pure Python function: `check_return_eligibility(facts, policy, today) -> EligibilityResult`.
   - Never query system time directly; always inject `today: date` to ensure complete test determinism.
2. **Fixed Rule Trace Order:**
   - **Check 1 (Completeness):** Verify required fields (`purchase_date`, `condition`, `product_id`). If missing, return `Decision.NEEDS_INFO` with `missing_fields`.
   - **Check 2 (Order Existence):** Verify order exists in `orders.csv` and matches `brand_id`.
   - **Check 3 (Exclusions):** Verify item category is not in `non_returnable_categories` (e.g. final-sale clearance).
   - **Check 4 (Time Boundary):** Calculate `elapsed_days = (today - purchase_date).days`.
     - `elapsed_days <= allowed_days` $\rightarrow$ Pass.
     - `elapsed_days > allowed_days` $\rightarrow$ Fail (`OUTSIDE_WINDOW`).
     - Note: Day 14 is ELIGIBLE; Day 15 is NOT_ELIGIBLE on a 14-day policy.
   - **Check 5 (Condition):** Check garment condition (unworn, unwashed, tags attached, original packaging).
   - **Check 6 (Exceptions):** Check if item is defective or wrong delivery (100% brand-covered replacement/refund).
3. **Traceability:**
   - Return an explicit `EligibilityResult` dataclass with `decision`, `reason_code`, `reason_text`, and `rule_trace`.
   - The `reason_text` is the ONLY justification the LLM may narrate.

## Testing & Validation Checklist
- [ ] 100% test pass rate on unit test suite (`tests/unit/test_policy_engine.py`).
- [ ] Exact boundary testing: Day 0, Day 14 (eligible), Day 15 (not eligible).
- [ ] Edge cases tested: future purchase date, missing condition, non-returnable categories, defective item exceptions.
