import os
import pytest
from httpx import AsyncClient

from app.core.config import settings
from tests.test_api_extract import MOCK_LEASE_TEXT


@pytest.mark.asyncio
async def test_live_gemini_extraction(client: AsyncClient) -> None:
    """Live integration test against Google Gemini API (runs when GEMINI_API_KEY is configured)."""
    if not settings.GEMINI_API_KEY or settings.GEMINI_API_KEY.startswith("your_"):
        pytest.skip("GEMINI_API_KEY is not set. Skipping live Gemini API test.")

    response = await client.post(
        "/api/v1/extract",
        json={
            "text": MOCK_LEASE_TEXT,
            "provider": "gemini",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert "Apex Holdings" in data["lessor"]
    assert "Vertex Tech" in data["lessee"]
    assert data["commencement_date"] == "2024-06-01"
    assert data["expiration_date"] == "2026-05-31"
    assert data["monthly_rent"] == 12500.00
    assert data["currency"] == "AED"
    assert data["termination_notice_period"] == 90
    assert data["contract_duration_days"] == 729


@pytest.mark.asyncio
async def test_live_openai_extraction(client: AsyncClient) -> None:
    """Live integration test against OpenAI API (runs when OPENAI_API_KEY is configured)."""
    if not settings.OPENAI_API_KEY or settings.OPENAI_API_KEY.startswith("your_"):
        pytest.skip("OPENAI_API_KEY is not set. Skipping live OpenAI API test.")

    response = await client.post(
        "/api/v1/extract",
        json={
            "text": MOCK_LEASE_TEXT,
            "provider": "openai",
            "model": "gpt-4o-mini",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert "Apex Holdings" in data["lessor"]
    assert "Vertex Tech" in data["lessee"]
    assert data["commencement_date"] == "2024-06-01"
    assert data["expiration_date"] == "2026-05-31"
    assert data["monthly_rent"] == 12500.00
    assert data["currency"] == "AED"
    assert data["termination_notice_period"] == 90
    assert data["contract_duration_days"] == 729
