"""
Nyaya-Sahayak — Premium Streamlit UI
"""
import sys, os, json
from pathlib import Path
import streamlit as st
import pandas as pd

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

# ── Page Config ─────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="न्याय-सहायक | Nyaya-Sahayak",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── CSS ─────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans:ital,wdth,wght@0,62.5..100,100..900;1,62.5..100,100..900&family=Noto+Sans+Devanagari:wght@100..900&display=swap');

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

html, body, [data-testid="stAppViewContainer"] {
    background: #050d1a !important;
    color: #e2e8f0 !important;
    font-family: 'Noto Sans', 'Noto Sans Devanagari', sans-serif !important;
}

[data-testid="stHeader"] { background: transparent !important; }
[data-testid="stSidebar"] { background: #0a1628 !important; }

/* Hero Banner */
.hero {
    background: linear-gradient(135deg, #0a1628 0%, #1a0a2e 40%, #0a1628 100%);
    border: 1px solid rgba(245,158,11,0.3);
    border-radius: 20px;
    padding: 2.5rem 2rem 2rem;
    text-align: center;
    margin-bottom: 1.5rem;
    position: relative;
    overflow: hidden;
}
.hero::before {
    content: '';
    position: absolute; inset: 0;
    background: radial-gradient(ellipse 80% 60% at 50% 0%, rgba(245,158,11,0.12) 0%, transparent 70%);
    pointer-events: none;
}
.hero h1 {
    font-size: 2.8rem; font-weight: 800;
    background: linear-gradient(135deg, #f59e0b, #fde68a, #f59e0b);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    background-clip: text;
    letter-spacing: -1px; margin-bottom: .3rem;
}
.hero .tagline { color: #94a3b8; font-size: 1.05rem; margin-bottom: .8rem; }
.hero .subtitle { color: #64748b; font-size: .9rem; }

/* Cards */
.card {
    background: rgba(13,20,38,0.9);
    border: 1px solid rgba(245,158,11,0.15);
    border-radius: 14px; padding: 1.4rem;
    margin-bottom: 1rem;
    backdrop-filter: blur(10px);
}
.card:hover { border-color: rgba(245,158,11,0.4); }
.card h4 { color: #f59e0b; font-size: 1rem; margin-bottom: .5rem; }
.card p  { color: #cbd5e1; font-size: .9rem; line-height: 1.6; }

/* Comparison table */
.compare-table { width: 100%; border-collapse: collapse; margin-top: 1rem; }
.compare-table th { background: rgba(245,158,11,0.15); color: #f59e0b; padding: .7rem 1rem; text-align: left; font-size:.9rem; }
.compare-table td { padding: .7rem 1rem; border-bottom: 1px solid rgba(255,255,255,0.06); color: #cbd5e1; font-size:.88rem; vertical-align: top; }
.compare-table tr:hover td { background: rgba(245,158,11,0.04); }
.tag-bns { background: rgba(34,197,94,0.2); color: #4ade80; padding: 2px 8px; border-radius: 20px; font-size:.78rem; }
.tag-ipc { background: rgba(239,68,68,0.2); color: #f87171; padding: 2px 8px; border-radius: 20px; font-size:.78rem; }
.tag-new { background: rgba(124,58,237,0.2); color: #a78bfa; padding: 2px 8px; border-radius: 20px; font-size:.78rem; }

/* Chat bubbles */
.msg-user { background: rgba(124,58,237,0.25); border: 1px solid rgba(124,58,237,0.4);
    border-radius: 14px 14px 4px 14px; padding: .8rem 1rem; margin: .5rem 0 .5rem 20%;
    color: #e2e8f0; font-size:.93rem; }
.msg-bot  { background: rgba(13,20,38,0.9); border: 1px solid rgba(245,158,11,0.2);
    border-radius: 14px 14px 14px 4px; padding: .8rem 1rem; margin: .5rem 20% .5rem 0;
    color: #cbd5e1; font-size:.93rem; line-height: 1.65; }
.msg-bot strong { color: #f59e0b; }

/* Scheme card */
.scheme-card {
    background: linear-gradient(135deg, rgba(13,20,38,0.95) 0%, rgba(20,13,38,0.9) 100%);
    border: 1px solid rgba(124,58,237,0.25); border-radius: 12px;
    padding: 1.1rem; margin-bottom: .8rem;
}
.scheme-card .sc-title { color: #a78bfa; font-weight: 700; font-size:.95rem; }
.scheme-card .sc-benefit { color: #4ade80; font-size:.85rem; margin: .3rem 0; }
.scheme-card .sc-eligibility { color: #94a3b8; font-size:.82rem; }
.scheme-badge { display:inline-block; background:rgba(245,158,11,0.15); color:#f59e0b;
    padding:2px 8px; border-radius:20px; font-size:.75rem; margin-right:.3rem; }

/* Stacked tab styling */
.stTabs [data-baseweb="tab-list"] {
    gap: 0; background: rgba(10,22,40,0.8);
    border-radius: 12px; padding: 4px;
    border: 1px solid rgba(245,158,11,0.15);
}
.stTabs [data-baseweb="tab"] {
    color: #64748b !important; border-radius: 8px !important;
    padding: .5rem 1.2rem !important; font-size:.9rem;
}
.stTabs [aria-selected="true"] {
    background: rgba(245,158,11,0.15) !important;
    color: #f59e0b !important;
}

/* Input fields */
.stTextInput input, .stTextArea textarea, .stSelectbox select {
    background: rgba(13,20,38,0.9) !important;
    border: 1px solid rgba(245,158,11,0.2) !important;
    border-radius: 8px !important; color: #e2e8f0 !important;
}
.stTextInput input:focus, .stTextArea textarea:focus {
    border-color: rgba(245,158,11,0.6) !important;
    box-shadow: 0 0 0 2px rgba(245,158,11,0.1) !important;
}

/* Buttons */
.stButton > button {
    background: linear-gradient(135deg, #b45309, #d97706) !important;
    color: white !important; border: none !important;
    border-radius: 8px !important; font-weight: 600 !important;
    transition: all .2s ease !important;
}
.stButton > button:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 20px rgba(245,158,11,0.4) !important;
}

/* Spinner */
.stSpinner { color: #f59e0b !important; }

/* Divider */
hr { border-color: rgba(245,158,11,0.1) !important; }

/* Metrics */
[data-testid="metric-container"] {
    background: rgba(13,20,38,0.8);
    border: 1px solid rgba(245,158,11,0.15);
    border-radius: 10px; padding: .8rem;
}
[data-testid="metric-container"] label { color: #94a3b8 !important; font-size:.8rem; }
[data-testid="metric-container"] [data-testid="stMetricValue"] { color: #f59e0b !important; font-weight:700; }

.footer { text-align: center; color: #334155; font-size:.78rem; margin-top: 2rem; padding-top: 1rem;
    border-top: 1px solid rgba(255,255,255,0.05); }
</style>
""", unsafe_allow_html=True)

# ── Hero ─────────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
  <h1>⚖️ न्याय-सहायक</h1>
  <div class="tagline">Nyaya-Sahayak · AI-Powered Indian Legal Assistant</div>
  <div class="subtitle">Navigating BNS 2023 · IPC Comparison · Government Schemes · Hindi &amp; English</div>
</div>
""", unsafe_allow_html=True)

# ── Language Toggle ─────────────────────────────────────────────────────────────
col_lang, col_stat1, col_stat2, col_stat3 = st.columns([2,1,1,1])
with col_lang:
    language = st.selectbox("🌐 Language / भाषा", ["English", "हिंदी"], label_visibility="collapsed")
    lang_code = "hi" if language == "हिंदी" else "en"
with col_stat1:
    st.metric("BNS Sections", "358")
with col_stat2:
    st.metric("IPC→BNS Maps", "50+")
with col_stat3:
    st.metric("Gov Schemes", "12")

st.markdown("<hr>", unsafe_allow_html=True)

# ── Lazy-load heavy modules ─────────────────────────────────────────────────────
@st.cache_resource(show_spinner="⚙️ Initializing Nyaya-Sahayak engine…")
def load_engine():
    from nyaya_sahayak.rag_engine import get_engine
    return get_engine()

@st.cache_resource(show_spinner="Loading comparison engine…")
def load_comparator():
    from nyaya_sahayak.comparator import get_comparator
    return get_comparator()

@st.cache_resource(show_spinner="Loading scheme database…")
def load_checker():
    from nyaya_sahayak.scheme_checker import get_checker
    return get_checker()

# ── Tabs ─────────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "💬 Legal Chatbot",
    "⚖️ IPC vs BNS Compare",
    "🔄 Section Translator",
    "🏛️ Scheme Checker",
])

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 — LEGAL CHATBOT
# ═══════════════════════════════════════════════════════════════════════════════
with tab1:
    st.markdown("""
    <div class="card">
      <h4>💬 Ask any legal question about BNS or IPC</h4>
      <p>Ask in Hindi or English. Answers include section references and practical advice.</p>
    </div>
    """, unsafe_allow_html=True)

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # Display history
    for role, msg in st.session_state.chat_history:
        css_cls = "msg-user" if role == "user" else "msg-bot"
        icon = "👤" if role == "user" else "⚖️"
        st.markdown(f'<div class="{css_cls}">{icon} {msg}</div>', unsafe_allow_html=True)

    # Input
    with st.form("chat_form", clear_on_submit=True):
        c1, c2 = st.columns([5,1])
        with c1:
            user_q = st.text_input(
                "Ask a question…",
                placeholder="e.g. What is the punishment for rape under BNS? / हत्या के लिए सजा क्या है?",
                label_visibility="collapsed",
            )
        with c2:
            submitted = st.form_submit_button("Send ➤", use_container_width=True)

    if submitted and user_q.strip():
        st.session_state.chat_history.append(("user", user_q))

        with st.spinner("Thinking…"):
            try:
                engine = load_engine()
                from nyaya_sahayak.llm_client import chat as llm_chat
                # Get RAG context
                ctx_results = engine.query_bns(user_q, top_k=3)
                context = engine.format_context(ctx_results)
                # Build message
                system_ctx = f"\n\nRelevant BNS context:\n{context}" if context else ""
                messages = [{"role": "user", "content": user_q + system_ctx}]
                answer = llm_chat(messages, language=lang_code, max_tokens=900)
            except Exception as e:
                answer = f"⚠️ Error: {e}\n\nPlease ensure your HF token is set in `.env`."

        st.session_state.chat_history.append(("bot", answer))
        st.rerun()

    if st.button("🗑️ Clear Chat"):
        st.session_state.chat_history = []
        st.rerun()

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 — IPC vs BNS COMPARISON
# ═══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.markdown("""
    <div class="card">
      <h4>⚖️ Scenario-based IPC vs BNS Comparison</h4>
      <p>Describe a legal scenario and get a side-by-side comparison of old IPC and new BNS provisions.</p>
    </div>
    """, unsafe_allow_html=True)

    scenario = st.text_area(
        "Describe the scenario",
        placeholder="e.g. A person threatens someone with a knife to take their money…",
        height=90,
        label_visibility="collapsed",
    )

    QUICK = ["Murder / हत्या", "Theft / चोरी", "Rape / बलात्कार",
             "Cheating / धोखाधड़ी", "Acid attack / एसिड हमला", "Stalking / पीछा करना"]
    q_pick = st.selectbox("Or pick a quick scenario:", ["—"] + QUICK, label_visibility="collapsed")
    if q_pick != "—":
        scenario = q_pick.split(" / ")[0]

    if st.button("🔍 Compare IPC vs BNS", key="cmp_btn"):
        if not scenario.strip():
            st.warning("Please enter a scenario.")
        else:
            with st.spinner("Querying BNS & IPC indices…"):
                try:
                    comp = load_comparator()
                    result = comp.compare_scenario(scenario, language=lang_code)
                except Exception as e:
                    st.error(f"Error: {e}")
                    result = None

            if result:
                bns_r = result["bns_results"]
                ipc_r = result["ipc_results"]

                c_bns, c_ipc = st.columns(2)
                with c_bns:
                    st.markdown('<span class="tag-bns">✅ BNS 2023</span>', unsafe_allow_html=True)
                    if bns_r:
                        for r in bns_r:
                            st.markdown(f"""
                            <div class="card">
                              <h4>{r.get('title','BNS Section')}</h4>
                              <p>{r.get('text','')[:400]}</p>
                            </div>""", unsafe_allow_html=True)
                    else:
                        st.info("No specific BNS sections found via index.")

                with c_ipc:
                    st.markdown('<span class="tag-ipc">📜 IPC 1860</span>', unsafe_allow_html=True)
                    if ipc_r:
                        for r in ipc_r:
                            st.markdown(f"""
                            <div class="card">
                              <h4>{r.get('title','IPC Section')}</h4>
                              <p>{r.get('text','')[:400]}</p>
                            </div>""", unsafe_allow_html=True)
                    else:
                        st.info("IPC index not yet built. Run pipeline to extract IPC text.")

                st.markdown("---")
                st.markdown("### 🤖 AI Analysis")
                st.markdown(f'<div class="msg-bot">⚖️ {result["llm_analysis"]}</div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3 — SECTION TRANSLATOR
# ═══════════════════════════════════════════════════════════════════════════════
with tab3:
    st.markdown("""
    <div class="card">
      <h4>🔄 IPC → BNS Section Translator</h4>
      <p>Enter an old IPC section number and instantly find its BNS equivalent.</p>
    </div>
    """, unsafe_allow_html=True)

    c1, c2 = st.columns([2, 1])
    with c1:
        ipc_input = st.text_input("Enter IPC Section Number", placeholder="e.g. 302, 420, 376D, 498A")
    with c2:
        st.markdown("<br>", unsafe_allow_html=True)
        translate_btn = st.button("🔄 Translate", key="trans_btn", use_container_width=True)

    # Quick lookup table
    st.markdown("#### 📋 Common IPC → BNS Mappings")
    try:
        comp = load_comparator()
        df = comp.get_full_mapping_df()
        df_display = df[df["bns_section"] != "NEW"][
            ["ipc_section","ipc_name","bns_section","bns_name","category","note"]
        ].rename(columns={
            "ipc_section":"IPC §","ipc_name":"IPC Offence",
            "bns_section":"BNS §","bns_name":"BNS Offence",
            "category":"Category","note":"Key Change"
        })
        st.dataframe(
            df_display,
            use_container_width=True,
            height=300,
            hide_index=True,
        )
    except Exception as e:
        st.warning(f"Could not load mapping table: {e}")

    if translate_btn and ipc_input.strip():
        with st.spinner(f"Looking up IPC {ipc_input}…"):
            try:
                comp = load_comparator()
                result = comp.translate_ipc_to_bns(ipc_input.strip())
            except Exception as e:
                result = {"found": False, "note": str(e)}

        if result.get("found"):
            bns_sec = result["bns_section"]
            is_repealed = bns_sec in ("REPEALED",)
            color = "#f87171" if is_repealed else "#4ade80"
            st.markdown(f"""
            <div class="card" style="border-color: {color}40;">
              <div style="display:flex; gap:1rem; align-items:flex-start;">
                <div style="flex:1;">
                  <span class="tag-ipc">IPC § {result['ipc_section']}</span>
                  <h4 style="margin-top:.5rem;">{result['ipc_name']}</h4>
                </div>
                <div style="font-size:1.5rem; color:#64748b;">→</div>
                <div style="flex:1;">
                  <span class="{'tag-bns' if not is_repealed else 'tag-ipc'}">BNS § {bns_sec}</span>
                  <h4 style="margin-top:.5rem;">{result['bns_name']}</h4>
                </div>
              </div>
              {("<p style='color:#94a3b8; margin-top:.7rem;'>📝 " + str(result['note']) + "</p>") if str(result.get('note','') or '').strip() not in ('', 'nan') else ""}
            </div>
            """, unsafe_allow_html=True)

            if result.get("bns_text"):
                with st.expander(f"📄 Full text of BNS § {bns_sec}"):
                    st.write(result["bns_text"])

            # LLM explanation
            if not is_repealed:
                with st.spinner("Getting AI explanation…"):
                    from nyaya_sahayak.llm_client import chat as llm_chat
                    explanation = llm_chat([
                        {"role": "user", "content":
                         f"Explain the change from IPC {result['ipc_section']} ({result['ipc_name']}) "
                         f"to BNS {bns_sec} ({result['bns_name']}). What are the key differences?"}
                    ], language=lang_code, max_tokens=500)
                st.markdown(f'<div class="msg-bot">⚖️ {explanation}</div>', unsafe_allow_html=True)
        else:
            st.warning(f"IPC Section {ipc_input} not found in mapping table. Try the chatbot for manual lookup.")

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 4 — SCHEME ELIGIBILITY CHECKER
# ═══════════════════════════════════════════════════════════════════════════════
with tab4:
    st.markdown("""
    <div class="card">
      <h4>🏛️ Government Scheme Eligibility Checker</h4>
      <p>Fill in your profile and discover which central government schemes you qualify for.</p>
    </div>
    """, unsafe_allow_html=True)

    with st.form("scheme_form"):
        r1c1, r1c2, r1c3 = st.columns(3)
        with r1c1:
            age = st.number_input("Age", 10, 100, 30)
            gender = st.selectbox("Gender", ["Male", "Female", "Other"])
        with r1c2:
            income = st.number_input("Annual Income (LPA ₹)", 0.0, 50.0, 2.0, step=0.5)
            caste = st.selectbox("Category", ["General","OBC","SC","ST"])
        with r1c3:
            location = st.selectbox("Location", ["Urban", "Rural"])
            occupation = st.selectbox("Occupation", ["Farmer","Student","Salaried","Self-employed","Unemployed","Business"])

        r2c1, r2c2, r2c3, r2c4 = st.columns(4)
        with r2c1: is_bpl = st.checkbox("BPL Card Holder")
        with r2c2: has_disability = st.checkbox("Differently-abled")
        with r2c3: is_survivor = st.checkbox("Violence Survivor")
        with r2c4: needs_legal = st.checkbox("Needs Legal Aid")

        r3c1, r3c2, r3c3 = st.columns(3)
        with r3c1: has_land = st.checkbox("Has Agricultural Land")
        with r3c2: has_girl = st.checkbox("Has Girl Child (< 10 yrs)")
        with r3c3: no_lpg = st.checkbox("No LPG Connection")

        scheme_submit = st.form_submit_button("🔍 Find Matching Schemes", use_container_width=True)

    if scheme_submit:
        profile = {
            "age": age,
            "gender": gender.lower(),
            "annual_income_lpa": income,
            "caste": caste.lower(),
            "location": location.lower(),
            "occupation": occupation.lower(),
            "is_bpl": is_bpl,
            "has_disability": has_disability,
            "is_violence_survivor": is_survivor,
            "needs_legal_aid": needs_legal,
            "has_agricultural_land": has_land,
            "has_girl_child": has_girl,
            "no_lpg": no_lpg,
        }

        with st.spinner("Matching schemes…"):
            try:
                checker = load_checker()
                result = checker.check_eligibility(profile, language=lang_code)
            except Exception as e:
                st.error(f"Error: {e}")
                result = None

        if result:
            matched = result["matched_schemes"]
            st.success(f"Found **{result['total_matched']}** potentially eligible schemes. Showing top {len(matched)}.")

            # Scheme cards
            for scheme in matched:
                cat = scheme.get("category","")
                benefit = scheme.get("benefit","")
                url = scheme.get("url","")
                score = scheme.get("_score", 0)
                st.markdown(f"""
                <div class="scheme-card">
                  <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                    <div>
                      <span class="sc-title">{scheme['name']}</span>
                      <span style="color:#475569; font-size:.8rem;"> &nbsp; {scheme.get('hindi_name','')}</span><br>
                      <span class="scheme-badge">{cat}</span>
                      <div class="sc-benefit">💰 {benefit}</div>
                      <div class="sc-eligibility">{scheme.get('description','')[:120]}…</div>
                    </div>
                    <div style="text-align:right;">
                      <span style="color:#f59e0b; font-size:.8rem;">Match: {score}pts</span><br>
                      {"<a href='" + url + "' target='_blank' style='color:#7c3aed; font-size:.8rem;'>🔗 Apply</a>" if url else ""}
                    </div>
                  </div>
                </div>
                """, unsafe_allow_html=True)

            st.markdown("---")
            st.markdown("### 🤖 AI Guide")
            st.markdown(f'<div class="msg-bot">⚖️ {result["explanation"]}</div>', unsafe_allow_html=True)

# ── Footer ───────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="footer">
  ⚖️ Nyaya-Sahayak · Powered by Sarvam-M + PageIndex + LangExtract + PySpark<br>
  This is an informational tool. For legal advice, consult a qualified advocate.<br>
  BNS 2023 data sourced from the Gazette of India.
</div>
""", unsafe_allow_html=True)
