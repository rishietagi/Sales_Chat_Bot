# Project Documentation: AI Chatbot for Sales (BDO Assistant)

## 1. Approach & Philosophy
The project is built on the philosophy of **Deterministic AI**. Instead of allowing the LLM to perform complex calculations on raw data (which often leads to hallucinations), we use a **Modular Analytical Pipeline**:
1.  **Extract**: Categorize user intent using keywords.
2.  **Analyze**: Execute hard-coded Pandas logic to get the exact numbers/dataframes.
3.  **Summarize**: Pass only the necessary data to the LLM for natural language generation.

This ensures that while the interaction feels like a conversation, the numbers and business rules are 100% accurate.

## 2. Methodology
- **Intent Routing**: Categorizes queries into family groups (Contract, Dispatch, Collection, etc.).
- **Subtype Metadata**: Extracts specific context like "aging", "expiring", or "today".
- **Grounding**: The LLM is provided with a strict system prompt and "Computed Data" to prevent it from making up metrics.
- **Priority Scoring**: Uses a tiered system (P1 to P5) to rank BDO tasks.
- **Pricing Analytics**: Uses Interquartile Range (IQR) to detect pricing outliers and recommends the Q1-Q3 range as a "safe" negotiation zone for new contracts.

## 3. Architecture
The system follows a classic **Client-Server architecture** with a decoupled core:

### Frontend
- **Interface**: A modern chat dashboard.
- **Logic**: Dynamic model fetching from the Gemini API and conditional table rendering based on user intent.

### Backend (FastAPI)
- **API Layer**: Handles `/api/chat`, `/api/metrics`, and `/api/models` endpoints.
- **Core Engine**:
    - `DataLoader`: Reads the `emami_flat_joined_dataset.xlsx`.
    - `FeatureEngineer`: Computes KPIs for the dashboard header.
    - `IntentRouter`: Maps natural language to analytical handlers.
    - `AnalyticsEngine`: The "brain" that filters and sorts data.
    - `DecisionEngine`: The logic that generates the "Top 5 Tasks".
    - `LLMInterface`: Routes prompts to either Google Gemini or Groq.

## 4. Workflow
1.  **Initialization**: On server start, the `DataLoader` loads the Excel dataset into memory.
2.  **Request**: User selects a BDO and enters a query (e.g., "Which contracts expire soon?").
3.  **Routing**: The `IntentRouter` identifies the query as `contract` with subtype `expiring`.
4.  **Analysis**: The `AnalyticsEngine` filters the dataframe for contracts ending in ≤7 days.
5.  **Prompting**: The `PromptBuilder` creates a context window containing the filtered list.
6.  **Inference**: The `LLMInterface` sends the prompt to the selected model (e.g., Gemini 2.0 Flash).
7.  **Response**: The UI displays a natural language summary and (if requested) a data table.

## 5. Key Business Rules
- **Active Dealer**: Has at least one non-empty contract or sales document.
- **Dormant Dealer**: Exists in the master file but has zero active business.
- **Task Priority**: Expiring contracts (≤3 days) with pending quantity always take precedence over general follow-ups.
