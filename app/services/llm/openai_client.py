import asyncio
import logging
from typing import Optional
import openai
from openai import AsyncOpenAI
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


class OpenAIClient(BaseLLMClient):
    """Production-ready OpenAI LLM client using native AsyncOpenAI with Structured Outputs."""

    def __init__(self, api_key: Optional[str] = None) -> None:
        self.api_key = api_key or settings.OPENAI_API_KEY
        self._client: Optional[AsyncOpenAI] = None

    def _get_client(self) -> AsyncOpenAI:
        if not self.api_key:
            raise LLMAuthenticationError(
                "OpenAI API key is not configured. Please set OPENAI_API_KEY in your environment or .env file."
            )
        if self._client is None:
            self._client = AsyncOpenAI(api_key=self.api_key, timeout=settings.LLM_TIMEOUT_SECONDS)
        return self._client

    async def extract_contract_data(
        self,
        text: str,
        model: Optional[str] = None,
    ) -> LLMContractExtraction:
        client = self._get_client()
        target_model = model or settings.OPENAI_MODEL

        async def _call_openai() -> LLMContractExtraction:
            completion = await client.beta.chat.completions.parse(
                model=target_model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": text},
                ],
                response_format=LLMContractExtraction,
                temperature=0.0,
            )
            message = completion.choices[0].message
            if getattr(message, "refusal", None):
                raise LLMSchemaDecodeError(f"Model refused to extract contract data: {message.refusal}")
            if not message.parsed:
                raise LLMSchemaDecodeError("Model did not return parsed structured output.")
            return message.parsed

        # Configure retry with exponential backoff and jitter
        retryer = AsyncRetrying(
            stop=stop_after_attempt(settings.LLM_MAX_RETRIES),
            wait=wait_exponential_jitter(
                initial=settings.LLM_RETRY_MIN_WAIT,
                max=settings.LLM_RETRY_MAX_WAIT,
            ),
            retry=retry_if_exception_type((
                openai.RateLimitError,
                openai.APITimeoutError,
                openai.APIConnectionError,
                openai.InternalServerError,
                asyncio.TimeoutError,
            )),
            reraise=True,
        )

        try:
            async for attempt in retryer:
                with attempt:
                    result = await _call_openai()
            return result

        except openai.AuthenticationError as err:
            logger.error("OpenAI authentication error: %s", err)
            raise LLMAuthenticationError(f"OpenAI API authentication failed: {str(err)}") from err

        except openai.RateLimitError as err:
            logger.error("OpenAI rate limit error: %s", err)
            raise LLMRateLimitError(f"OpenAI rate limit exceeded: {str(err)}") from err

        except (openai.APITimeoutError, asyncio.TimeoutError) as err:
            logger.error("OpenAI request timeout after retries.")
            raise LLMTimeoutError("OpenAI request timed out after all retries.") from err

        except (openai.APIConnectionError, openai.InternalServerError, openai.APIError) as err:
            logger.error("OpenAI API error: %s", err)
            raise LLMProviderError(f"OpenAI upstream error: {str(err)}") from err

        except (LLMAuthenticationError, LLMRateLimitError, LLMTimeoutError, LLMSchemaDecodeError, LLMProviderError):
            raise
        except Exception as err:
            logger.exception("Unexpected error in OpenAI extraction pipeline: %s", err)
            raise LLMProviderError(f"Unexpected error communicating with OpenAI API: {str(err)}") from err
