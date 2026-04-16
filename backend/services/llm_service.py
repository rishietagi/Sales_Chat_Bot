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
        You are a senior sales strategy assistant and GenAI Solution Architect.
        Your role is to provide deep business insights and actionable decision support for the Himani Best Choice direct-dealer channel.
        
        You are answering a query from a user acting in the role: {context.get('user_role', 'National Sales Manager')}
        
        Based on the provided data context and user query, generate a comprehensive, executive response.
        Do NOT just restate the data; analyze it deeply.
        - Ground everything in the provided metrics.
        - Output your response strictly using this Markdown structure:

        ###  Direct Answer
        (1-2 sentences answering the query. If the user asks for 5 daily actions, strictly list them here or in Next-Best-Actions.)

        ###  Key Insights
        - (Insight 1: e.g. Why these dealers were selected, notable patterns)
        - (Insight 2: e.g. Anomaly or risk detected)

        ###  Next-Best-Actions
        - (Action 1: e.g. "Call Dealer X to resolve pending payment of Y")
        - (Action 2: ...)

        ###  Priority
        (State the urgency level and briefly explain why)

        ###  Supporting Metrics
        (Bullet points of the main metrics driving this conclusion, e.g. days since last order, outstanding payments, open order value)

        CONTEXT:
        {json.dumps(context, default=str, indent=2)}
        
        CONSTRAINTS:
        - Use ONLY the provided context. Do NOT invent facts or numbers.
        - Answer in concise, executive business language.
        - Be highly analytical and interpret the signals (e.g. high value + no recent orders = churn risk).
        """
        
        try:
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "You are a helpful dealer operations assistant."},
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
