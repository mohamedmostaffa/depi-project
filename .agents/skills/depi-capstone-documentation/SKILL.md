---
name: depi-capstone-documentation
description: Generating defense-ready DEPI documentation, architectural decision records (ADRs), source audit matrices, and presentation scripts.
---

# DEPI Capstone Documentation Skill

## Purpose
This skill establishes guidelines for maintaining defense-grade project documentation, traceability matrices, Architectural Decision Records (ADRs), and live demonstration materials required for the DEPI Capstone evaluation.

## When to Activate
- Authoring or updating files in `docs/` (`PROGRESS.md`, `DECISIONS.md`, `TESTING.md`, `RLVNT_SOURCE_AUDIT.md`, `ARCHITECTURE.md`).
- Preparing the 23-slide final presentation outline and 10-minute live demo script.
- Documenting AWS production cloud architecture mappings.

## Technical Instructions
1. **Continuous Documentation Discipline:**
   - Update `docs/PROGRESS.md` immediately upon phase completion or status change.
   - For every architectural decision, add an ADR entry in `docs/DECISIONS.md` explaining: Context, Alternatives Considered, Decision, Rationale, and Trade-offs.
   - Never allow documentation to drift from the actual running codebase.
2. **Honest Status Labelling:**
   - Explicitly label every system feature as `PLANNED`, `IMPLEMENTED`, or `VALIDATED`.
   - Never mark an untested feature as validated. If a benchmark or test was not run, mark it `NOT RUN`.
3. **DEPI Presentation & Defense Preparation:**
   - Maintain a 10-step scripted demo walkthrough in `docs/DEMO_SCRIPT.md` with anticipated panel questions and rigorous technical defenses (e.g., Why RAG? Why deterministic rules over LLM agents? How is prompt injection prevented?).

## Testing & Validation Checklist
- [ ] All cross-references and markdown links resolve correctly.
- [ ] No placeholder or unverified claims in published documentation.
- [ ] Rehearsed 10-step demo script with backup contingency plan documented.
