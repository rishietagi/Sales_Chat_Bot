from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
import pandas as pd
import os
import logging
from pydantic import BaseModel
from backend.config.settings import settings

# Import modular components from backend.core
from backend.core.data_loader import DataLoader
from backend.core.feature_engineering import FeatureEngineer
from backend.core.intent_router import IntentRouter
from backend.core.analytics_engine import AnalyticsEngine
from backend.core.prompt_builder import PromptBuilder
from backend.core.llm_interface import LLMInterface
from backend.core.schema_registry import SCHEMA_DICT

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Himani Best Choice BDO Assistant")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances initialized on startup
# We'll wrap these in a way that handles the case where data might not be ready
try:
    loader = DataLoader(settings.DATA_PATH)
    df = loader.load_and_clean()
    intent_router = IntentRouter()
    analytics_engine = AnalyticsEngine(df)
    prompt_builder = PromptBuilder(SCHEMA_DICT)
    llm = LLMInterface()
    fe = FeatureEngineer(df)
    logger.info("Backend services initialized successfully.")
except Exception as e:
    logger.error(f"Failed to initialize backend services: {e}")
    df = pd.DataFrame()

# Mount static files
app.mount("/static", StaticFiles(directory="frontend"), name="static")

@app.get("/", response_class=HTMLResponse)
async def read_index():
    with open(os.path.join("frontend", "index.html"), "r", encoding="utf-8") as f:
        return f.read()

@app.get("/api/bdos")
def get_bdos():
    if df.empty:
        return {"bdos": []}
    bdos = sorted([b for b in df['bdo'].unique().tolist() if b != "Unknown"])
    return {"bdos": bdos}

@app.get("/api/models/gemini")
def get_gemini_models(api_key: str):
    if not api_key:
        return {"models": []}
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        models = []
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                models.append({
                    "name": m.name,
                    "display": m.display_name
                })
        return {"models": models}
    except Exception as e:
        logger.error(f"Error fetching Gemini models: {e}")
        return {"error": str(e), "models": []}

@app.get("/api/metrics")
def get_metrics(bdo: str = ''):
    if df.empty:
        return {"error": "Data not loaded"}
    if not bdo:
        return {"error": "BDO not selected"}
    metrics = fe.get_bdo_metrics(bdo)
    return metrics

class QueryRequest(BaseModel):
    query: str
    api_key: str
    bdo: str
    model: str = "gemini-1.5-flash"

@app.post("/api/chat")
async def process_query(request: QueryRequest):
    if not request.query or not request.bdo:
        raise HTTPException(status_code=400, detail="Query and BDO are required")
    
    # Set API key for this request if provided
    if request.api_key:
        os.environ["GROQ_API_KEY"] = request.api_key
        # Note: LLMInterface now handles key per-request internally

    try:
        # Route intent
        routing = intent_router.route_intent(request.query)
        intent_family = routing["family"]
        metadata = routing["metadata"]

        # Execute deterministic analytics
        analytics_result = analytics_engine.execute_query(intent_family, request.bdo, **metadata)

        # Build prompt
        sys_p, usr_p = prompt_builder.build_prompt(request.query, request.bdo, analytics_result)

        # Call LLM
        explanation = llm.generate_explanation(sys_p, usr_p, model=request.model, api_key=request.api_key)

        # Prepare response data - only if specifically requested via keywords
        show_table = any(kw in request.query.lower() for kw in ["table", "list", "details", "show", "all", "top 5", "top five", "actions"])
        data = []
        if show_table:
            if "data" in analytics_result:
                data = analytics_result["data"]
            elif "actions" in analytics_result:
                data = analytics_result["actions"]

        return {
            "explanation": explanation,
            "data": data,
            "intent": intent_family
        }
    except Exception as e:
        logger.error(f"Error processing query: {e}")
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
