# Tech Stack: Next Best Action Assistant

This document outlines the primary technologies and libraries used in the Next Best Action Sales Assistant.

## 1. Backend & Server
- **Python (3.10+)**: The core programming language.
- **FastAPI**: Modern web framework for high-performance REST APIs.
- **Uvicorn**: ASGI web server for running the FastAPI application.
- **Pydantic**: Data validation and type safety for API requests.

## 2. Data Processing & Analytics
- **Pandas**: Core engine for data manipulation, cleaning, and complex aggregations.
- **"Active-Row-First" Logic**: Custom logic to ensure Sauda-level metrics are preferred over DO-level metrics during grouping.
- **SKU-Level Pricing**: IQR-based outlier detection and guidance computed per material description.
- **openpyxl**: Excel engine for reading `.xlsx` files.

## 3. AI & Language Models (LLM)
- **Multi-Model Support**: The system supports dynamic switching between providers.
- **Google Gemini API**: 
  - Models: Gemini 2.0 Flash, Gemini 1.5 Pro, Gemini 1.5 Flash.
  - SDK: `google-generativeai`.
- **Groq API**:
  - Models: Llama 3.3 70B, Llama 3.1 8B.
  - Integration: RESTful API via `requests`.

## 4. Frontend & User Interface
- **HTML5 / CSS3 / Vanilla JS**: Responsive, premium dashboard with a sidebar-based layout.
- **Cache-Busting (v1)**: Implemented script versioning to ensure latest logic loads immediately.
- **Marked.js**: Renders AI-generated Markdown into rich text and bullet points.
- **Responsive Design**: Custom CSS grid and flexbox layout for mobile and desktop support.

## 5. Configuration & Environment
- **python-dotenv**: Securely manages API keys via `.env` files.
- **CORS Middleware**: Enabled for local and remote browser interaction.

## 6. Core Logic Packages (`backend/core/`)
- **DataLoader**: Optimized loading and initial cleaning of Excel datasets.
- **FeatureEngineer**: Computes 6 core business KPIs, including the newly added Total Booked Revenue.
- **IntentRouter**: Keyword-based classification engine for routing 24+ specific business queries.
- **AnalyticsEngine**: Deterministic logic layer that executes pandas queries based on identified intent.
- **DecisionEngine**: Priority-scoring algorithm (P1-P4) for Next-Best-Actions (Follow-up focused).
- **LLMInterface**: Unified wrapper for dual-provider (Google/Groq) inference.
- **PromptBuilder**: Advanced prompt engineering for grounded AI responses, excluding row-number references.
