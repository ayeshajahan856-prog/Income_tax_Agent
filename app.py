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
            "title": "নতুন চ্যাট",
            "created_at": datetime.now().strftime("%I:%M %p"),
            "messages": [
                {
                    "role": "assistant",
                    "content": "আসসালামু আলাইকুম! আমি বাংলাদেশ আয়কর এআই সহকারী। চাকরি, বাড়িভাড়া, ব্যবসা, উপহার বা ফ্রিল্যান্সিং আয়ের যেকোনো কর সংক্রান্ত নিয়ম বা হিসাব জানতে প্রশ্ন করুন।",
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
    st.markdown("### 🏛️ করদাতা ড্যাশবোর্ড")

    # Active Assessment Year
    selected_year = RULES.get("active_assessment_year", "2025-2026")
    st.markdown("""
    <div style="font-size: 0.82rem; color: #334155; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; padding: 6px 10px; margin-bottom: 12px;">
        📅 <b>করবর্ষ:</b> ২০২৫-২০২৬ (AY 2025-26)
    </div>
    """, unsafe_allow_html=True)


    # 1. New Chat Button
    if st.button("➕ New Chat", use_container_width=True, type="primary"):
        new_id = str(uuid.uuid4())[:8]
        st.session_state.conversations[new_id] = {
            "title": "নতুন চ্যাট",
            "created_at": datetime.now().strftime("%I:%M %p"),
            "messages": [
                {
                    "role": "assistant",
                    "content": "আসসালামু আলাইকুম! নতুন সেশনে স্বাগতম। আপনার কর সংক্রান্ত যেকোনো প্রশ্ন করতে পারেন।",
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
                if st.button("✕", key=f"del_{c_id}", help="চ্যাট মুছুন"):
                    del st.session_state.conversations[c_id]
                    st.session_state.current_chat_id = list(st.session_state.conversations.keys())[0]
                    st.rerun()

    st.markdown("---")
    
    # 3. Taxpayer Category
    st.markdown("#### 👤 করদাতার ধরন")
    category_options = {
        "regular": RULES["years"][selected_year]["exemption_limits"]["regular"]["name"],
        "female": RULES["years"][selected_year]["exemption_limits"]["female_senior"]["name"],
        "disabled": RULES["years"][selected_year]["exemption_limits"]["disabled"]["name"],
        "freedom_fighter": RULES["years"][selected_year]["exemption_limits"]["freedom_fighter"]["name"]
    }
    
    curr_cat = current_conv.get("category", "regular")
    selected_cat = st.selectbox(
        "ক্যাটাগরি নির্বাচন করুন:",
        list(category_options.keys()),
        format_func=lambda x: category_options[x],
        index=list(category_options.keys()).index(curr_cat) if curr_cat in category_options else 0
    )
    current_conv["category"] = selected_cat
    threshold = get_exemption_limit(selected_cat, year=selected_year)

    st.markdown(f"""
    <div class="tax-card">
        <strong>করমুক্ত আয়ের সীমা:</strong><br>
        <span style="font-size: 1.25rem; color: #15803d; font-weight: bold;">৳ {threshold:,.0f}</span>
    </div>
    """, unsafe_allow_html=True)

    # 4. Live Slot Memory ("আমি যা জানি")
    slots = current_conv.get("slots", {})
    if any(slots.values()):
        st.markdown("#### 🧠 আমি যা জানি (Active Memory):")
        slot_text = ""
        if slots.get("income_type"):
            slot_text += f"• **আয়ের খাত:** {slots['income_type']}<br>"
        if slots.get("salary_amount"):
            slot_text += f"• **বেতন:** ৳ {slots['salary_amount']:,.0f}<br>"
        if slots.get("rental_amount"):
            slot_text += f"• **ভাড়া আয়:** ৳ {slots['rental_amount']:,.0f}<br>"
        if slots.get("gift_amount"):
            slot_text += f"• **উপহারের অঙ্ক:** ৳ {slots['gift_amount']:,.0f}<br>"
        if slots.get("gift_sender"):
            slot_text += f"• **উপহারদাতা:** {slots['gift_sender']}<br>"
        if slots.get("gift_channel"):
            slot_text += f"• **লেনদেনের মাধ্যম:** {slots['gift_channel']}<br>"
        
        st.markdown(f"""
        <div class="slot-card">
            {slot_text}
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("#### 💡 স্যাম্পল টেস্ট প্রশ্ন:")
    samples = [
        "amr ayy na thakle ki kor dite hbe",
        "amar ekjon bondhu amake 5 lakh gift dise",
        "Mahmud amar bondhu, she amake 6 lakh taka gift korlo",
        "আমার বার্ষিক বেতন ৮,৫০,০০০ টাকা। কত ট্যাক্স হবে?",
        "বাবা আমাকে ব্যাংকে ৫ লাখ টাকা উপহার দিয়েছেন। ট্যাক্স লাগবে কি?",
        "ফ্ল্যাট থেকে বছরে ৪ লাখ টাকা বাড়িভাড়া পাই। ট্যাক্স কত?"
    ]
    sample_clicked = None
    for idx, s in enumerate(samples):
        if st.button(s, key=f"sample_{idx}"):
            sample_clicked = s

    st.markdown("---")
    st.markdown("""
    <div style="font-size: 0.76rem; color: #64748b; line-height: 1.45;">
        ⚖️ <b>আইনি দায়মুক্তি:</b> এই সিস্টেমটি একটি শিক্ষামূলক ও সিদ্ধান্ত-সহায়তাকারী AI প্রোটোটাইপ। এটি কোনো সার্টিফাইড আয়কর আইনজীবী বা NBR-এর আনুষ্ঠানিক আইনি পরামর্শের বিকল্প নয়।
    </div>
    """, unsafe_allow_html=True)


# ----------------- MAIN INTERFACE -----------------
st.markdown('<div class="main-title">🇧🇩 Bangladesh Income Tax AI Assistant</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">বাংলাদেশ আয়কর আইন ২০২৩ ভিত্তিক স্বায়ত্তশাসিত এআই ট্যাক্স সহকারী • করবর্ষ ২০২৫-২০২৬</div>', unsafe_allow_html=True)

# Tabs
tab_chat, tab_peas, tab_eval = st.tabs([
    "💬 কথোপকথন (Conversation)",
    "📋 PEAS Specification & Architecture",
    "📊 গবেষণা ও বাস্তব মূল্যায়ন (Real System Evaluation)"
])

# ----------------- TAB 2: PEAS SPECIFICATION -----------------
with tab_peas:
    st.markdown("### 🏛️ Agent PEAS Model Specification & System Architecture")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("""
        <div class="peas-card">
            <strong>🎯 Performance Measure (সাফল্যের পরিমাপ):</strong>
            <ul>
                <li>আয়ের ধরণ (Salary, Rent, Gift, Freelancing, Business, Zero Income) নির্ভুল শনাক্তকরণ।</li>
                <li>আইনের সঠিক ধারা (Sections 32, 36, 45, 66, 166 etc.) নির্ভুল উদ্ধৃত করা।</li>
                <li>Python ক্যালকুলেটর টুলের সাহায্যে ১০০% সঠিক গাণিতিক স্ল্যাব হিসাব (Zero Math Error)।</li>
                <li>অসম্পূর্ণ তথ্যে উত্তর দেওয়ার পূর্বে <strong>Clarification First</strong> নিশ্চিতকরণ।</li>
                <li>হ্যালুসিনেশন রোধে <em>"আমি নিশ্চিত নই"</em> গার্ডের উপস্থিতি।</li>
            </ul>
        </div>
        <div class="peas-card">
            <strong>🌍 Environment (পরিবেশ):</strong>
            <ul>
                <li>ওয়েব চ্যাট উইন্ডো (Streamlit UI)।</li>
                <li>ভেরিফাইড নলেজ বেইস (Bangladesh Income Tax Act 2023, Section 166 & NBR Rules.json)।</li>
                <li>মাল্টি-টার্ন স্টেট মেশিন ও ডায়নামিক স্লট মেমোরি।</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown("""
        <div class="peas-card">
            <strong>🦾 Actuators (এজেন্টের কর্মকাণ্ড):</strong>
            <ul>
                <li>সংক্ষিপ্ত উত্তর, আইনের ব্যাখ্যা ও পরবর্তী পদক্ষেপ সমন্বিত রেসপন্স প্রদান।</li>
                <li>আইনের মূল স্নsnippet সহ সোর্স এক্সপ্যান্ডার প্রদর্শন।</li>
                <li>Deterministic Tax Calculator ফাংশন ইনভোক করা ও স্ল্যাব টেবিল তৈরি।</li>
                <li>অসম্পূর্ণ তথ্যের ক্ষেত্রে ব্যবহারকারীকে ক্ল্যারিফিকেশন প্রশ্ন করা।</li>
            </ul>
        </div>
        <div class="peas-card">
            <strong>📡 Sensors (এজেন্টের ইনপুট গ্রাহক):</strong>
            <ul>
                <li>ব্যবহারকারীর টাইপ করা টেক্সট প্রশ্ন (বাংলা/ইংরেজি/বাংলিশ)।</li>
                <li>করদাতার ধরন (Regular Male / Female 65+ / Disabled / Freedom Fighter)।</li>
                <li>চলমান কনভারসেশন হিস্ট্রি এবং লাইভ স্লট মেমোরি।</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

# ----------------- TAB 3: SYSTEM EVALUATION -----------------
with tab_eval:
    st.markdown("### 📊 মডেল পারফরম্যান্স ও বাস্তব মূল্যায়ন (Empirical Benchmark Results)")
    if EVAL_DATA:
        total_cases = EVAL_DATA.get("total_test_cases", 0)
        st.caption(f"**Last run:** {EVAL_DATA.get('timestamp', 'N/A')} | **{total_cases} cases** | **model:** {EVAL_DATA.get('model', 'N/A')}")

        errs = EVAL_DATA.get("api_error_counts", {})
        if not EVAL_DATA.get("complete"):
            st.warning("এই ফলাফল সম্পূর্ণ নয় (কিছু কেস API/rate-limit এর কারণে বাকি)। বাকি অংশ শেষ করতে `python run_eval.py` আবার চালান। নিচের শতাংশ শুধু সম্পন্ন কেসের উপর।")

        summary = EVAL_DATA.get("summary_table", {})
        metrics = EVAL_DATA.get("metrics", {})
        dens = EVAL_DATA.get("denominators", {})
        short = {"Vanilla LLM": "Vanilla LLM", "LLM + Basic RAG": "LLM+RAG", "Proposed Tax Agent (RAG + Tools + Guard)": "Agent"}

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

        st.markdown("#### 📊 পারফরম্যান্স মেট্রিক্স")
        st.dataframe(pd.DataFrame(rows).set_index("Architecture"), use_container_width=True)

        st.markdown("#### 📈 তুলনামূলক মূল্যায়ন (0-100%)")
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

        # Category breakdown (math, numeric cases that finished without API error)
        st.markdown("#### 📑 খাতভিত্তিক সঠিক উত্তর (Math, API error বাদে)")
        case_items = EVAL_DATA.get("case_details", [])
        keys = [("Vanilla LLM", "vanilla_eval"), ("LLM+RAG", "rag_eval"), ("Proposed Agent", "proposed_eval")]
        cat_rows = []
        for cat in sorted({c.get("category", "") for c in case_items}):
            cs = [c for c in case_items if c.get("category") == cat and c.get("expected_tax") is not None]
            if not cs:
                continue
            row = {"আয়ের খাত (Category)": cat}
            for label, k in keys:
                valid = [c for c in cs if c.get(k, {}).get("status") == "ok"]
                row[label] = f"{sum(1 for c in valid if c[k].get('math_ok'))}/{len(valid)}"
            cat_rows.append(row)
        if cat_rows:
            st.dataframe(pd.DataFrame(cat_rows).set_index("আয়ের খাত (Category)"), use_container_width=True)

        # Failed cases of the proposed agent (API errors are NOT failures)
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
        with st.expander(f"⚠️ ফেইল করা টেস্ট কেস ({len(failed)} টি)"):
            if failed:
                st.dataframe(pd.DataFrame(failed), use_container_width=True, hide_index=True)
            else:
                st.success("সম্পন্ন কেসগুলোর মধ্যে Proposed Agent-এ কোনো কেস ফেইল করেনি।")

        st.markdown(f"""
        <div style="background:#fffbeb; border:1px solid #fde68a; border-radius:6px; padding:10px 14px; font-size:0.83rem; color:#92400e; margin-top:14px;">
            📌 <strong>সীমাবদ্ধতা (Limitations):</strong><br>
            • মোট {total_cases}টি হাতে-লেখা টেস্ট কেস, একবারের রান — ছোট স্যাম্পল।<br>
            • Ground truth `rules.json` এর নিয়মের উপর নির্ভরশীল; অফিশিয়াল গেজেটের সাথে এখনো যাচাই করা হয়নি।<br>
            • "Hallucinated section" মানে উদ্ধৃত ধারা এই প্রজেক্টের knowledge base-এ নেই; আসল আইনে ভুল কি না তা প্রমাণ করে না।
        </div>
        """, unsafe_allow_html=True)
    else:
        st.info("ইভ্যালুয়েশন ফলাফল দেখতে টার্মিনালে `python run_eval.py` চালান।")


# ----------------- TAB 1: INTERACTIVE CHAT -----------------
with tab_chat:
    for msg in current_conv["messages"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

            # Render Tool Outputs
            t_data = msg.get("tool_data")
            if t_data and t_data.get("tool") in ["salary_tax", "rental_tax", "combined_tax"]:
                calc_out = t_data["output"]
                st.markdown("##### 📊 কর স্ল্যাবভিত্তিক হিসাব বিবরণী:")
                if calc_out.get("slabs"):
                    df = pd.DataFrame(calc_out["slabs"])
                    df.columns = ["স্ল্যাব স্তর", "কর হার", "করযোগ্য টাকা", "প্রদেয় কর (টাকা)"]
                    st.dataframe(df, use_container_width=True, hide_index=True)
                st.info(f"**মোট প্রদেয় আয়কর:** ৳ {calc_out.get('total_tax', 0):,.2f}")
                if calc_out.get("min_tax_applied"):
                    st.caption("ℹ️ করযোগ্য আয় থাকায় সংবিধিবদ্ধ ন্যূনতম কর (Minimum Tax ৳ ৫,০০০) ধার্য করা হয়েছে।")
            
            elif t_data and t_data.get("tool") == "gift_check":
                g_out = t_data["output"]
                st.markdown(f"**উপহার ফলাফল:** {'করযোগ্য' if g_out['is_taxable'] else 'সম্পূর্ণ করমুক্ত'}")
                st.caption(f"কারণ: {g_out['reason']}")

            # Render Verified Legal Snippets Expander
            snippets = msg.get("retrieved_snippets", [])
            if snippets:
                with st.expander("📚 আইনের প্রাসঙ্গিক ধারা ও মূল পাঠ্য (Retrieved Legal Snippets)"):
                    for s in snippets:
                        st.markdown(f"**ধারা/বিধি: {', '.join(s['section'])}**")
                        st.markdown(f"> *\"{s['snippet']}\"*")

    # Chat Input
    user_input = st.chat_input("আপনার কর বিষয়ক প্রশ্ন এখানে লিখুন...")
    query_to_run = sample_clicked if sample_clicked else user_input

    if query_to_run:
        current_conv["messages"].append({
            "role": "user",
            "content": query_to_run,
            "references": [],
            "retrieved_snippets": [],
            "tool_data": None
        })

        if current_conv["title"] in ["নতুন চ্যাট", "নতুন চ্যাট (New Chat)"]:
            short_t = query_to_run.replace("?", "").strip()
            current_conv["title"] = short_t[:20] + ("..." if len(short_t) > 20 else "")

        with st.chat_message("user"):
            st.markdown(query_to_run)

        with st.chat_message("assistant"):
            with st.spinner("আইন পর্যালোচনা এবং হিসাব যাচাই করা হচ্ছে..."):
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
                    st.markdown("##### 📊 কর স্ল্যাবভিত্তিক হিসাব বিবরণী:")
                    if calc_out.get("slabs"):
                        df = pd.DataFrame(calc_out["slabs"])
                        df.columns = ["স্ল্যাব স্তর", "কর হার", "করযোগ্য টাকা", "প্রদেয় কর (টাকা)"]
                        st.dataframe(df, use_container_width=True, hide_index=True)
                    st.info(f"**মোট প্রদেয় আয়কর:** ৳ {calc_out.get('total_tax', 0):,.2f}")
                    if calc_out.get("min_tax_applied"):
                        st.caption("ℹ️ করযোগ্য আয় থাকায় সংবিধিবদ্ধ ন্যূনতম কর (Minimum Tax ৳ ৫,০০০) ধার্য করা হয়েছে।")
                
                elif tool_data and tool_data.get("tool") == "gift_check":
                    g_out = tool_data["output"]
                    st.markdown(f"**উপহার ফলাফল:** {'করযোগ্য' if g_out['is_taxable'] else 'সম্পূর্ণ করমুক্ত'}")
                    st.caption(f"কারণ: {g_out['reason']}")

                snippets = response_dict.get("retrieved_snippets", [])
                if snippets:
                    with st.expander("📚 আইনের প্রাসঙ্গিক ধারা ও মূল পাঠ্য (Retrieved Legal Snippets)"):
                        for s in snippets:
                            st.markdown(f"**ধারা/বিধি: {', '.join(s['section'])}**")
                            st.markdown(f"> *\"{s['snippet']}\"*")

        current_conv["messages"].append({
            "role": "assistant",
            "content": reply_text,
            "references": response_dict.get("references", []),
            "retrieved_snippets": response_dict.get("retrieved_snippets", []),
            "tool_data": tool_data
        })
        st.rerun()