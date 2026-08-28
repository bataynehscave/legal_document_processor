from typing import Optional
from app.core.config import settings
from app.core.exceptions import InvalidInputError
from app.services.llm.base import BaseLLMClient
from app.services.llm.gemini_client import GeminiClient
from app.services.llm.openai_client import OpenAIClient

_gemini_instance: Optional[GeminiClient] = None
_openai_instance: Optional[OpenAIClient] = None


def get_llm_client(provider: Optional[str] = None) -> BaseLLMClient:
    """Factory function to retrieve configured LLM client instance.

    Args:
        provider: 'gemini' or 'openai'. If None, defaults to settings.LLM_PROVIDER.

    Returns:
        BaseLLMClient instance.
    """
    global _gemini_instance, _openai_instance
    selected_provider = (provider or settings.LLM_PROVIDER).lower().strip()

    if selected_provider == "gemini":
        if _gemini_instance is None:
            _gemini_instance = GeminiClient()
        return _gemini_instance

    if selected_provider == "openai":
        if _openai_instance is None:
            _openai_instance = OpenAIClient()
        return _openai_instance

    raise InvalidInputError(
        f"Unsupported LLM provider '{provider}'. Supported providers are: 'gemini', 'openai'."
    )
