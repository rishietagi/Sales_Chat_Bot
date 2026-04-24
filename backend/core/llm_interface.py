import os
import logging
import google.generativeai as genai
import requests

logger = logging.getLogger(__name__)

class LLMInterface:
    """Unified LLM interface supporting Groq and Gemini with per-request API keys."""

    def __init__(self):
        # Default keys from environment
        self.default_groq_key = os.environ.get("GROQ_API_KEY")
        self.default_gemini_key = os.environ.get("GEMINI_API_KEY")
        self._call_count = 0

    def generate_explanation(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str = "gemini-1.5-flash",
        api_key: str = None
    ) -> str:
        """Routes the request to the appropriate LLM provider."""
        self._call_count += 1
        
        # Detect provider from model name
        if "gemini" in model.lower():
            key = api_key or self.default_gemini_key
            return self._call_gemini(system_prompt, user_prompt, model, key)
        else:
            key = api_key or self.default_groq_key
            return self._call_groq(system_prompt, user_prompt, model, key)

    def _call_gemini(self, system_prompt: str, user_prompt: str, model: str, api_key: str) -> str:
        if not api_key:
            return "⚠️ **GEMINI_API_KEY NOT CONFIGURED**"
        
        try:
            # Configure per-request
            genai.configure(api_key=api_key)
            
            # Use the generativeai package
            gen_model = genai.GenerativeModel(
                model_name=model,
                system_instruction=system_prompt
            )
            response = gen_model.generate_content(user_prompt)
            return response.text
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            return f"**Gemini API Error:** `{str(e)}`"

    def _call_groq(self, system_prompt: str, user_prompt: str, model: str, api_key: str) -> str:
        if not api_key:
            return "⚠️ **GROQ_API_KEY NOT CONFIGURED**"
        
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.1,
            "max_tokens": 1024,
        }
        
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=30)
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"Groq API error: {e}")
            return f"**Groq API Error:** `{str(e)}`"

    @property
    def call_count(self) -> int:
        return self._call_count
