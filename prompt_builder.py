import json
import pandas as pd
import datetime

# Human‑readable labels for each intent
INTENT_LABELS = {
    "dealer_ranking": "Top Dealers by Sales",
    "dormant_dealers": "Dormant Dealers – Reactivation Targets",
    "slowing_dealers": "Dealers Whose Buying Is Slowing Down",
    "status_follow_up": "Orders Stuck in Non-Final Statuses",
    "territory_performance": "Territory Performance Comparison",
    "product_analysis": "Product Line Performance",
    "time_trend": "Sales Trends Over Time",
    "contact_lookup": "Dealer Contact Lookup",
}

# Intent-specific instruction blocks appended to the user prompt
_INTENT_INSTRUCTIONS: dict[str, str] = {
    "dormant_dealers": (
        "Stress urgency — these dealers are at risk of churning. "
        "For each dealer, state EXACTLY how many days since their last order "
        "and recommend a specific outreach action (call, email, visit)."
    ),
    "slowing_dealers": (
        "Highlight the percentage sales drop for each dealer and compare their "
        "recent-period spending to their prior-period spending. "
        "Suggest concrete retention plays for each."
    ),
    "status_follow_up": (
        "Focus on operational urgency. State the exact count of stuck orders per "
        "dealer and recommend whether the rep should escalate, call the dealer, "
        "or coordinate with internal operations."
    ),
    "territory_performance": (
        "Rank territories clearly. Call out the best AND worst performers. "
        "Mention dormant dealer counts and blocked orders if available."
    ),
    "contact_lookup": (
        "Return dealer name, contact person, and phone number prominently. "
        "Add a one-line context note per dealer (e.g., total sales, last order)."
    ),
    "dealer_ranking": (
        "Highlight the top 5 dealers and their contribution. Mention if any top "
        "dealer shows warning signs (slowing, dormant, stuck orders)."
    ),
    "product_analysis": (
        "Rank product lines and note which have the most dealers buying them. "
        "Flag any product line with declining sales if visible in the data."
    ),
    "time_trend": (
        "Describe the sales trajectory. Call out the best and worst months/quarters. "
        "Mention month-over-month change percentages where available."
    ),
}


class PromptBuilder:
    """Creates compact, structured contexts for the Groq LLM."""

    def __init__(self, schema_dict: dict):
        self.schema_dict = schema_dict

    def build_prompt(
        self, user_question: str, intent: str, result_df: pd.DataFrame,
        chat_history: list[dict] | None = None,
    ) -> tuple[str, str]:
        """Returns (system_prompt, user_prompt) ready for the Groq API."""

        capped = result_df.head(15)

        # Drop columns the LLM doesn't need to save tokens
        drop = {"action_labels", "contact_first", "contact_last",
                "last_order_date", "top_pl_sales", "prev_sales"}
        cols_to_drop = [c for c in drop if c in capped.columns]
        slim = capped.drop(columns=cols_to_drop, errors="ignore")

        compact_data = self._serialise(slim)
        intent_label = INTENT_LABELS.get(intent, intent)
        intent_instr = _INTENT_INSTRUCTIONS.get(intent, "")

        system_prompt = self._system_prompt()
        user_prompt = self._user_prompt(
            user_question, intent, intent_label, compact_data,
            len(slim), intent_instr, chat_history,
        )
        return system_prompt, user_prompt

    # ------------------------------------------------------------------ #
    #  System prompt                                                      #
    # ------------------------------------------------------------------ #
    def _system_prompt(self) -> str:
        return f"""You are a senior Sales Operations Advisor embedded inside an analytics platform.
Your job is to turn pre-computed data into clear, actionable business guidance for a sales rep.

--- ABSOLUTE RULES ---
1. NEVER invent, estimate, or recalculate any number. Every figure you cite MUST appear in the COMPUTED RESULTS payload.
2. NEVER reference internal column names, pandas, or technical jargon. Speak in plain business English.
3. CUSTOMERNAME = the dealer / retail account.  contact_name = the contact person.
4. When a dealer appears in the results, always mention the dealer name and, if available, the contact person and phone number so the rep can act immediately.
5. When "recommended_actions" or "action_reasons" are present, explain WHY each label was assigned by citing the exact metric.
6. If the computed results are empty, say "No matching records were found for this query" and suggest the user try adjusting filters.

--- RESPONSE STRUCTURE ---
Respond in Markdown using exactly these three sections:

### Key Findings
A concise bullet list (3-6 bullets) of the most important insights. Each bullet must cite at least one specific number from the payload.

### Priority Actions
A numbered list of the top 3-5 actions the sales rep should take TODAY, ordered by urgency. Each action must name the specific dealer/territory/product and explain why.

### Recommended Next Steps
2-3 sentences of broader strategic advice based on the pattern in the data.

--- FEW-SHOT EXAMPLE ---
If the query is "Who are our top dealers by sales?" and the top dealer is "Acme Corp" with $500,000 in sales, 12 orders, contact "John Doe" at 555-1234, your response should look like:

### Key Findings
- **Acme Corp** leads with $500,000 across 12 orders — a clear key account.
- The top 5 dealers contribute 60% of total revenue in this segment.

### Priority Actions
1. **Schedule a quarterly business review with Acme Corp** (John Doe, 555-1234) to protect the $500K relationship and explore upsell.

### Recommended Next Steps
Focus relationship-management resources on the top 5 accounts. Consider assigning a dedicated rep to each.

--- COLUMN DICTIONARY ---
{json.dumps(self.schema_dict, indent=2)}
"""

    # ------------------------------------------------------------------ #
    #  User prompt                                                        #
    # ------------------------------------------------------------------ #
    def _user_prompt(
        self,
        question: str,
        intent: str,
        intent_label: str,
        compact_data: list[dict],
        row_count: int,
        intent_instruction: str,
        chat_history: list[dict] | None,
    ) -> str:
        parts: list[str] = []

        # Conversation context (last 3 turns)
        if chat_history:
            recent = [m for m in chat_history if m["role"] == "user"][-3:]
            if recent:
                hist = "\n".join(f"- {m['content']}" for m in recent)
                parts.append(f"RECENT CONVERSATION:\n{hist}\n")

        parts.append(f"USER QUESTION: {question}")
        parts.append(f"DETECTED ANALYSIS TYPE: {intent_label} (code: {intent})")
        parts.append(f"\nCOMPUTED RESULTS ({row_count} rows):")
        parts.append(json.dumps(compact_data, indent=2))

        parts.append("\nInstructions:")
        parts.append("- Answer the user's question using ONLY the data above.")
        parts.append("- For every dealer mentioned, include the contact person and phone if available.")
        parts.append("- For every action label, explain the specific metric that triggered it using the action_reasons field.")
        parts.append("- Keep the response under 400 words.")

        if intent_instruction:
            parts.append(f"\nSPECIAL FOCUS FOR THIS QUERY TYPE:\n{intent_instruction}")

        return "\n".join(parts)

    # ------------------------------------------------------------------ #
    #  Helpers                                                            #
    # ------------------------------------------------------------------ #
    @staticmethod
    def _serialise(df: pd.DataFrame) -> list[dict]:
        """Converts a DataFrame to JSON-safe list of dicts."""
        return json.loads(df.to_json(orient="records", date_format="iso"))
