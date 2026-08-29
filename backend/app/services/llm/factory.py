from typing import Optional
from app.services.llm.base import BaseLLMClient
from app.services.llm.gemini_client import GeminiClient

_gemini_instance: Optional[GeminiClient] = None


def get_llm_client() -> BaseLLMClient:
    """Factory function to retrieve configured LLM client instance.
    Returns:
        BaseLLMClient instance (Gemini).
    """
    global _gemini_instance
    if _gemini_instance is None:
        _gemini_instance = GeminiClient()
    return _gemini_instance
