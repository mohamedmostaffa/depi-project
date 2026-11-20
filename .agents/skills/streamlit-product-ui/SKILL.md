---
name: streamlit-product-ui
description: Developing responsive customer chat frontends with real-time technical inspector side panels and Arabic RTL rendering.
---

# Streamlit Product UI Skill

## Purpose
This skill governs the presentation layer (`app/streamlit_app.py`), delivering a production-grade user experience for demonstration panels, customers, and evaluators.

## When to Activate
- Authoring or enhancing the Streamlit customer chat interface.
- Integrating the real-time technical inspector side panel.
- Configuring custom CSS styling for RLVNT branding and Arabic Right-to-Left (RTL) support.

## Technical Instructions
1. **User Interface Structure:**
   - **Main Chat Window:** RLVNT brand header, conversation stream, loading spinners, and synthetic demo badge.
   - **Inspector Side Panel:** Real-time visibility into the system's inner workings:
     - Detected intent and confidence score.
     - Detected language and dialect.
     - Retrieved context snippets with similarity scores and page numbers.
     - Tools invoked, arguments, and return status.
     - Rule engine decision trace (`ELIGIBLE` / `NOT_ELIGIBLE` / `NEEDS_INFO`).
     - Safety/Escalation status and trigger reason.
     - Turn latency (in milliseconds).
2. **Arabic RTL Styling:**
   - Inject custom CSS using `st.markdown('<style>...</style>', unsafe_allow_html=True)` to ensure Arabic messages render cleanly right-to-left (`direction: rtl; text-align: right;`).
3. **Resilience & Fallback:**
   - Connect to the FastAPI backend by default.
   - Provide an in-process direct Python pipeline fallback so the demo remains functional if the external API process is offline.

## Testing & Validation Checklist
- [ ] UI loads cleanly without errors or layout shifts.
- [ ] Arabic and English text render with correct alignment.
- [ ] Technical inspector side panel updates dynamically after every turn.
- [ ] In-process fallback executes smoothly when API is disconnected.
