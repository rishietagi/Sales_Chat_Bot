import streamlit as st
import pandas as pd
import os
from dotenv import load_dotenv

from data_loader import DataLoader
from feature_engineering import FeatureEngineer
from intent_router import IntentRouter
from analytics_engine import AnalyticsEngine
from decision_engine import DecisionEngine
from prompt_builder import PromptBuilder
from llm_interface import GroqInterface
from schema_registry import SCHEMA_DICT
from utils import sanitise_user_input
import ui_components

# ── Environment ──────────────────────────────────────────────────────
load_dotenv()

# ── Page config ──────────────────────────────────────────────────────
st.set_page_config(page_title="AI Sales Assistant", page_icon="💼", layout="centered")

# ── Custom CSS ───────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    #MainMenu, footer {visibility: hidden;}

    .stApp {
        background: linear-gradient(135deg, #0f0c29 0%, #1a1a2e 50%, #16213e 100%);
    }

    .hero {text-align: center; padding: 2rem 0 0.5rem;}
    .hero h1 {
        font-size: 2.2rem;
        background: linear-gradient(90deg, #00d2ff, #7b2ff7);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
        margin-bottom: 0.2rem;
    }
    .hero p {color: #94a3b8; font-size: 1rem; margin-top: 0;}

    [data-testid="stChatMessage"] {border-radius: 14px; margin-bottom: 0.8rem;}

    hr {border-color: rgba(255,255,255,0.07);}

    section[data-testid="stSidebar"] {background: #111827;}
    section[data-testid="stSidebar"] .stMarkdown {color: #e2e8f0;}
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Singletons ───────────────────────────────────────────────────────
intent_router = IntentRouter()
decision_engine = DecisionEngine()
prompt_builder = PromptBuilder(SCHEMA_DICT)
llm = GroqInterface()

# ── Sidebar ──────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️  Settings")
    uploaded_file = st.file_uploader("Upload Sales Data (CSV / XLSX)", type=["csv", "xlsx"])

    if not uploaded_file:
        default_file = "sales_data_sample.csv"
        if os.path.exists(default_file):
            uploaded_file = default_file
            st.success(f"Using **{default_file}**")
        else:
            st.warning("Upload a data file to begin.")
            st.stop()

    st.markdown("---")
    st.subheader("🔍 Filters")

# ── Load & cache data ────────────────────────────────────────────────
@st.cache_data
def load_and_process(file):
    loader = DataLoader(file)
    raw = loader.load_and_clean()
    fe = FeatureEngineer(raw)
    fe.add_territory()
    dealer_m = fe.compute_dealer_metrics()
    territory_m = fe.compute_territory_metrics(dealer_metrics=dealer_m)
    return raw, dealer_m, territory_m

try:
    raw_df, dealer_metrics, territory_metrics = load_and_process(uploaded_file)
except Exception as e:
    st.error(f"Schema error – {e}")
    st.stop()

# ── Sidebar filters (after data loads) ───────────────────────────────
with st.sidebar:
    sel_status = (
        st.multiselect("Order Status", raw_df["STATUS"].dropna().unique())
        if "STATUS" in raw_df.columns else []
    )
    sel_product = (
        st.multiselect("Product Line", raw_df["PRODUCTLINE"].dropna().unique())
        if "PRODUCTLINE" in raw_df.columns else []
    )
    sel_deal = (
        st.multiselect("Deal Size", raw_df["DEALSIZE"].dropna().unique())
        if "DEALSIZE" in raw_df.columns else []
    )

    # Dataset snapshot
    st.markdown("---")
    st.caption(
        f"**Loaded:** {raw_df['CUSTOMERNAME'].nunique()} dealers · "
        f"{raw_df['ORDERNUMBER'].nunique():,} orders · "
        f"${raw_df['SALES'].sum():,.0f} revenue"
    )
    if llm.call_count:
        st.caption(f"Groq API calls this session: {llm.call_count}")

# ── Session state ────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []

# ── Hero ─────────────────────────────────────────────────────────────
st.markdown(
    '<div class="hero">'
    "<h1>💼 AI Sales Assistant</h1>"
    "<p>Ask anything about your dealers, territories, products, or orders.</p>"
    "</div>",
    unsafe_allow_html=True,
)

# ── Dataset summary chips ────────────────────────────────────────────
ui_components.render_dataset_summary(raw_df)
st.markdown("---")

# ── Example chips (visible only when chat is empty) ──────────────────
EXAMPLE_QUERIES = [
    "Who are our top dealers by sales?",
    "Which dealers have not ordered in 30 days?",
    "Which dealers are slowing down?",
    "Which orders need follow-up?",
    "Which territory performs best?",
    "Which product lines sell the most?",
]

if not st.session_state.messages:
    cols = st.columns(3)
    for idx, q in enumerate(EXAMPLE_QUERIES):
        if cols[idx % 3].button(q, key=f"ex_{idx}", use_container_width=True):
            st.session_state.pending_query = q
            st.rerun()

# ── Render chat history ──────────────────────────────────────────────
for msg_i, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"]):
        if msg["role"] == "assistant":
            ui_components.render_chat_response(
                msg["explanation"], msg["result_df"], msg["intent"],
                msg_idx=msg_i,
            )
        else:
            st.markdown(msg["content"])

# ── Chat input ───────────────────────────────────────────────────────
user_input = st.chat_input("Ask a sales question…")

if not user_input and "pending_query" in st.session_state:
    user_input = st.session_state.pop("pending_query")

if user_input:
    # Sanitise
    clean_input = sanitise_user_input(user_input)

    # Show user bubble
    st.session_state.messages.append({"role": "user", "content": clean_input})
    with st.chat_message("user"):
        st.markdown(clean_input)

    # ── Apply filters ────────────────────────────────────────────────
    filtered = raw_df.copy()
    if sel_status:
        filtered = filtered[filtered["STATUS"].isin(sel_status)]
    if sel_product:
        filtered = filtered[filtered["PRODUCTLINE"].isin(sel_product)]
    if sel_deal:
        filtered = filtered[filtered["DEALSIZE"].isin(sel_deal)]

    if sel_status or sel_product or sel_deal:
        fe_f = FeatureEngineer(filtered)
        fe_f.add_territory()
        d_met = fe_f.compute_dealer_metrics()
        t_met = fe_f.compute_territory_metrics(dealer_metrics=d_met)
    else:
        d_met, t_met = dealer_metrics, territory_metrics

    # ── Intent & analytics ───────────────────────────────────────────
    intent = intent_router.route_intent(clean_input)

    extra_kw: dict = {}
    if intent == "dormant_dealers":
        extra_kw["dormant_days"] = intent_router.extract_dormant_days(clean_input)
    elif intent == "contact_lookup":
        name = intent_router.extract_dealer_name(clean_input)
        if name:
            extra_kw["dealer_name"] = name

    engine = AnalyticsEngine(filtered, d_met, t_met)

    with st.spinner("Analyzing…"):
        result_df = engine.execute_query(intent, **extra_kw)
        if "CUSTOMERNAME" in result_df.columns:
            result_df = decision_engine.process_dealers(result_df)

    # ── LLM explanation ──────────────────────────────────────────────
    with st.spinner("Generating insights…"):
        sys_p, usr_p = prompt_builder.build_prompt(
            clean_input, intent, result_df,
            chat_history=st.session_state.messages,
        )
        explanation = llm.generate_explanation(sys_p, usr_p)

    # ── Show assistant bubble ────────────────────────────────────────
    st.session_state.messages.append({
        "role": "assistant",
        "explanation": explanation,
        "result_df": result_df,
        "intent": intent,
    })
    with st.chat_message("assistant"):
        ui_components.render_chat_response(
            explanation, result_df, intent,
            msg_idx=len(st.session_state.messages) - 1,
        )
