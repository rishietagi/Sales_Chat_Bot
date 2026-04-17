import os
import json
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

class LLMService:
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("API Key is missing")
        self.client = Groq(api_key=api_key)
        self.model = "llama-3.3-70b-versatile"

    def get_explanation(self, context):
        """Generates a business explanation for the provided context."""
        prompt = f"""
        You are a senior sales strategy assistant for the Himani Best Choice direct-dealer channel.
        
        QUERY: "{context.get('user_query')}"
        ROLE: {context.get('user_role', 'National Sales Manager')}
        
        INSTRUCTION:
        1. Start with a ONE-LINE summary answering the query directly.
        2. Provide a bulleted list of "Next-Best-Actions" (NBA).
        3. CRITICAL: Every NBA bullet MUST include the Action, Dealer Name, Reason, and the specific Data Point (e.g., "Call Dealer_1017 to collect ₹12,810 outstanding" or "Contact Dealer_1240 regarding 65-day order gap").
        4. Do NOT provide headers, tables, or deep insights UNLESS the user explicitly requested a "detailed analysis", "table", or "header".
        5. Keep the tone professional, concise, and executive.
        
        CONTEXT DATA:
        {json.dumps(context, default=str, indent=2)}
        
        CONSTRAINTS:
        - Use ONLY the provided context.
        - If the user query is simple, the response MUST be extremely short.
        """
        
        try:
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "You are a concise dealer operations assistant. Always prioritize brevity unless details are requested."},
                    {"role": "user", "content": prompt}
                ],
                model=self.model,
            )
            return chat_completion.choices[0].message.content
        except Exception as e:
            return f"Error generating explanation: {str(e)}"

    def interpret_query(self, query):
        """Interprets the user query to identify intent and filters."""
        # In a real app, this would use the LLM to route to a specific analytics function.
        # For the POC, we can use a simple mapping or a small LLM call.
        prompt = f"""
        Interpret the user query and output a JSON with 'intent' and 'filters' (if any).
        Available Intents: dealer_ranking, dormant_detection, high_value_detection, open_order_followup, payment_followup, geo_analysis, sku_analysis, bdo_daily_actions.
        
        QUERY: "{query}"
        
        JSON VERSION:
        """
        try:
            chat_completion = self.client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=self.model,
                response_format={"type": "json_object"}
            )
            return chat_completion.choices[0].message.content
        except:
            return '{{"intent": "general_query", "filters": {{}}}}'
