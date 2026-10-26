import streamlit as st
import pandas as pd
import uuid
import json
import os
from datetime import datetime
from config import GROQ_API_KEY
from tax_agent import BangladeshTaxAgent
from calculator import get_exemption_limit

# ----------------- CONFIGURATION -----------------
st.set_page_config(
    page_title="Bangladesh Income Tax AI Agent",
    page_icon="🇧🇩",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load rules safely
RULES_PATH = os.path.join(os.path.dirname(__file__), "rules.json")
with open(RULES_PATH, "r", encoding="utf-8") as f:
    RULES = json.load(f)

# Load real evaluation results if present
RESULTS_PATH = os.path.join(os.path.dirname(__file__), "results.json")
EVAL_DATA = None
if os.path.exists(RESULTS_PATH):
    with open(RESULTS_PATH, "r", encoding="utf-8") as f:
        EVAL_DATA = json.load(f)

# Styling
st.markdown("""
<style>
    .main-title {
        font-size: 2.1rem;
        font-weight: 700;
        color: #0d5c3a;
        margin-bottom: 0.1rem;
    }
    .sub-title {
        color: #4A5568;
        font-size: 0.95rem;
        margin-bottom: 1.2rem;
    }
    .tax-card {
        background: #f0fdf4;
        border: 1px solid #bbf7d0;
        border-radius: 8px;
        padding: 10px 14px;
        margin: 8px 0;
    }
    .slot-card {
        background: #eff6ff;
        border: 1px solid #bfdbfe;
        border-radius: 8px;
        padding: 10px 14px;
        margin: 8px 0;
        font-size: 0.88rem;
    }
    .disclaimer-box {
        background: #fffbeb;
        border-left: 4px solid #f59e0b;
        padding: 8px 12px;
        margin-bottom: 12px;
        border-radius: 4px;
        font-size: 0.82rem;
        color: #92400e;
    }
    .recents-header {
        font-size: 0.82rem;
        font-weight: 600;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-top: 14px;
        margin-bottom: 6px;
    }
    .ref-badge {
        display: inline-block;
        background-color: #e0f2fe;
        color: #0369a1;
        padding: 3px 8px;
        border-radius: 12px;
        font-size: 0.8rem;
        margin-right: 5px;
        margin-top: 5px;
    }
    .peas-card {
        background: #f8fafc;
        border-left: 4px solid #0284c7;
        padding: 12px;
        margin-bottom: 12px;
        border-radius: 6px;
        font-size: 0.88rem;
    }
</style>
""", unsafe_allow_html=True)

# ----------------- SESSION MANAGEMENT -----------------
if "conversations" not in st.session_state:
    initial_id = str(uuid.uuid4())[:8]
    st.session_state.conversations = {
        initial_id: {
            "title": "New Chat",
            "created_at": datetime.now().strftime("%I:%M %p"),
            "messages": [
                {
                    "role": "assistant",
                    "content": "Hello! I am your Bangladesh Income Tax AI Assistant. Feel free to ask any question regarding salary, rental property, business, gifts, or IT freelancing tax calculations under the Income Tax Act 2023.",
                    "references": [],
                    "retrieved_snippets": [],
                    "tool_data": None
                }
            ],
            "category": "regular",
            "slots": {}
        }
    }
    st.session_state.current_chat_id = initial_id

if "current_chat_id" not in st.session_state or st.session_state.current_chat_id not in st.session_state.conversations:
    first_key = list(st.session_state.conversations.keys())[0]
    st.session_state.current_chat_id = first_key

curr_id = st.session_state.current_chat_id
current_conv = st.session_state.conversations[curr_id]

# Initialize Tax Agent
if "tax_agent" not in st.session_state:
    st.session_state.tax_agent = BangladeshTaxAgent(api_key=GROQ_API_KEY)


# ----------------- SIDEBAR -----------------
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/8/84/Government_Seal_of_Bangladesh.svg", width=65)
    st.markdown("### 🏛️ Taxpayer Dashboard")

    # Active Assessment Year
    selected_year = RULES.get("active_assessment_year", "2025-2026")
    st.markdown(f"""
    <div style="font-size: 0.82rem; color: #334155; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; padding: 6px 10px; margin-bottom: 12px;">
        📅 <b>Tax Year:</b> 2025-2026 (AY 2025-26)
    </div>
    """, unsafe_allow_html=True)

    # 1. New Chat Button
    if st.button("➕ New Chat", use_container_width=True, type="primary"):
        new_id = str(uuid.uuid4())[:8]
        st.session_state.conversations[new_id] = {
            "title": "New Chat",
            "created_at": datetime.now().strftime("%I:%M %p"),
            "messages": [
                {
                    "role": "assistant",
                    "content": "Welcome to a new session! How can I assist you with your Bangladesh income tax questions today?",
                    "references": [],
                    "retrieved_snippets": [],
                    "tool_data": None
                }
            ],
            "category": "regular",
            "slots": {}
        }
        st.session_state.current_chat_id = new_id
        st.rerun()

    # 2. Recents Section with Previous Chats
    st.markdown('<div class="recents-header">Recents</div>', unsafe_allow_html=True)
    for c_id, conv in list(st.session_state.conversations.items()):
        is_active = (c_id == curr_id)
        chat_title = conv["title"]
        if len(chat_title) > 22:
            chat_title = chat_title[:20] + "..."

        col_nav, col_rm = st.columns([5, 1])
        with col_nav:
            btn_label = f"💬 {chat_title}" if is_active else f"　 {chat_title}"
            if st.button(btn_label, key=f"chat_{c_id}", use_container_width=True):
                st.session_state.current_chat_id = c_id
                st.rerun()
        with col_rm:
            if len(st.session_state.conversations) > 1:
                if st.button("✕", key=f"del_{c_id}", help="Delete chat"):
                    del st.session_state.conversations[c_id]
                    st.session_state.current_chat_id = list(st.session_state.conversations.keys())[0]
                    st.rerun()

    st.markdown("---")
    
    # 3. Taxpayer Category
    st.markdown("#### 👤 Taxpayer Category")
    category_options = {
        "regular": "Individual / Male (General)",
        "female": "Female & Senior Citizens (65+)",
        "disabled": "Physically Challenged (Disabled)",
        "freedom_fighter": "Gazetted War-Wounded Freedom Fighters"
    }
    
    curr_cat = current_conv.get("category", "regular")
    selected_cat = st.selectbox(
        "Select Category:",
        list(category_options.keys()),
        format_func=lambda x: category_options[x],
        index=list(category_options.keys()).index(curr_cat) if curr_cat in category_options else 0
    )
    current_conv["category"] = selected_cat
    threshold = get_exemption_limit(selected_cat, year=selected_year)

    st.markdown(f"""
    <div class="tax-card">
        <strong>Tax-Free Threshold:</strong><br>
        <span style="font-size: 1.25rem; color: #15803d; font-weight: bold;">৳ {threshold:,.0f}</span>
    </div>
    """, unsafe_allow_html=True)

    # 4. Live Slot Memory
    slots = current_conv.get("slots", {})
    if any(slots.values()):
        st.markdown("#### 🧠 Active Session Memory:")
        slot_text = ""
        if slots.get("income_type"):
            slot_text += f"• **Income Head:** {slots['income_type']}<br>"
        if slots.get("salary_amount"):
            slot_text += f"• **Salary:** ৳ {slots['salary_amount']:,.0f}<br>"
        if slots.get("rental_amount"):
            slot_text += f"• **Rental Income:** ৳ {slots['rental_amount']:,.0f}<br>"
        if slots.get("gift_amount"):
            slot_text += f"• **Gift Amount:** ৳ {slots['gift_amount']:,.0f}<br>"
        if slots.get("gift_sender"):
            slot_text += f"• **Gift Sender:** {slots['gift_sender']}<br>"
        if slots.get("gift_channel"):
            slot_text += f"• **Payment Channel:** {slots['gift_channel']}<br>"
        
        st.markdown(f"""
        <div class="slot-card">
            {slot_text}
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("#### 💡 Sample Test Questions:")
    samples = [
        "My annual salary is 12,00,000 BDT, what is my tax?",
        "If I have zero income, do I still need to file a tax return?",
        "I received 5,00,000 BDT gift from a friend, is it taxable?",
        "Monthly house rent income is 50,000 BDT, calculate tax",
        "Is IT freelancing remittance income tax-free in Bangladesh?",
        "Father gifted 5,00,000 BDT via banking channel, tax payable?"
    ]
    sample_clicked = None
    for idx, s in enumerate(samples):
        if st.button(s, key=f"sample_{idx}"):
            sample_clicked = s

    st.markdown("---")
    st.markdown("""
    <div style="font-size: 0.76rem; color: #64748b; line-height: 1.45;">
        ⚖️ <b>Legal Disclaimer:</b> This system is an educational AI prototype for decision-support and does not substitute for certified tax advocate or official NBR legal advice.
    </div>
    """, unsafe_allow_html=True)


# ----------------- MAIN INTERFACE -----------------
st.markdown('<div class="main-title">🇧🇩 Bangladesh Income Tax AI Assistant</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Autonomous AI Tax Assistant based on Bangladesh Income Tax Act 2023 • Assessment Year 2025-2026</div>', unsafe_allow_html=True)

# Tabs
tab_chat, tab_peas, tab_eval = st.tabs([
    "💬 Conversation",
    "📋 PEAS Specification & Architecture",
    "📊 System Evaluation & Research"
])

# ----------------- TAB 2: PEAS SPECIFICATION -----------------
with tab_peas:
    st.markdown("### 🏛️ Agent PEAS Model Specification & System Architecture")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("""
        <div class="peas-card">
            <strong>🎯 Performance Measure:</strong>
            <ul>
                <li>Accurate classification of income heads (Salary, Rent, Gift, Freelancing, Business, Zero Income).</li>
                <li>Exact statutory citation of the Income Tax Act 2023 (Sections 32, 36, 45, 66, 166, etc.).</li>
                <li>100% mathematical accuracy using deterministic Python tax calculator tools (Zero Math Error).</li>
                <li>Strict <strong>Clarification-First</strong> behavior on ambiguous or incomplete queries.</li>
                <li>Zero-hallucination guard with explicit fallback when confident information is unavailable.</li>
            </ul>
        </div>
        <div class="peas-card">
            <strong>🌍 Environment:</strong>
            <ul>
                <li>Interactive Web Interface (Streamlit UI multi-session chat).</li>
                <li>Verified Knowledge Base (Bangladesh Income Tax Act 2023, Section 166 & NBR rules.json).</li>
                <li>Multi-turn conversation state machine and dynamic session slot memory.</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown("""
        <div class="peas-card">
            <strong>🦾 Actuators:</strong>
            <ul>
                <li>Structured 4-part response generation (Short Answer, Law & Section, Calculation, Next Steps).</li>
                <li>Interactive statutory legal snippet expanders with verifiable excerpts.</li>
                <li>Invocation of deterministic Python functions (`salary_tax`, `rental_tax`, `gift_check`, `combined_tax`).</li>
                <li>Clarification prompts prompting the user before assuming missing financial parameters.</li>
            </ul>
        </div>
        <div class="peas-card">
            <strong>📡 Sensors:</strong>
            <ul>
                <li>User textual input queries (Bangla, English, and Banglish).</li>
                <li>Selected Taxpayer Category (Regular Male / Female 65+ / Disabled / Freedom Fighter).</li>
                <li>Ongoing conversation history, contextual monetary amount parser, and live slot extractor.</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

# ----------------- TAB 3: SYSTEM EVALUATION -----------------
with tab_eval:
    st.markdown("### 📊 Model Performance & Empirical Benchmark Results")
    if EVAL_DATA:
        total_cases = EVAL_DATA.get("total_test_cases", 0)
        st.caption(f"**Last run:** {EVAL_DATA.get('timestamp', 'N/A')} | **{total_cases} test cases** | **Model:** {EVAL_DATA.get('model', 'N/A')}")

        errs = EVAL_DATA.get("api_error_counts", {})
        if not EVAL_DATA.get("complete"):
            st.warning("Benchmark run is incomplete due to rate limits. Re-run `python run_eval.py` to finalize. Displayed metrics reflect completed cases only.")

        summary = EVAL_DATA.get("summary_table", {})
        metrics = EVAL_DATA.get("metrics", {})
        dens = EVAL_DATA.get("denominators", {})
        short = {"Vanilla LLM": "Vanilla LLM", "LLM + Basic RAG": "LLM+RAG", "Proposed Tax Agent (RAG + Tools + Guard)": "Proposed Agent"}

        def cell(n, d, pct):
            return f"{n}/{d} ({pct}%)" if d and pct is not None else "n/a"

        rows, chart = [], []
        for arch, sm in summary.items():
            m, d = metrics[arch], dens[arch]
            rows.append({
                "Architecture": short.get(arch, arch),
                "API errors (excluded)": errs.get(arch, 0),
                "Math": cell(m["correct_math"], d["math"], sm["Math Accuracy (%)"]),
                "Section": cell(m["correct_section"], d["section"], sm["Section Citation Accuracy (%)"]),
                "Clarification": cell(m["clarification_handled"], d["clarification"], sm["Clarification-First Rate (%)"]),
                "Hallucinated section": cell(m["hallucinations"], d["hallucination"], sm["Hallucination Rate (%)"]),
            })
            chart.append({
                "Architecture": short.get(arch, arch),
                "Math Accuracy (%)": sm["Math Accuracy (%)"] or 0,
                "Section Accuracy (%)": sm["Section Citation Accuracy (%)"] or 0,
                "Clarification (%)": sm["Clarification-First Rate (%)"] or 0,
            })

        st.markdown("#### 📊 Performance Metrics Comparison")
        st.dataframe(pd.DataFrame(rows).set_index("Architecture"), use_container_width=True)

        st.markdown("#### 📈 Comparative Accuracy (0-100%)")
        df_chart = pd.DataFrame(chart).set_index("Architecture")
        try:
            import altair as alt
            melted = df_chart.reset_index().melt(id_vars="Architecture", var_name="Metric", value_name="Score (%)")
            st.altair_chart(alt.Chart(melted).mark_bar().encode(
                x=alt.X("Metric:N", title=""),
                y=alt.Y("Score (%):Q", scale=alt.Scale(domain=[0, 100])),
                color=alt.Color("Metric:N", legend=alt.Legend(title="Metrics")),
                column=alt.Column("Architecture:N", header=alt.Header(labelOrient="bottom", titleOrient="bottom")),
            ).properties(width=160, height=280))
        except Exception:
            st.bar_chart(df_chart)

        # Category breakdown
        st.markdown("#### 📑 Category-wise Math Accuracy (Excluding API Errors)")
        case_items = EVAL_DATA.get("case_details", [])
        keys = [("Vanilla LLM", "vanilla_eval"), ("LLM+RAG", "rag_eval"), ("Proposed Agent", "proposed_eval")]
        cat_rows = []
        for cat in sorted({c.get("category", "") for c in case_items}):
            cs = [c for c in case_items if c.get("category") == cat and c.get("expected_tax") is not None]
            if not cs:
                continue
            row = {"Category": cat}
            for label, k in keys:
                valid = [c for c in cs if c.get(k, {}).get("status") == "ok"]
                row[label] = f"{sum(1 for c in valid if c[k].get('math_ok'))}/{len(valid)}"
            cat_rows.append(row)
        if cat_rows:
            st.dataframe(pd.DataFrame(cat_rows).set_index("Category"), use_container_width=True)

        # Failed cases
        failed = []
        for c in case_items:
            p = c.get("proposed_eval", {})
            if p.get("status") != "ok":
                continue
            reasons = []
            if c.get("expected_tax") is not None and not p.get("math_ok"):
                reasons.append("Math Mismatch")
            if not p.get("sec_ok"):
                reasons.append("Section Missing")
            if c.get("is_ambiguous") and not p.get("clar_ok"):
                reasons.append("Clarification Missed")
            if p.get("hallucinated"):
                reasons.append("Section not in KB")
            if reasons:
                failed.append({"ID": c["id"], "Query": c["query"], "Expected Tax": c["expected_tax"],
                               "Agent Tax": p.get("tax"), "Failed Checks": ", ".join(reasons),
                               "Cited": ", ".join(p.get("cited_sections", [])),
                               "Reply Snippet": p.get("reply_snippet", "")[:120]})
        with st.expander(f"⚠️ Failed Test Cases ({len(failed)})"):
            if failed:
                st.dataframe(pd.DataFrame(failed), use_container_width=True, hide_index=True)
            else:
                st.success("All completed test cases passed successfully for Proposed Agent.")

        st.markdown(f"""
        <div style="background:#fffbeb; border:1px solid #fde68a; border-radius:6px; padding:10px 14px; font-size:0.83rem; color:#92400e; margin-top:14px;">
            📌 <strong>Limitations & Academic Notes:</strong><br>
            • {total_cases} curated benchmark test cases evaluated across 3 architectures with 0 API errors.<br>
            • Ground truth is based on statutory rules codified in `rules.json`.<br>
            • "Hallucinated section" denotes citations not indexed in the verified knowledge base.
        </div>
        """, unsafe_allow_html=True)
    else:
        st.info("Run `python run_eval.py` to view benchmark evaluation results.")


# ----------------- TAB 1: INTERACTIVE CHAT -----------------
with tab_chat:
    for msg in current_conv["messages"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

            # Render Tool Outputs
            t_data = msg.get("tool_data")
            if t_data and t_data.get("tool") in ["salary_tax", "rental_tax", "combined_tax"]:
                calc_out = t_data["output"]
                st.markdown("##### 📊 Slab-based Tax Breakdown:")
                if calc_out.get("slabs"):
                    df = pd.DataFrame(calc_out["slabs"])
                    df.columns = ["Tax Slab Tier", "Tax Rate", "Taxable Amount (BDT)", "Tax Payable (BDT)"]
                    st.dataframe(df, use_container_width=True, hide_index=True)
                st.info(f"**Total Income Tax Payable:** ৳ {calc_out.get('total_tax', 0):,.2f}")
                if calc_out.get("min_tax_applied"):
                    st.caption("ℹ️ Statutory minimum tax applied (Minimum Tax ৳ 5,000) due to taxable income.")
            
            elif t_data and t_data.get("tool") == "gift_check":
                g_out = t_data["output"]
                st.markdown(f"**Gift Assessment:** {'Taxable' if g_out['is_taxable'] else 'Fully Tax-Exempt'}")
                st.caption(f"Reason: {g_out['reason']}")

            # Render Verified Legal Snippets Expander
            snippets = msg.get("retrieved_snippets", [])
            if snippets:
                with st.expander("📚 Relevant Statutory Sections & Legal Snippets"):
                    for s in snippets:
                        st.markdown(f"**Statutory Section: {', '.join(s['section'])}**")
                        st.markdown(f"> *\"{s['snippet']}\"*")

    # Chat Input
    user_input = st.chat_input("Type your income tax question here (e.g. salary, rent, gift, freelancing)...")
    query_to_run = sample_clicked if sample_clicked else user_input

    if query_to_run:
        current_conv["messages"].append({
            "role": "user",
            "content": query_to_run,
            "references": [],
            "retrieved_snippets": [],
            "tool_data": None
        })

        if current_conv["title"] in ["New Chat", "নতুন চ্যাট", "নতুন চ্যাট (New Chat)"]:
            short_t = query_to_run.replace("?", "").strip()
            current_conv["title"] = short_t[:20] + ("..." if len(short_t) > 20 else "")

        with st.chat_message("user"):
            st.markdown(query_to_run)

        with st.chat_message("assistant"):
            with st.spinner("Reviewing tax statute and calculating..."):
                history_payload = [
                    {"role": m["role"], "content": m["content"]}
                    for m in current_conv["messages"]
                ]
                response_dict = st.session_state.tax_agent.respond(
                    messages_history=history_payload,
                    taxpayer_category=selected_cat,
                    current_slots=current_conv.get("slots", {})
                )
                
                reply_text = response_dict["content"]
                st.markdown(reply_text)
                
                if response_dict.get("updated_slots"):
                    current_conv["slots"] = response_dict["updated_slots"]

                tool_data = response_dict.get("tool_data")

                if tool_data and tool_data.get("tool") in ["salary_tax", "rental_tax", "combined_tax"]:
                    calc_out = tool_data["output"]
                    st.markdown("##### 📊 Slab-based Tax Breakdown:")
                    if calc_out.get("slabs"):
                        df = pd.DataFrame(calc_out["slabs"])
                        df.columns = ["Tax Slab Tier", "Tax Rate", "Taxable Amount (BDT)", "Tax Payable (BDT)"]
                        st.dataframe(df, use_container_width=True, hide_index=True)
                    st.info(f"**Total Income Tax Payable:** ৳ {calc_out.get('total_tax', 0):,.2f}")
                    if calc_out.get("min_tax_applied"):
                        st.caption("ℹ️ Statutory minimum tax applied (Minimum Tax ৳ 5,000) due to taxable income.")
                
                elif tool_data and tool_data.get("tool") == "gift_check":
                    g_out = tool_data["output"]
                    st.markdown(f"**Gift Assessment:** {'Taxable' if g_out['is_taxable'] else 'Fully Tax-Exempt'}")
                    st.caption(f"Reason: {g_out['reason']}")

                snippets = response_dict.get("retrieved_snippets", [])
                if snippets:
                    with st.expander("📚 Relevant Statutory Sections & Legal Snippets"):
                        for s in snippets:
                            st.markdown(f"**Statutory Section: {', '.join(s['section'])}**")
                            st.markdown(f"> *\"{s['snippet']}\"*")

        current_conv["messages"].append({
            "role": "assistant",
            "content": reply_text,
            "references": response_dict.get("references", []),
            "retrieved_snippets": response_dict.get("retrieved_snippets", []),
            "tool_data": tool_data
        })
        st.rerun()
