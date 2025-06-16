# File: ai_handler.py (Complete and Corrected Version)
import requests
import json
import re
from abc import ABC, abstractmethod
import google.generativeai as genai

# --- Prompt Engineering ---
def build_prompt(instruction: str, questions: list, options: list, blank_counts: list) -> str:
    """Builds the standardized prompt to be sent to the AI."""
    cleaned_questions = [re.sub(r"^\d+\.\s*", "", q).strip() for q in questions]
    questions_block = "\n".join([f"{i+1}. {q}" for i, q in enumerate(cleaned_questions)])
    options_block = ", ".join(options)
    
    prompt = f"""
You are an expert English test-solver. Your task is to solve a fill-in-the-blanks quiz.
Analyze the instruction, the questions, and the provided word bank carefully.
Place the most appropriate word or phrase from the options into each blank.

**Instruction:**
{instruction}

**Questions:**
{questions_block}

**Word Bank:**
{options_block}
"""
    if blank_counts:
        prompt += "\n**Structure:**\n"
        for i, count in enumerate(blank_counts):
            prompt += f"Question {i+1} has {count} blank(s).\n"
            
    prompt += """
**Output Format:**
You MUST provide ONLY the answers, without any explanation or pleasantries.
Follow this format strictly, separating answers for multiple blanks with a pipe character (|).

ANSWERS:
1. word1
2. word2|word3
3. word4
"""
    return prompt

def parse_ai_response(response_text: str) -> list:
    """Parses the raw text from the AI to extract a list of answers."""
    try:
        if not response_text:
            return []
        
        # Isolate the core answer block
        if "ANSWERS:" in response_text:
            response_text = response_text.split("ANSWERS:", 1)[1].strip()
            
        lines = response_text.splitlines()
        answers = []
        
        for line in lines:
            line = line.strip()
            if re.match(r"^\d+\.\s*", line):
                content = re.sub(r"^\d+\.\s*", "", line).strip()
                multi_answers = [ans.strip() for ans in content.split("|")]
                answers.append(multi_answers)
        return answers
    except Exception as e:
        print(f"Error parsing AI response: {e}")
        return []

# --- AI Provider Abstraction ---
class BaseAIProvider(ABC):
    """Abstract base class for all AI providers."""
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("API key is missing.")
        self.api_key = api_key

    @abstractmethod
    def call_ai(self, prompt: str) -> str:
        """Sends the prompt to the AI and returns the raw text response."""
        pass

# --- Concrete Implementations ---
class DashScopeProvider(BaseAIProvider):
    """Provider for Alibaba's DashScope (Qwen models)."""
    def call_ai(self, prompt: str) -> str:
        payload = {
            "model": "qwen-plus",
            "input": {"prompt": prompt},
            "parameters": {"result_format": "text"}
        }
        headers = { "Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json" }
        try:
            response = requests.post("https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation", headers=headers, data=json.dumps(payload), timeout=30)
            response.raise_for_status()
            return response.json()['output']['text']
        except Exception as e: return f"Error calling DashScope: {e}"

class GeminiProvider(BaseAIProvider):
    """Provider for Google's Gemini models."""
    def __init__(self, api_key: str):
        super().__init__(api_key)
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-pro')
    def call_ai(self, prompt: str) -> str:
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e: return f"Error calling Gemini: {e}"

class DeepSeekProvider(BaseAIProvider):
    """Provider for Deep Seek models (OpenAI-compatible API)."""
    def call_ai(self, prompt: str) -> str:
        payload = {"model": "deepseek-chat", "messages": [{"role": "user", "content": prompt}], "temperature": 0.1}
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        try:
            response = requests.post("https://api.deepseek.com/chat/completions", headers=headers, data=json.dumps(payload), timeout=30)
            response.raise_for_status()
            return response.json()['choices'][0]['message']['content']
        except Exception as e: return f"Error calling DeepSeek: {e}"

class ZhipuAIProvider(BaseAIProvider):
    """Provider for Zhipu AI's GLM models."""
    def call_ai(self, prompt: str) -> str:
        payload = {"model": "glm-4-flash", "messages": [{"role": "user", "content": prompt}]}
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        try:
            response = requests.post("https://open.bigmodel.cn/api/paas/v4/chat/completions", headers=headers, data=json.dumps(payload), timeout=30)
            response.raise_for_status()
            return response.json()['choices'][0]['message']['content']
        except Exception as e: return f"Error calling Zhipu AI: {e}"

class GroqProvider(BaseAIProvider):
    """Provider for Groq's high-speed inference engine."""
    def call_ai(self, prompt: str) -> str:
        payload = {"model": "llama3-8b-8192", "messages": [{"role": "user", "content": prompt}], "temperature": 0.1}
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        try:
            response = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, data=json.dumps(payload), timeout=30)
            response.raise_for_status()
            return response.json()['choices'][0]['message']['content']
        except Exception as e: return f"Error calling Groq: {e}"


# --- Factory Function ---
AI_PROVIDERS = {
    "Qwen (DashScope)": DashScopeProvider,
    "Gemini": GeminiProvider,
    "Deep Seek": DeepSeekProvider,
    "GLM-4 Flash (Zhipu)": ZhipuAIProvider,
    "Groq (Llama 3)": GroqProvider,
}

def get_ai_provider(provider_name: str, api_key: str) -> BaseAIProvider:
    """Factory function to get an instance of an AI provider."""
    provider_class = AI_PROVIDERS.get(provider_name)
    if not provider_class:
        raise ValueError(f"Unknown AI provider: {provider_name}")
    return provider_class(api_key=api_key)