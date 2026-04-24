import os
import json
import re
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

# Keyword-based intent matching for deterministic routing
KEYWORD_INTENT_MAP = [
    (r"5 task|daily action|today.{0,10}task|task.{0,10}today|what should i do", "daily_actions"),
    (r"pending payment|follow.?up.*payment|collection follow|outstanding payment", "pending_payments"),
    (r"dormant|inactive dealer|not order|stopped order", "dormant_dealers"),
    (r"active dealer|how many active|who.*active|active.*dealer|have active order", "active_dealers"),
    (r"dispatch left|pending dispatch|dispatch pending|dispatch remain|how much dispatch", "pending_dispatch"),
    (r"%.*collect|percentage.*collect|yet to be collected|amount.*collected|collection percent|uncollected", "collection_percentage"),
]

def match_intent_by_keywords(query: str):
    """Deterministic keyword-based intent matching. Returns intent or None."""
    query_lower = query.lower().strip()
    for pattern, intent in KEYWORD_INTENT_MAP:
        if re.search(pattern, query_lower):
            return intent
    return None


class LLMService:
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("API Key is missing")
        self.client = Groq(api_key=api_key)
        self.model = "llama-3.3-70b-versatile"

    def get_explanation(self, context):
        """Generates a business explanation for the provided context."""
        intent = context.get('intent', 'general_query')
        answer_summary = context.get('answer_summary', {})

        # Build intent-specific instruction
        intent_instructions = self._get_intent_instruction(intent, answer_summary)

        prompt = f"""You are a senior sales strategy assistant for the Himani Best Choice direct-dealer channel.

QUERY: "{context.get('user_query')}"
ROLE: {context.get('user_role', 'National Sales Manager')}
INTENT: {intent}

TASK:
1. FIRST, evaluate if the QUERY is related to dealer operations, sales, or the provided context. If it is completely unrelated (e.g., recipes, general knowledge), reply ONLY with: "I am a Sales Assistant and can only answer questions related to your dealer operations and sales data." and STOP.
2. If related, follow the SPECIFIC INSTRUCTION below exactly.

SPECIFIC INSTRUCTION:
{intent_instructions}

PRE-COMPUTED ANSWER:
{json.dumps(answer_summary, default=str, indent=2)}

DEALER SAMPLES:
{json.dumps(context.get('samples', []), default=str, indent=2)}

STRICT RULES:
- Use ONLY the provided data. Do not invent dealers or numbers.
- NEVER output raw column names like 'pending_dispatch_qty', 'outstanding_amount', 'priority_score'.
- NEVER include "Data Point:" or technical metadata in your response.
- For dispatch issues: ALWAYS say "Contact Warehouse", never suggest contacting the dealer.
- For payments: Say "Call [Dealer Name] to collect ₹X outstanding".
- Keep the response concise and professional. No headers or tables unless explicitly asked.
- The PRE-COMPUTED ANSWER contains the definitive numbers. Use those exact numbers.
"""

        try:
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "You are a concise dealer operations assistant. You present pre-computed business answers in clean, professional language. Never show raw data column names or technical metadata."},
                    {"role": "user", "content": prompt}
                ],
                model=self.model,
            )
            return chat_completion.choices[0].message.content
        except Exception as e:
            return f"Error generating explanation: {str(e)}"

    def _get_intent_instruction(self, intent, summary):
        """Returns intent-specific prompt instructions."""
        if intent == "daily_actions":
            actions = summary.get('formatted_actions', [])
            actions_text = "\n".join(f"  {i+1}. {a}" for i, a in enumerate(actions))
            return f"""Present exactly these tasks as a clean numbered list. Do NOT add reasons, data points, or column names.

Tasks to present:
{actions_text}

Start with "You have {summary.get('task_count', 5)} tasks for today." then list them."""

        elif intent == "active_dealers":
            return f"""State the count clearly: "{summary.get('active_count', 'N/A')} out of {summary.get('total_count', 'N/A')} dealers have active (open) orders."
Then list each active dealer by name with their open order count."""

        elif intent == "dormant_dealers":
            return f"""State: "{summary.get('dormant_count', 'N/A')} out of {summary.get('total_count', 'N/A')} dealers are dormant (no orders in 30+ days and no open orders)."
Then list each dormant dealer with how many days since their last order."""

        elif intent == "pending_payments":
            return f"""State: "₹{summary.get('total_outstanding', 0):,.2f} is outstanding across {summary.get('dealers_with_outstanding', 0)} dealers."
Then list each dealer with their outstanding amount as a follow-up action."""

        elif intent == "pending_dispatch":
            return f"""State: "{summary.get('total_pending_cases', 0)} cases are pending dispatch across {summary.get('dealers_with_pending', 0)} dealers."
Then list each dealer and the exact number of pending cases. Ensure you mention "cases" or "quantity", NOT currency values. Always say "Contact Warehouse" for dispatch."""

        elif intent == "collection_percentage":
            return f"""State the answer directly: "{summary.get('uncollected_pct', 'N/A')}% of the total active order value is yet to be collected."
Then briefly list the top dealers with the highest outstanding amounts."""

        else:
            return "Provide a concise answer based on the data. Start with a one-line summary, then provide Next-Best-Actions as bullet points."

    def interpret_query(self, query):
        """Interprets the user query to identify intent and filters."""
        prompt = f"""Classify the user query into ONE intent and output a JSON object.

INTENTS AND THEIR DEFINITIONS:
- "daily_actions": User asks for daily tasks, top 5 actions, what to do today.
- "pending_payments": User asks about outstanding payments, collection follow-ups, who owes money.
- "dormant_dealers": User asks about dormant/inactive dealers, who stopped ordering.
- "active_dealers": User asks about active dealers, how many are active, who has open/active orders.
- "pending_dispatch": User asks about pending dispatch, dispatch left, open order fulfillment.
- "collection_percentage": User asks what percentage of amount is collected/uncollected.
- "high_value_detection": User asks about high-value dealers, top dealers by revenue.
- "geo_analysis": User asks about specific zones, states, cities, or geographic performance.
- "general_query": Anything else related to sales/dealers.

QUERY: "{query}"

Output JSON with:
- "intent": one of the intents above
- "filters": any specific filters mentioned (zone, city, state, dealer name)
- "show_table": true ONLY if user explicitly asks to see "raw data", "dataset", "data table". Otherwise false.

JSON:"""

        try:
            chat_completion = self.client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=self.model,
                response_format={"type": "json_object"}
            )
            return chat_completion.choices[0].message.content
        except:
            return '{"intent": "general_query", "filters": {}, "show_table": false}'
