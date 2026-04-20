# Dealer Operations AI Assistant

A high-performance dealer analytics and next-best-action system designed for sales teams. The application interprets operational signals from multi-sheet Excel workbooks and provides actionable call lists and natural language insights.

## 🚀 Architecture
- **Backend**: FastAPI (Python) serving a modular analytics engine.
- **Frontend**: Polished Streamlit Dashboard (v2) with interactive charts.
- **Data Engine**: Pandas-based multi-sheet join and metrics derivation.
- **LLM Layer**: Groq (`llama-3.1-8b-instant`) for query interpretation and business explanations.

## 📂 Project Structure
- `backend/`: Core logic
  - `config/`: Application settings and business thresholds.
  - `services/`: Data processing, rule implementation, and LLM interface.
  - `main.py`: FastAPI server (for future React conversion).
- `app_v2.py`: The production-grade Streamlit interface.
- `scripts/`: Validation and data processing scripts.
- `docs/`: Knowledge base and schema definitions.
- `data/`: Ingestion and processed outputs.

## 🛠️ Setup Instructions

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Environment**:
   Ensure `.env` contains your `GROQ_API_KEY`.

3. **Run Validation**:
   ```bash
   $env:PYTHONPATH="."; python scripts/validate_pipeline.py
   ```

4. **Launch the Dashboard**:
   ```bash
   streamlit run app_v2.py
   ```

## 📊 Key Features
- **Dormant Dealer Detection**: Automatically flags accounts with no orders for >30 days.
- **High-Value Prioritization**: Ranks dealers by total revenue and frequency.
- **Operational Signals**: Tracks open orders, fulfillment gaps, and pending payments.
- **AI Chat**: Ask questions like "Which state has the highest outstanding amount?" or "Who should I call in Lucknow?"
- **Exportable Call Lists**: One-click download of prioritized action items.
