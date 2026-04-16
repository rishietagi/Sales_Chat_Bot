import streamlit as st
import pandas as pd
from backend.services.data_engine import DataEngine
from backend.services.rule_engine import RuleEngine
from backend.services.llm_service import LLMService
import json
from backend.config.settings import settings

# Page Config
st.set_page_config(page_title=settings.PROJECT_NAME, page_icon="📈", layout="wide")

# Persistent Chat History
if "messages" not in st.session_state:
    st.session_state.messages = []

# Custom CSS for Premium Dark/Glassmorphism Look
st.markdown("""
<style>
    /* Main Background */
    [data-testid="stAppViewContainer"] {
        background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%);
        color: #f8fafc;
    }
    
    /* Headers */
    .main-header {
        font-size: 3rem;
        font-weight: 900;
        background: -webkit-linear-gradient(#38bdf8, #818cf8);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
        text-align: center;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #94a3b8;
        text-align: center;
        margin-bottom: 3rem;
    }

    /* Glassmorphism Card */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
        background-color: transparent;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: rgba(255, 255, 255, 0.05);
        border-radius: 8px 8px 0px 0px;
        color: #94a3b8;
        padding: 10px 20px;
    }
    .stTabs [aria-selected="true"] {
        background-color: rgba(56, 189, 248, 0.2) !important;
        color: #38bdf8 !important;
    }

    /* Metrics */
    [data-testid="stMetricValue"] {
        font-size: 2rem;
        font-weight: 700;
        color: #f8fafc;
    }
    [data-testid="stMetricLabel"] {
        color: #38bdf8;
    }

    /* Dataframe padding */
    .stDataFrame {
        background-color: rgba(255, 255, 255, 0.03);
        border-radius: 12px;
        padding: 10px;
    }

    /* Chat Styling */
    .stChatMessage {
        background-color: rgba(255, 255, 255, 0.05) !important;
        border-radius: 12px !important;
        margin-bottom: 10px !important;
    }
</style>
""", unsafe_allow_html=True)

# Initialize Services
@st.cache_resource
def get_services():
    data_path = settings.DATA_PATH
    engine = DataEngine(data_path)
    engine.load_data()
    engine.standardize_and_merge()
    llm = LLMService()
    return engine, llm

engine, llm = get_services()

# Stats Row
df = engine.processed_df
df_with_actions = RuleEngine.apply_rules(df)

# Header
st.markdown('<div class="main-header">Dealer Intelligence AI</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Premium Operations & Strategy Dashboard</div>', unsafe_allow_html=True)

# Metrics in Glass Cards
m_col1, m_col2, m_col3, m_col4 = st.columns(4)
with m_col1:
    st.metric("Total Dealers", len(df))
with m_col2:
    revenue_total = df['total_revenue'].sum()
    st.metric("Gross Revenue", f"₹{revenue_total/1e7:.2f} Cr")
with m_col3:
    outstanding = df['outstanding_amount'].sum()
    st.metric("Risk Exposure", f"₹{outstanding/1e5:.2f} L")
with m_col4:
    dormant = df['is_dormant'].sum()
    st.metric("Critical Dormancy", dormant, delta=f"{(dormant/len(df)*100):.1f}%", delta_color="inverse")

st.markdown("---")

# Chat Interface Sub-Header
st.markdown("### 🤖 Strategy Assistant")

# Pre-built query suggestions
st.markdown("Try asking:")
q_cols = st.columns(3)
with q_cols[0]:
    if st.button("Top high-value dormant dealers?"):
        st.session_state.current_query = "Which high-value dealers are currently dormant?"
with q_cols[1]:
    if st.button("Highest outstanding in Maharashtra?"):
        st.session_state.current_query = "Who are the dealers in Maharashtra with highest outstanding?"
with q_cols[2]:
    if st.button("SKUs with low fulfillment?"):
        st.session_state.current_query = "Which orders have low dispatch ratios?"

# Display Chat History
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if "data" in message:
            st.dataframe(pd.DataFrame(message["data"]), use_container_width=True)

# Chat Input
query = st.chat_input("Ask about dealers, sales, or payments...")

# Handle suggested queries
if "current_query" in st.session_state and not query:
    query = st.session_state.current_query
    del st.session_state.current_query

if query:
    # Add human message
    st.session_state.messages.append({"role": "user", "content": query})
    with st.chat_message("user"):
        st.markdown(query)
    
    with st.spinner("Analyzing operational signals..."):
        # Interpretation
        interpretation_raw = llm.interpret_query(query)
        try:
            interpretation = json.loads(interpretation_raw)
        except:
             interpretation = {"intent": "general", "filters": {}}
        
        intent = interpretation.get("intent")
        
        # Filter Data
        filtered_df = df_with_actions
        if intent == "dormant_detection":
            filtered_df = df_with_actions[df_with_actions['is_dormant']]
        elif intent == "payment_followup":
            filtered_df = df_with_actions[df_with_actions['outstanding_amount'] > 0]
        elif intent == "high_value_detection":
            filtered_df = df_with_actions[df_with_actions['is_high_value']]
        elif intent == "geo_analysis":
            # Just an example sorting for geo
            filtered_df = df_with_actions.sort_values('total_revenue', ascending=False)
        else:
            # Default fallback sorting by priority
            filtered_df = df_with_actions.sort_values('priority_score', ascending=False)
            
        # Context for LLM - send up to 15 top examples to give LLM rich context
        top_samples = filtered_df.head(15)[['Dealer Name', 'State', 'City', 'total_revenue', 'outstanding_amount', 'days_since_last_order', 'open_order_value', 'actions', 'priority_score']].to_dict(orient="records")
        context = {
            "user_query": query,
            "intent": intent,
            "metrics": {
                "total_matched": len(filtered_df), 
                "total_revenue_matched": float(filtered_df['total_revenue'].sum()),
                "total_outstanding_matched": float(filtered_df['outstanding_amount'].sum())
            },
            "samples": top_samples
        }
        
        explanation = llm.get_explanation(json.dumps(context, default=str))
        
        # Add AI message
        ai_msg = {"role": "assistant", "content": explanation}
        if top_samples:
            ai_msg["data"] = top_samples
        
        st.session_state.messages.append(ai_msg)
        with st.chat_message("assistant"):
            st.markdown(explanation)
            if "data" in ai_msg:
                st.dataframe(pd.DataFrame(ai_msg["data"]), use_container_width=True)
