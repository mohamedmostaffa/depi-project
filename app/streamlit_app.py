"""
BrandMind × RLVNT — Streamlit Product UI & Real-Time Technical Inspector
Provides an authentic streetwear customer chat interface and live audit inspector side panel.
"""

import os
import re
import time
from datetime import date
from typing import Any, Dict, List, Optional
import requests
import streamlit as st

# Import internal pipeline for resilient offline/in-process fallback
from src.agents.orchestrator import AgentOrchestrator
from src.schemas import Decision, Dialect, Intent, Language

# ==============================================================================
# Page Configuration & Custom CSS Styling
# ==============================================================================

st.set_page_config(
    page_title="BrandMind × RLVNT | AI Customer Assistant",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

RLVNT_CUSTOM_CSS = """
<style>
/* Global Dark Streetwear Theme */
.stApp {
    background-color: #0E0E10;
    color: #F8F6F4;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}

/* Sidebar styling */
[data-testid="stSidebar"] {
    background-color: #16161A;
    border-right: 1px solid #2B2B32;
}

/* Brand Banner */
.brand-header {
    background: linear-gradient(135deg, #1A1A1E 0%, #2A1010 100%);
    border: 1px solid #8F1D1D;
    border-radius: 10px;
    padding: 18px 24px;
    margin-bottom: 20px;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.brand-title {
    font-size: 26px;
    font-weight: 800;
    letter-spacing: 2px;
    color: #FFFFFF;
    margin: 0;
}

.brand-badge {
    background-color: #8F1D1D;
    color: #FFFFFF;
    padding: 4px 10px;
    border-radius: 4px;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1px;
    text-transform: uppercase;
}

.demo-disclaimer {
    color: #A0A0A8;
    font-size: 12px;
    margin-top: 4px;
}

/* Inspector Cards */
.inspector-card {
    background-color: #1E1E24;
    border: 1px solid #2E2E38;
    border-radius: 8px;
    padding: 12px 14px;
    margin-bottom: 12px;
}

.inspector-title {
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: #8F1D1D;
    margin-bottom: 6px;
}

/* Badges */
.badge-eligible {
    background-color: rgba(46, 204, 113, 0.2);
    border: 1px solid #2ECC71;
    color: #2ECC71;
    padding: 4px 8px;
    border-radius: 4px;
    font-weight: 700;
    font-size: 12px;
}

.badge-not-eligible {
    background-color: rgba(231, 76, 60, 0.2);
    border: 1px solid #E74C3C;
    color: #E74C3C;
    padding: 4px 8px;
    border-radius: 4px;
    font-weight: 700;
    font-size: 12px;
}

.badge-needs-info {
    background-color: rgba(243, 156, 18, 0.2);
    border: 1px solid #F39C12;
    color: #F39C12;
    padding: 4px 8px;
    border-radius: 4px;
    font-weight: 700;
    font-size: 12px;
}

.badge-escalated {
    background-color: rgba(231, 76, 60, 0.3);
    border: 1px solid #FF3333;
    color: #FF5555;
    padding: 6px 10px;
    border-radius: 4px;
    font-weight: 700;
    font-size: 12px;
    animation: pulse 2s infinite;
}

/* Arabic RTL support */
.arabic-message {
    direction: rtl;
    text-align: right;
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    font-size: 15px;
    line-height: 1.6;
}

.english-message {
    direction: ltr;
    text-align: left;
    font-size: 14px;
    line-height: 1.5;
}
</style>
"""
st.markdown(RLVNT_CUSTOM_CSS, unsafe_allow_html=True)


# ==============================================================================
# Helper Functions & State Initialization
# ==============================================================================

def is_arabic_text(text: str) -> bool:
    """Checks whether text contains Arabic characters."""
    return bool(re.search(r"[\u0600-\u06FF]", text))


@st.cache_resource
def get_in_process_orchestrator() -> AgentOrchestrator:
    """Instantiates a single cached AgentOrchestrator for offline or fallback execution."""
    return AgentOrchestrator()


if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "Hey! Welcome to RLVNT. ⚡ I'm your AI customer assistant. Ask me anything about our heavyweight winter hoodies, sizing, care instructions, orders, or return policies!",
            "transparency": None,
        }
    ]

if "current_transparency" not in st.session_state:
    st.session_state.current_transparency = None

if "session_id" not in st.session_state:
    st.session_state.session_id = f"rlvnt_ui_{int(time.time())}"


# ==============================================================================
# Pipeline Dispatcher (FastAPI with In-Process Fallback)
# ==============================================================================

def execute_chat_turn(user_msg: str, backend_mode: str = "Auto") -> Dict[str, Any]:
    """Sends message to FastAPI REST backend if running, or falls back to in-process orchestrator."""
    api_url = os.getenv("API_URL", "http://127.0.0.1:8000/chat")

    # If backend mode is set to API or Auto, attempt HTTP request
    if backend_mode in ["FastAPI REST", "Auto"]:
        try:
            payload = {
                "brand_id": "rlvnt",
                "session_id": st.session_state.session_id,
                "message": user_msg,
            }
            resp = requests.post(api_url, json=payload, timeout=2.5)
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "reply": data.get("reply", ""),
                    "transparency": data.get("transparency", {}),
                    "source": "FastAPI Service",
                }
        except Exception:
            pass  # Fall through to in-process execution

    # In-Process Orchestrator Fallback
    orchestrator = get_in_process_orchestrator()
    turn_res = orchestrator.handle_turn(
        brand_id="rlvnt",
        session_id=st.session_state.session_id,
        message=user_msg,
    )

    return {
        "reply": turn_res.reply,
        "transparency": turn_res.transparency.model_dump(mode="json"),
        "source": "In-Process Agent",
    }


# ==============================================================================
# SIDEBAR: Real-Time Technical Inspector
# ==============================================================================

with st.sidebar:
    st.markdown("### 🛠️ Technical Inspector")
    st.caption("Live pipeline execution state & auditable transparency")

    # Connection Status & Control
    col_ctrl1, col_ctrl2 = st.columns([1, 1])
    with col_ctrl1:
        if st.button("🔄 Reset Chat", use_container_width=True):
            st.session_state.messages = [
                {
                    "role": "assistant",
                    "content": "Hey! Welcome to RLVNT. ⚡ I'm your AI customer assistant. Ask me anything about our hoodies, sizing, care, orders, or returns!",
                    "transparency": None,
                }
            ]
            st.session_state.current_transparency = None
            st.session_state.session_id = f"rlvnt_ui_{int(time.time())}"
            st.rerun()

    with col_ctrl2:
        backend_choice = st.selectbox(
            "Backend",
            ["Auto", "In-Process", "FastAPI REST"],
            index=0,
            label_visibility="collapsed",
        )

    t_data = st.session_state.current_transparency

    if t_data:
        # 1. Turn Latency & Pipeline Route
        latency = t_data.get("latency_ms", 0.0)
        st.markdown(
            f"""
            <div class="inspector-card">
                <div class="inspector-title">⚡ Performance & Route</div>
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span style="font-size: 20px; font-weight: 800; color: #FFFFFF;">{latency:.1f} <span style="font-size: 12px; color: #8F1D1D;">ms</span></span>
                    <span style="font-size: 11px; background: #2E2E38; padding: 2px 6px; border-radius: 4px;">{t_data.get("source", "In-Process")}</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # 2. Safety & Escalation Status
        is_esc = t_data.get("is_escalated", False)
        esc_reason = t_data.get("escalation_reason", "")
        if is_esc:
            st.markdown(
                f"""
                <div class="inspector-card" style="border-color: #E74C3C;">
                    <div class="inspector-title" style="color: #E74C3C;">🚨 Human Escalation Triggered</div>
                    <div class="badge-escalated">ESCALATED TO HUMAN AGENT</div>
                    <div style="font-size: 12px; color: #FF9999; margin-top: 6px;">Reason: {esc_reason}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                """
                <div class="inspector-card">
                    <div class="inspector-title">🛡️ Safety Guardrail</div>
                    <span style="color: #2ECC71; font-weight: 700; font-size: 12px;">✓ PASS (Autonomous Execution)</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

        # 3. Natural Language Understanding (NLU)
        intent = t_data.get("detected_intent", "Unknown")
        conf = t_data.get("confidence", 1.0) * 100
        lang = t_data.get("language", "en")
        dialect = t_data.get("dialect", "en")

        st.markdown(
            f"""
            <div class="inspector-card">
                <div class="inspector-title">🧠 Intent & Dialect</div>
                <div style="margin-bottom: 6px;">
                    <strong>Intent:</strong> <span style="color: #8F1D1D; font-weight: 700;">{intent.upper()}</span>
                    <span style="font-size: 11px; color: #888;">({conf:.0f}% conf)</span>
                </div>
                <div>
                    <strong>Language:</strong> {str(lang).upper()} | <strong>Dialect:</strong> {str(dialect).upper()}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # 4. Deterministic Policy Engine Decision
        pol_dec = t_data.get("policy_decision")
        if pol_dec:
            dec = pol_dec.get("decision", "needs_info")
            r_code = pol_dec.get("reason_code", "")
            r_text = pol_dec.get("reason_text", "")
            r_trace = pol_dec.get("rule_trace", [])

            badge_cls = (
                "badge-eligible"
                if dec == "eligible"
                else ("badge-not-eligible" if dec == "not_eligible" else "badge-needs-info")
            )

            st.markdown(
                f"""
                <div class="inspector-card">
                    <div class="inspector-title">⚖️ Deterministic Policy Engine</div>
                    <div style="margin-bottom: 8px;">
                        <span class="{badge_cls}">{dec.upper()}</span>
                        <span style="font-size: 11px; color: #BBB; margin-left: 6px;">[{r_code}]</span>
                    </div>
                    <div style="font-size: 12px; color: #DDD; margin-bottom: 8px;">{r_text}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            with st.expander("🔍 Rule Execution Trace"):
                for step in r_trace:
                    st.code(step, language="markdown")

        # 5. Tools Executed
        tools = t_data.get("tools_executed", [])
        if tools:
            with st.expander(f"⚙️ Executed Tools ({len(tools)})", expanded=True):
                for tool in tools:
                    st.markdown(f"**Tool:** `{tool.get('tool_name')}`")
                    st.caption(f"Success: {tool.get('success')} | Latency: {tool.get('latency_ms', 0):.1f}ms")
                    if tool.get("data"):
                        st.json(tool.get("data"))

        # 6. RAG Retrieved Context Chunks
        retrieved = t_data.get("retrieved_sources", [])
        if retrieved:
            with st.expander(f"📚 RAG Retrieved Context ({len(retrieved)})", expanded=False):
                for idx, chunk in enumerate(retrieved, 1):
                    cid = chunk.get("chunk_id", f"Chunk {idx}")
                    score = chunk.get("similarity_score", 0.0)
                    doc = chunk.get("source_file", "")
                    page = chunk.get("source_page", 0)
                    content = chunk.get("content", "")

                    st.markdown(f"**{idx}. [{cid}]** (Sim: `{score:.3f}`)")
                    st.caption(f"Source: `{doc}` (Page {page})")
                    st.text(content[:200] + ("..." if len(content) > 200 else ""))
                    st.divider()
    else:
        st.info("Send a message in the chat to inspect live pipeline transparency, RAG chunks, and deterministic rule traces.")


# ==============================================================================
# MAIN VIEW: RLVNT Brand Chat Interface
# ==============================================================================

# RLVNT Brand Header
st.markdown(
    """
    <div class="brand-header">
        <div>
            <h1 class="brand-title">RLVNT <span style="font-size: 16px; font-weight: 400; color: #8F1D1D;">STREETWEAR</span></h1>
            <div class="demo-disclaimer">⚡ BrandMind AI Customer Assistant | Heavyweight Cotton Apparel | Cairo, Egypt</div>
        </div>
        <div style="text-align: right;">
            <span class="brand-badge">SYNTHETIC DEMO</span>
            <div style="font-size: 11px; color: #888; margin-top: 4px;">DEPI AI Capstone</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# Quick Demonstration Suggestion Chips
st.markdown("<p style='font-size: 12px; color: #888; margin-bottom: 6px;'>💡 Quick Demo Scenarios (Click to test):</p>", unsafe_allow_html=True)
c1, c2, c3, c4 = st.columns(4)
with c1:
    if st.button("📦 Return Window (14 Days)", use_container_width=True):
        st.session_state.pending_prompt = "What is RLVNT's return window and policy?"
with c2:
    if st.button("🔍 Track Order RLVNT-1001", use_container_width=True):
        st.session_state.pending_prompt = "Can you check the delivery status of order RLVNT-1001?"
with c3:
    if st.button("🇪🇬 استبدال بمقاس أصغر (مصري)", use_container_width=True):
        st.session_state.pending_prompt = "وصلني هودي من ٨ أيام في أوردر RLVNT-1001 وعايز أبدله بمقاس لارج وهو لسه بالتيكت"
with c4:
    if st.button("🚨 Human Escalation Trigger", use_container_width=True):
        st.session_state.pending_prompt = "I developed a severe skin allergy and rash from this sweater. I need a medical review."

# Render Message Stream
for msg in st.session_state.messages:
    role = msg["role"]
    content = msg["content"]
    with st.chat_message(role, avatar="⚡" if role == "assistant" else "👤"):
        if is_arabic_text(content):
            st.markdown(f'<div class="arabic-message">{content}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="english-message">{content}</div>', unsafe_allow_html=True)

# Chat Input Handler
prompt = st.chat_input("Ask about sizing, wash care, order status, or exchange eligibility...")

# Handle Pending Button Chips
if "pending_prompt" in st.session_state and st.session_state.pending_prompt:
    prompt = st.session_state.pending_prompt
    st.session_state.pending_prompt = None

if prompt:
    # 1. Append User Message
    st.session_state.messages.append({"role": "customer", "content": prompt})
    with st.chat_message("customer", avatar="👤"):
        if is_arabic_text(prompt):
            st.markdown(f'<div class="arabic-message">{prompt}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="english-message">{prompt}</div>', unsafe_allow_html=True)

    # 2. Execute Turn via Pipeline
    with st.spinner("Processing turn with RAG & Policy Engine..."):
        result = execute_chat_turn(prompt, backend_mode=backend_choice)
        reply = result["reply"]
        transparency = result["transparency"]
        transparency["source"] = result.get("source", "In-Process")

    # 3. Append Assistant Reply & Update Inspector
    st.session_state.messages.append({"role": "assistant", "content": reply, "transparency": transparency})
    st.session_state.current_transparency = transparency

    with st.chat_message("assistant", avatar="⚡"):
        if is_arabic_text(reply):
            st.markdown(f'<div class="arabic-message">{reply}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="english-message">{reply}</div>', unsafe_allow_html=True)

    # Rerun to refresh inspector panel with latest state
    st.rerun()
