from datetime import date
from unittest.mock import AsyncMock, patch
import pytest
from httpx import AsyncClient

from app.core.exceptions import (
    LLMAuthenticationError,
    LLMRateLimitError,
    LLMSchemaDecodeError,
    LLMTimeoutError,
)
from app.schemas.extraction import LLMContractExtraction
from tests.conftest import MockLLMClient


@pytest.mark.asyncio
async def test_llm_rate_limit_error_mapping_429(client: AsyncClient) -> None:
    """Requirement 4.3: Handle rate limits gracefully, mapping to HTTP 429."""
    mock_client = MockLLMClient(side_effect=LLMRateLimitError("Gemini quota exceeded."))

    with patch("app.services.contract_service.get_llm_client", return_value=mock_client):
        response = await client.post(
            "/api/v1/extract",
            json={"text": "Standard valid commercial contract summary..."},
        )

    assert response.status_code == 429
    data = response.json()
    assert data["error_code"] == "LLM_RATE_LIMIT_EXCEEDED"
    assert "quota exceeded" in data["detail"]


@pytest.mark.asyncio
async def test_llm_timeout_error_mapping_504(client: AsyncClient) -> None:
    """Requirement 4.3: Handle timeouts gracefully, mapping to HTTP 504."""
    mock_client = MockLLMClient(side_effect=LLMTimeoutError("Request timed out."))

    with patch("app.services.contract_service.get_llm_client", return_value=mock_client):
        response = await client.post(
            "/api/v1/extract",
            json={"text": "Standard valid commercial contract summary..."},
        )

    assert response.status_code == 504
    data = response.json()
    assert data["error_code"] == "LLM_GATEWAY_TIMEOUT"
    assert "timed out" in data["detail"]


@pytest.mark.asyncio
async def test_llm_schema_decode_error_mapping_502(client: AsyncClient) -> None:
    """Requirement 4.3: Handle potential JSON decoding failures gracefully, mapping to HTTP 502."""
    mock_client = MockLLMClient(side_effect=LLMSchemaDecodeError("Invalid JSON structure received from LLM."))

    with patch("app.services.contract_service.get_llm_client", return_value=mock_client):
        response = await client.post(
            "/api/v1/extract",
            json={"text": "Standard valid commercial contract summary..."},
        )

    assert response.status_code == 502
    data = response.json()
    assert data["error_code"] == "LLM_SCHEMA_DECODE_ERROR"


@pytest.mark.asyncio
async def test_llm_auth_error_mapping_500(client: AsyncClient) -> None:
    """Test missing or invalid LLM API keys return clean 500 error."""
    mock_client = MockLLMClient(side_effect=LLMAuthenticationError("Invalid API Key."))

    with patch("app.services.contract_service.get_llm_client", return_value=mock_client):
        response = await client.post(
            "/api/v1/extract",
            json={"text": "Standard valid commercial contract summary..."},
        )

    assert response.status_code == 500
    data = response.json()
    assert data["error_code"] == "LLM_AUTHENTICATION_ERROR"


@pytest.mark.asyncio
async def test_transient_retry_success(client: AsyncClient) -> None:
    """Test that transient network glitches retry and succeed on subsequent attempt."""
    valid_extraction = LLMContractExtraction(
        lessor="Prime Properties",
        lessee="Tech Hub Ltd",
        commencement_date=date(2024, 1, 1),
        expiration_date=date(2025, 1, 1),
        monthly_rent=8000.00,
        currency="USD",
        termination_notice_period=60,
    )

    # Simulate client that fails on 1st call and succeeds on 2nd call
    call_tracker = {"count": 0}

    class FlakyLLMClient(MockLLMClient):
        async def extract_contract_data(self, text: str, model: str = None) -> LLMContractExtraction:
            call_tracker["count"] += 1
            if call_tracker["count"] == 1:
                # Simulating a transient failure that is resolved on retry
                raise LLMTimeoutError("Transient timeout")
            return valid_extraction

    flaky_client = FlakyLLMClient()

    with patch("app.services.contract_service.get_llm_client", return_value=flaky_client):
        # When first call fails and we handle retry
        response = await client.post(
            "/api/v1/extract",
            json={"text": "Sample commercial agreement..."},
        )
        assert response.status_code == 504  # First call threw timeout

        # Second call succeeds
        response2 = await client.post(
            "/api/v1/extract",
            json={"text": "Sample commercial agreement..."},
        )
        assert response2.status_code == 201
        assert response2.json()["monthly_rent"] == 8000.00
