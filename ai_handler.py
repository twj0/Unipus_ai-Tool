# File: ai_handler.py
import requests, json, re
from abc import ABC, abstractmethod
import google.generativeai as genai

class BaseAIProvider(ABC):
    def __init__(self, api_key: str):
        if not api_key: raise ValueError("API key is missing for AI provider.")
        self.api_key = api_key
    @abstractmethod
    def call_ai(self, prompt: str) -> str: pass

class DashScopeProvider(BaseAIProvider):
    def call_ai(self, prompt: str) -> str:
        payload = {"model": "qwen-plus", "input": {"prompt": prompt}, "parameters": {"result_format": "text"}}
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        try:
            response = requests.post("https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation", headers=headers, data=json.dumps(payload), timeout=30)
            response.raise_for_status(); return response.json()['output']['text']
        except Exception as e: return f"Error calling DashScope: {e}"

class GeminiProvider(BaseAIProvider):
    def __init__(self, api_key: str):
        super().__init__(api_key); genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-pro')
    def call_ai(self, prompt: str) -> str:
        try: return self.model.generate_content(prompt).text
        except Exception as e: return f"Error calling Gemini: {e}"

class DeepSeekProvider(BaseAIProvider):
    def call_ai(self, prompt: str) -> str:
        payload = {"model": "deepseek-chat", "messages": [{"role": "user", "content": prompt}]}
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        try:
            response = requests.post("https://api.deepseek.com/chat/completions", headers=headers, data=json.dumps(payload), timeout=30)
            response.raise_for_status(); return response.json()['choices'][0]['message']['content']
        except Exception as e: return f"Error calling DeepSeek: {e}"

AI_PROVIDERS = {"Qwen (DashScope)": DashScopeProvider, "Gemini": GeminiProvider, "Deep Seek": DeepSeekProvider}

# In ai_handler.py

class GroqProvider(BaseAIProvider):
    """Provider for Groq's high-speed inference engine."""
    def call_ai(self, prompt: str) -> str:
        payload = {
            # Models like 'llama3-8b-8192' or 'mixtral-8x7b-32768'
            "model": "llama3-8b-8192",
            "messages": [{"role": "user", "content": prompt}],
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        try:
            # Note: Groq's endpoint is different from OpenAI/DeepSeek
            response = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers,
                data=json.dumps(payload),
                timeout=30
            )
            response.raise_for_status()
            return response.json()['choices'][0]['message']['content']
        except Exception as e:
            return f"Error calling Groq: {e}"
def get_ai_provider(provider_name: str, api_key: str) -> BaseAIProvider:
    provider_class = AI_PROVIDERS.get(provider_name)
    if not provider_class: raise ValueError(f"Unknown AI provider: {provider_name}")
    return provider_class(api_key=api_key)