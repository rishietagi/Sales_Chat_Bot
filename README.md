# Next Best Action: BDO Sales Assistant

A high-performance dealer analytics and "Next-Best-Action" system designed for Business Development Officers (BDOs). The application interprets operational signals from the `emami_flat_joined_dataset.xlsx` and provides deterministic insights, prioritized action lists, and SKU-level pricing guidance.

## 🚀 Architecture
- **Backend**: FastAPI (Python 3.10+) serving a modular, deterministic analytics engine.
- **Frontend**: Premium HTML/Vanilla JS Dashboard with a sidebar-based chat interface.
- **Data Engine**: Pandas-based "Active-Row-First" aggregation strategy to differentiate between Sauda (Contract) and DO (Dispatch) data.
- **LLM Layer**: Multi-model support for Google Gemini and Groq, grounded by a context-rich Prompt Engineering layer.

## 📂 Project Structure
- `backend/core/`: The modular "Brain" of the application.
  - `data_loader.py`: Optimized ingestion and cleaning of the flat dataset.
  - `feature_engineering.py`: KPI computation and SKU-level pricing stats.
  - `intent_router.py`: Keyword-based routing for 24+ unique business intents.
  - `analytics_engine.py`: Deterministic data filtering and sorting.
  - `decision_engine.py`: Priority-scored rule engine for the "Top 5 Actions".
  - `prompt_builder.py`: Advanced prompt engineering for grounded AI responses.
- `frontend/`: Modern UI assets (HTML, CSS, JS).
- `data/`: Source Excel files and processed data.
- `docs/`: Technical documentation and BDO-specific data audits.

## 📊 Key Features
- **Deterministic Next-Best-Actions**: Rule-based prioritization (Critical P1 to Low P4) for dealer follow-ups.
- **SKU-Level Pricing Guidance**: Real-time IQR-based price analysis at the material level (not just oil type).
- **Active-Row Filtering**: Sophisticated deduplication that ensures contract metrics come from Sauda rows, not Delivery Orders.
- **Dashboard KPIs**: Real-time visibility into Total Dealers, Active Dealers, Contract Ratios, and Total Booked Revenue.
- **Grounded AI Chat**: Ask questions about pending quantities, deliveries today, expiring contracts, or payment aging.

## 🛠️ Setup Instructions

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Environment**:
   Create a `.env` file in the root with:
   ```env
   GOOGLE_API_KEY=your_gemini_key
   GROQ_API_KEY=your_groq_key
   DATA_PATH=data/emami_flat_joined_dataset.xlsx
   ```

3. **Launch the Application**:
   ```bash
   python -m backend.main
   ```
   The app will be available at `http://localhost:8000`.

## ⚖️ Business Rules
- **No "Call Dealer" Instruction**: AI suggests "Follow up" or "Inform" to maintain professional communication standards.
- **No Excel Row References**: Removed for cleaner natural language output.
- **Active Sauda Priority**: Contracts expiring in ≤3 days with pending quantity are always ranked as P1 Critical.
