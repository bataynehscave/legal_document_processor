import asyncio
import json
import logging
from typing import Optional
from google import genai
from google.genai import errors as genai_errors
from google.genai import types
from pydantic import ValidationError
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

from app.core.config import settings
from app.core.exceptions import (
    LLMAuthenticationError,
    LLMProviderError,
    LLMRateLimitError,
    LLMSchemaDecodeError,
    LLMTimeoutError,
)
from app.schemas.extraction import LLMContractExtraction
from app.services.llm.base import SYSTEM_PROMPT, BaseLLMClient

logger = logging.getLogger(__name__)


class GeminiClient(BaseLLMClient):
    """Production-ready Gemini LLM client using official google-genai SDK."""

    def __init__(self, api_key: Optional[str] = None) -> None:
        self.api_key = api_key or settings.GEMINI_API_KEY
        self._client: Optional[genai.Client] = None

    def _get_client(self) -> genai.Client:
        if not self.api_key:
            raise LLMAuthenticationError(
                "Gemini API key is not configured. Please set GEMINI_API_KEY in your environment or .env file."
            )
        if self._client is None:
            self._client = genai.Client(api_key=self.api_key)
        return self._client

    async def extract_contract_data(
        self,
        text: str,
        model: Optional[str] = None,
    ) -> LLMContractExtraction:
        client = self._get_client()
        target_model = model or settings.GEMINI_MODEL

        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=LLMContractExtraction,
            system_instruction=SYSTEM_PROMPT,
            temperature=0.0,
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        )

        async def _call_gemini() -> str:
            response = await asyncio.wait_for(
                client.aio.models.generate_content(
                    model=target_model,
                    contents=text,
                    config=config,
                ),
                timeout=settings.LLM_TIMEOUT_SECONDS,
            )
            if not response.text:
                raise LLMSchemaDecodeError("Gemini returned an empty response.")
            return response.text

        # Configure retry with exponential backoff and jitter
        retryer = AsyncRetrying(
            stop=stop_after_attempt(settings.LLM_MAX_RETRIES),
            wait=wait_exponential_jitter(
                initial=settings.LLM_RETRY_MIN_WAIT,
                max=settings.LLM_RETRY_MAX_WAIT,
            ),
            retry=retry_if_exception_type((genai_errors.APIError, asyncio.TimeoutError)),
            reraise=True,
        )

        try:
            async for attempt in retryer:
                with attempt:
                    raw_text = await _call_gemini()

            # Parse and validate returned JSON
            try:
                data = json.loads(raw_text)
                return LLMContractExtraction.model_validate(data)
            except (json.JSONDecodeError, ValidationError) as err:
                logger.error("Failed to parse Gemini response into schema: %s", err)
                raise LLMSchemaDecodeError(
                    message=f"Failed to parse LLM structured output: {str(err)}",
                    details={"raw_output": raw_text},
                ) from err

        except asyncio.TimeoutError as err:
            logger.error("Gemini API request timed out after retries.")
            raise LLMTimeoutError("Gemini request timed out after all retries.") from err

        except genai_errors.APIError as err:
            logger.error("Gemini API error: code=%s, message=%s", getattr(err, "code", None), err)
            status_code = getattr(err, "code", 500)
            if status_code in (401, 403):
                raise LLMAuthenticationError(f"Gemini API authentication failed: {str(err)}") from err
            elif status_code == 429:
                raise LLMRateLimitError(f"Gemini rate limit or quota exceeded: {str(err)}") from err
            else:
                raise LLMProviderError(f"Gemini API error ({status_code}): {str(err)}") from err

        except (LLMAuthenticationError, LLMRateLimitError, LLMTimeoutError, LLMSchemaDecodeError, LLMProviderError):
            raise
        except Exception as err:
            logger.exception("Unexpected error in Gemini extraction pipeline: %s", err)
            raise LLMProviderError(f"Unexpected error communicating with Gemini API: {str(err)}") from err
