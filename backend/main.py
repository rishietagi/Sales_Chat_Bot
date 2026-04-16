from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from backend.services.data_engine import DataEngine
from backend.services.rule_engine import RuleEngine
from backend.services.llm_service import LLMService
import json
import os
from pydantic import BaseModel
from backend.config.settings import settings

app = FastAPI(title=settings.PROJECT_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

data_path = settings.DATA_PATH
engine = DataEngine(data_path)

@app.on_event("startup")
def startup_event():
    try:
        engine.load_data()
        engine.standardize_and_merge()
    except Exception as e:
        print(f"Error loading initial data: {e}")

# Mount static files (CSS, JS)
app.mount("/static", StaticFiles(directory="frontend"), name="static")

@app.get("/", response_class=HTMLResponse)
async def read_index():
    with open(os.path.join("frontend", "index.html"), "r", encoding="utf-8") as f:
        return f.read()

@app.get("/api/metrics")
def get_metrics(role: str = 'National Sales Manager', zone: str = '', bdo: str = ''):
    df = engine.processed_df
    if df is None: return {"error": "Data not loaded"}
    
    df_with_actions = RuleEngine.apply_rules(df)
    
    # Pre-filter by hierarchy
    if role == 'Zonal Sales Manager' and zone:
        df_with_actions = df_with_actions[df_with_actions['Zone'] == zone]
    elif role == 'BDO' and bdo:
        df_with_actions = df_with_actions[df_with_actions['BDO'] == bdo]

    stats = {
        "total_dealers": len(df_with_actions),
        "total_revenue": float(df_with_actions['total_revenue'].sum() if 'total_revenue' in df_with_actions.columns else 0),
        "total_outstanding": float(df_with_actions['outstanding_amount'].sum() if 'outstanding_amount' in df_with_actions.columns else 0),
        "dormant_count": int(df_with_actions['is_dormant'].sum() if 'is_dormant' in df_with_actions.columns else 0),
    }
    return stats

class QueryRequest(BaseModel):
    query: str
    api_key: str
    role: str = 'National Sales Manager'
    zone: str = ''
    bdo: str = ''

@app.post("/api/chat")
async def process_query(request: QueryRequest):
    query = request.query
    if not query:
        raise HTTPException(status_code=400, detail="Query is required")
        
    try:
        llm = LLMService(api_key=request.api_key)
    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid API Key or LLM Error")
        
    interpretation_raw = llm.interpret_query(query)
    try:
        interpretation = json.loads(interpretation_raw)
    except:
        interpretation = {"intent": "general", "filters": {}}
        
    intent = interpretation.get("intent")
    
    df = engine.processed_df
    df_with_actions = RuleEngine.apply_rules(df)
    
    # Strict Hierarchical Filter Enforcement
    if request.role == 'Zonal Sales Manager' and request.zone:
        df_with_actions = df_with_actions[df_with_actions['Zone'] == request.zone]
    elif request.role == 'BDO' and request.bdo:
        df_with_actions = df_with_actions[df_with_actions['BDO'] == request.bdo]
    
    filtered_df = df_with_actions
    
    # Handle the specific new 5 daily actions
    if intent == "bdo_daily_actions":
        # Force sort by highest priority
        filtered_df = df_with_actions.sort_values('priority_score', ascending=False)
        top_samples = filtered_df.head(5) # Exactly 5 actions
    elif intent == "dormant_detection":
        filtered_df = df_with_actions[df_with_actions['is_dormant']]
        top_samples = filtered_df.sort_values('priority_score', ascending=False).head(15)
    elif intent == "payment_followup":
        filtered_df = df_with_actions[df_with_actions['outstanding_amount'] > 0]
        top_samples = filtered_df.sort_values('priority_score', ascending=False).head(15)
    elif intent == "high_value_detection":
        filtered_df = df_with_actions[df_with_actions['is_high_value']]
        top_samples = filtered_df.sort_values('priority_score', ascending=False).head(15)
    elif intent == "geo_analysis":
        top_samples = df_with_actions.sort_values('total_revenue', ascending=False).head(15)
    else:
        top_samples = df_with_actions.sort_values('priority_score', ascending=False).head(15)
        
    cols_to_extract = ['Zone', 'Zonal Manager', 'BDO', 'Dealer Name', 'State', 'City', 'total_revenue', 'outstanding_amount', 'days_since_last_order', 'open_order_value', 'priority_score', 'actions']
    available_cols = [c for c in cols_to_extract if c in top_samples.columns]
    
    top_samples_list = top_samples[available_cols].to_dict(orient="records")
    
    context = {
        "user_query": query,
        "user_role": request.role,
        "active_hierarchy": {"zone": request.zone, "bdo": request.bdo},
        "intent": intent,
        "metrics": {
            "total_matched": len(filtered_df), 
            "total_revenue_matched": float(filtered_df['total_revenue'].sum() if 'total_revenue' in filtered_df.columns else 0),
            "total_outstanding_matched": float(filtered_df['outstanding_amount'].sum() if 'outstanding_amount' in filtered_df.columns else 0)
        },
        "samples": top_samples_list
    }
    
    explanation = llm.get_explanation(context)
    
    return {
        "explanation": explanation,
        "data": top_samples_list
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
