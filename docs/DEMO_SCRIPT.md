# BrandMind × RLVNT — Live Demonstration Script (`docs/DEMO_SCRIPT.md`)
**DEPI AI & Data Science Capstone | Scripted 10-Step Defense Demonstration**

---

## 1. Demonstration Setup & Pre-Flight Checklist

Before presenting to the DEPI evaluation panel, verify the following:

- [ ] Terminal 1: FastAPI Microservice running (optional, or in-process mode):
  ```bash
  py -m uvicorn src.api.app:app --host 127.0.0.1 --port 8000
  ```
- [ ] Terminal 2: Streamlit Product UI running:
  ```bash
  py -m streamlit run app/streamlit_app.py
  ```
- [ ] Browser window opened to `http://localhost:8501` with sidebar expanded.
- [ ] Reset button clicked (`🔄 Reset Chat`) to ensure a fresh session.

---

## 2. 10-Step Scripted Demonstration Walkthrough

### Step 1: Brand Greeting & AI Identity Transparency (Enforcing G10)
- **Presenter Prompt:** `"Hello! Who are you and what do you do?"`
- **What to Explain to Panel:**
  > *"Notice Golden Rule G10 in action: The assistant immediately identifies itself as an AI assistant for RLVNT, setting clear customer expectations without impersonating a human employee."*
- **Inspector Panel Verification:**
  - `Intent`: `PRODUCT_INFO` / `GENERAL`
  - `Language`: `EN`
  - `Safety Guardrail`: `PASS`

---

### Step 2: Factual Brand & Garment Care FAQ (Grounded RAG Retrieval)
- **Presenter Prompt:** `"How should I wash and care for my graphic streetwear hoodie to keep the print intact?"`
- **Expected Response:**
  - Explains turning inside out, washing at max 30°C on gentle cycle, avoiding bleach, and hang drying in the shade.
- **What to Explain to Panel:**
  > *"The assistant did not invent care advice. In the inspector panel, you can see chunk `RLVNT-GOV-P06-02` retrieved from Page 6 of the official RLVNT Brand Identity & Policies PDF with a cosine similarity score of ~0.42. The `<context>` is treated as untrusted data (G3)."*
- **Inspector Panel Verification:**
  - `Retrieved Chunks`: `RLVNT-GOV-P06-02` (Page 6)
  - `Policy Engine`: None (Informational Turn)

---

### Step 3: Structured Catalog Lookup (Tool Execution)
- **Presenter Prompt:** `"Tell me about the Lionel Messi signature hoodie and how much it costs."`
- **Expected Response:**
  - Confirms Lionel Messi 100% Cotton Signature Hoodie, 1650 EGP, available sizes S–XXL, heavyweight cotton fabric with gold foil print.
- **What to Explain to Panel:**
  > *"To prevent pricing hallucinations (Golden Rule G1), BrandMind calls `search_products` against our structured product catalog (`data/structured/products.csv`). Vector search is never used for exact numerical prices."*
- **Inspector Panel Verification:**
  - `Executed Tools`: `search_products(query="Lionel Messi...")` $\to$ Success: `True`

---

### Step 4: Synthetic Order Tracking (Tool Execution)
- **Presenter Prompt:** `"Can you check the delivery status of order RLVNT-1001?"`
- **Expected Response:**
  - Confirms order RLVNT-1001 is `DELIVERED`, shipped to Nasr City, Cairo, with synthetic total amount 1650 EGP.
- **What to Explain to Panel:**
  > *"Enforcing Golden Rule G4 (Tool Honesty): The agent only claims an order is checked because the registered `get_order_status` tool executed against our synthetic order store."*
- **Inspector Panel Verification:**
  - `Executed Tools`: `get_order_status(order_id="RLVNT-1001")` $\to$ Status: `DELIVERED`

---

### Step 5: Multi-Turn Coreference Resolution (Session Memory)
- **Presenter Prompt:** `"Can I exchange it for a smaller size?"`
- **What to Explain to Panel:**
  > *"Notice the customer said 'it' instead of repeating the order ID or product name. Our `SessionManager` inspects the sliding history window ($N=8$) and resolves 'it' to order `RLVNT-1001` automatically across turns."*
- **Inspector Panel Verification:**
  - `Extracted Entities`: `order_id="RLVNT-1001"`, `request_type="exchange"`

---

### Step 6: 100% Deterministic Policy Evaluation (Eligible Case)
- **Presenter Prompt:** `"I received order RLVNT-1001 8 days ago. The hoodie is unworn with original tags attached. Can I exchange it?"`
- **Expected Response:**
  - Confirms eligibility under the 14-day policy. Explains customer covers standard exchange courier fee.
- **What to Explain to Panel:**
  > *"Notice the inspector side panel: The LLM did not make this decision! The pure Python `PolicyEngine` executed Rule 1 (Order lookup), Rule 2 (Category check), Rule 4 (8 days $\le$ 14 days), and Rule 5 (Condition unworn with tags). The decision is 100% auditable and deterministic (G2)."*
- **Inspector Panel Verification:**
  - `Decision Badge`: `ELIGIBLE` (Green)
  - `Reason Code`: `ELIGIBLE_EXCHANGE`
  - `Rule Trace`: Complete 5-step trace

---

### Step 7: 100% Deterministic Policy Evaluation (Ineligible Case)
- **Presenter Prompt:** `"My order RLVNT-1003 was delivered 16 days ago. Can I still return it? The tags are still attached."`
- **Expected Response:**
  - Politely refuses return: Delivered 16 days ago, exceeding RLVNT's strict 14-day return window.
- **What to Explain to Panel:**
  > *"As shown in our benchmark report, direct LLMs and RAG-only systems frequently suffer from boundary errors here, leniently approving Day 15 or 16 returns. Our deterministic Python engine guarantees zero drift: 16 days > 14 days strictly outputs NOT_ELIGIBLE."*
- **Inspector Panel Verification:**
  - `Decision Badge`: `NOT_ELIGIBLE` (Red)
  - `Reason Code`: `OUTSIDE_WINDOW`

---

### Step 8: Colloquial Egyptian Arabic Inquiry (Bilingual Normalization)
- **Presenter Prompt:** `"وصلني هودي من ٨ أيام في أوردر RLVNT-1001 وعايز أبدله بمقاس لارج وهو مش ملبوس وبالتيكت"`
- **Expected Response:**
  - Natural Egyptian Arabic confirmation in RLVNT's authentic streetwear tone.
- **What to Explain to Panel:**
  > *"BrandMind seamlessly handles Egyptian Arabic colloquial dialect (`ar_eg`), automatically converting Arabic-Indic numerals (`٨` $\to$ `8`), computing relative dates in Python, and detecting condition tokens (`مش ملبوس وبالتيكت`)."*
- **Inspector Panel Verification:**
  - `Language`: `AR`
  - `Dialect`: `EGYPTIAN`
  - `Arabic RTL Styling`: Injected in chat bubble

---

### Step 9: Out-of-Domain Refusal (Calibrated Similarity Threshold)
- **Presenter Prompt:** `"Do you sell leather motorcycle boots and crash helmets?"`
- **Expected Response:**
  - Polite refusal: RLVNT is an apparel brand specializing in streetwear hoodies and crewnecks.
- **What to Explain to Panel:**
  > *"Because our cosine similarity threshold is calibrated to 0.30, the retriever flags this query as uncovered (`is_covered=False`). The orchestrator triggers an ActionType.REFUSE without hallucinating."*
- **Inspector Panel Verification:**
  - `Covered`: `False` (Top similarity < 0.30)
  - `Action Type`: `REFUSE`

---

### Step 10: Critical Safety & Human Escalation (Enforcing G5 with 100% Recall)
- **Presenter Prompt:** `"I broke out in a severe skin allergy and burning rash after wearing your sweater. I need a medical review!"`
- **Expected Response:**
  - Immediate escalation message connecting the customer with the human medical/support desk.
- **What to Explain to Panel:**
  > *"Golden Rule G5: Human Escalation is a Valid and Safe Outcome. Hard-coded safety pre-checks bypass model generation completely, preventing harmful speculative medical advice. Our benchmark achieved 100.0% recall across all safety test cases."*
- **Inspector Panel Verification:**
  - `🚨 Human Escalation Triggered`: `True`
  - `Escalation Reason`: `Matched critical escalation trigger: 'rash'`
  - `Tool Executed`: `escalate_to_human`

---

## 3. Contingency & Backup Plan (Failure Mitigation)

If live network connectivity or external servers fail during the presentation:
1. **FastAPI Disconnection:** The Streamlit UI automatically detects API timeouts and switches to the embedded in-process `AgentOrchestrator` in 0 milliseconds without disrupting the demonstration.
2. **Offline Sentence-Transformers:** The embedding model and ChromaDB collection are fully persisted locally in `./chroma_db`, requiring zero internet connectivity.
3. **Mock LLM Fallback:** The orchestrator features an offline deterministic generator (`src/llm/mock_client.py`), ensuring that demo responses and policy traces render perfectly even in airplane mode.
