from datetime import date
from unittest.mock import patch
import pytest
from httpx import AsyncClient

from app.core.rate_limiter import InMemorySlidingWindowRateLimiter, rate_limiter
from app.main import app
from app.schemas.extraction import LLMContractExtraction
from tests.conftest import MockLLMClient


@pytest.mark.asyncio
async def test_rate_limiter_exceeded_returns_429(client: AsyncClient) -> None:
    """Test that exceeding the rate limit triggers HTTP 429 with Retry-After header."""
    mock_result = LLMContractExtraction(
        lessor="Apex Holdings LLC",
        lessee="Vertex Tech Solutions Corp",
        commencement_date=date(2024, 6, 1),
        expiration_date=date(2026, 5, 31),
        monthly_rent=12500.0,
        currency="AED",
        termination_notice_period=90,
    )
    mock_llm = MockLLMClient(response=mock_result)

    # Use dependency override with tight limit of 2 requests per minute
    custom_limiter = InMemorySlidingWindowRateLimiter(requests_per_minute=2)
    app.dependency_overrides[rate_limiter] = custom_limiter

    try:
        with patch("app.services.contract_service.get_llm_client", return_value=mock_llm):
            payload = {"text": "MEMORANDUM OF LEASE agreement between Apex and Vertex."}

            # Request 1: OK
            res1 = await client.post("/api/v1/extract", json=payload)
            assert res1.status_code == 201

            # Request 2: OK
            res2 = await client.post("/api/v1/extract", json=payload)
            assert res2.status_code == 201

            # Request 3: Rate Limited (429)
            res3 = await client.post("/api/v1/extract", json=payload)
            assert res3.status_code == 429
            assert "Rate limit exceeded" in res3.json()["detail"]
            assert "Retry-After" in res3.headers
            assert res3.headers["X-RateLimit-Limit"] == "2"
            assert res3.headers["X-RateLimit-Remaining"] == "0"
    finally:
        app.dependency_overrides.pop(rate_limiter, None)
