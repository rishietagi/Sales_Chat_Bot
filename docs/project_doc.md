# Project Documentation: Next Best Action Sales Assistant

## 1. Overview
The "Next Best Action" assistant is a deterministic, AI-powered tool designed to help Business Development Officers (BDOs) at Himani Best Choice manage their sales pipeline. It transforms raw Excel data into actionable insights, prioritized tasks, and pricing guidance.

## 2. Data Strategy
The application relies on a flat-joined dataset (`emami_flat_joined_dataset.xlsx`) which contains Master, Sauda, and DO records. 

### Active-Row-First Aggregation
To prevent data ambiguity (e.g., pulling pending quantities from Delivery Order rows), the engine uses a sorting-based aggregation:
- It filters the dataframe for a specific BDO.
- It sorts by `active_contract_flag` descending (ensuring Sauda rows appear first).
- It groups by `contract_no` and takes the `first` value for attributes like `pending_qty`, `material_desc`, and `excel_row`.

## 3. Core Components

### Frontend
- **Interface**: A modern chat dashboard with real-time KPI cards.
- **KPIs**: Displays Total Dealers, Active Dealers, Active Contract Ratios, and **Total Booked Revenue**.
- **Logic**: Dynamic model switching and conditional table rendering.

### Backend (FastAPI)
- **DataLoader**: Ingests and cleans the Excel source.
- **FeatureEngineer**: Derives SKU-level pricing stats (IQR, guidance ranges, and outliers) and high-level KPIs.
- **IntentRouter**: Routes 24+ business queries to the correct logic handlers.
- **DecisionEngine**: A deterministic rule-based engine that generates exactly 5 priority-scored tasks for the day.
- **PromptBuilder**: Contextualizes data for the LLM while enforcing strict "No Call" and "No Excel Row" communication rules.

## 4. Key Business Rules
- **SKU-Level Pricing**: All pricing guidance is computed at the SKU level (e.g., "HBC RPO 1L POUCH") to ensure specificity.
- **Communication Standards**: The AI is instructed never to use the phrase "call dealer". Instead, it suggests "Follow up with" or "Inform".
- **Data Privacy**: No Excel row numbers or internal indices are shared in the final natural language output.
- **Active Dealer**: Defined as having at least one non-empty contract or sales document.
- **Task Priority**: 
    - **P1 Critical**: Contracts expiring in ≤3 days with pending quantity.
    - **P2 High**: Deliveries arriving today.
    - **P3 Medium**: Contracts expiring in 4-7 days with pending quantity.
    - **P4 Low**: Routine follow-ups and data audits.

## 5. Workflow
1.  **Ingestion**: `DataLoader` loads the flat dataset.
2.  **Request**: User selects a BDO and enters a query.
3.  **Routing**: `IntentRouter` classifies the intent.
4.  **Analysis**: `AnalyticsEngine` or `FeatureEngineer` processes the data.
5.  **Prompting**: `PromptBuilder` prepares a grounded context window.
6.  **Response**: UI displays the natural language answer and a clean data table (excluding row numbers).
