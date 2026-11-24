---
name: agent-orchestration
description: Engineering constrained agent pipelines (handle_turn), tool dispatching, observation handling, and auditable JSONL execution logging.
---

# Agent Orchestration Skill

## Purpose
This skill governs the sequential orchestration pipeline that processes each customer conversation turn. It maintains a deterministic, predictable state machine rather than an unconstrained, unpredictable autonomous loop.

## When to Activate
- Authoring or modifying `src/agents/orchestrator.py`.
- Adding or modifying agent tools and observation handlers.
- Configuring the turn execution trace and session memory flow.

## Technical Instructions
1. **Pipeline Execution Flow (`handle_turn`):**
   - **Step 1:** Load brand configuration (`config/<brand>.yaml`) and session memory (`N` turns).
   - **Step 2 (Hard Pre-Checks):** Scan user message against regex/keyword lists for immediate escalation (explicit human request, safety complaint, legal dispute). If matched, bypass NLU and normal tools, execute the escalation tool, then still use Gemini to generate the customer-facing status message. Never fall back to a canned message.
   - **Step 3 (Understanding):** Execute a single structured LLM call to extract intent, language, dialect, entities, and sentiment.
   - **Step 4 (Normalization & Coreference):** Convert Arabic digits, resolve relative dates via Python, and map coreferences ("the black one" $\rightarrow$ previous product).
   - **Step 5 (Retrieval):** Query vector store for prose policy (`retrieve`) and structured catalog/order services for exact facts.
   - **Step 6 (Decision):** If eligibility or tools are required, execute deterministic tool functions and capture typed observations.
   - **Step 7 (Generation):** Invoke the LLM with layered Jinja2 prompts, passing retrieved context and tool observations inside XML delimiters.
   - **Step 8 (Post-Checks & Logging):** Validate groundedness, record full JSONL execution trace, and update sliding memory window.
2. **Constrained Agent Principles:**
   - The LLM does NOT decide on arbitrary execution loops. Execution order is fixed, predictable, and fully auditable.
   - Never report a tool action to the customer without a verified tool execution result in `observations`.

## Testing & Validation Checklist
- [ ] End-to-end integration test passes for all standard customer turns.
- [ ] Full JSONL audit trace emitted per turn with latency and tool metadata.
- [ ] Tool errors degrade gracefully to honest customer refusal/escalation.
