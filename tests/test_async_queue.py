import asyncio
from datetime import date
from unittest.mock import patch
import pytest
from httpx import AsyncClient

from app.schemas.extraction import LLMContractExtraction
from tests.conftest import MockLLMClient


@pytest.mark.asyncio
async def test_async_extraction_job_success_flow(client: AsyncClient) -> None:
    """Test full asynchronous extraction lifecycle from 202 Accepted to COMPLETED."""
    mock_result = LLMContractExtraction(
        lessor="Gulf Real Estate Co",
        lessee="Tech Horizon FZ-LLC",
        commencement_date=date(2025, 1, 1),
        expiration_date=date(2026, 12, 31),
        monthly_rent=25000.0,
        currency="AED",
        termination_notice_period=60,
    )
    mock_llm = MockLLMClient(response=mock_result)

    with patch("app.services.contract_service.get_llm_client", return_value=mock_llm):
        # 1. Enqueue async job
        response = await client.post(
            "/api/v1/extract/async",
            json={"text": "Standard commercial lease agreement between Gulf Real Estate and Tech Horizon."},
        )

        assert response.status_code == 202
        job_data = response.json()
        job_id = job_data["id"]
        assert job_id is not None
        assert job_data["status"] in ("PENDING", "PROCESSING", "COMPLETED")

        # 2. Poll until completed (with timeout safety)
        current_job = None
        for _ in range(30):
            status_res = await client.get(f"/api/v1/jobs/{job_id}")
            assert status_res.status_code == 200
            current_job = status_res.json()
            if current_job["status"] == "COMPLETED":
                break
            await asyncio.sleep(0.05)

        assert current_job is not None
        assert current_job["status"] == "COMPLETED"
        assert current_job["contract_id"] is not None
        assert current_job["contract"]["lessor"] == "Gulf Real Estate Co"
        assert current_job["contract"]["monthly_rent"] == 25000.0
        assert current_job["contract"]["contract_duration_days"] == 729


@pytest.mark.asyncio
async def test_async_extraction_job_failure_flow(client: AsyncClient) -> None:
    """Test that async jobs capture validation errors and mark status as FAILED."""
    # Invalid date range (expiration before commencement)
    invalid_result = LLMContractExtraction(
        lessor="Faulty Lessor",
        lessee="Faulty Lessee",
        commencement_date=date(2025, 6, 1),
        expiration_date=date(2024, 6, 1),
        monthly_rent=5000.0,
        currency="USD",
        termination_notice_period=30,
    )
    mock_llm = MockLLMClient(response=invalid_result)

    with patch("app.services.contract_service.get_llm_client", return_value=mock_llm):
        response = await client.post(
            "/api/v1/extract/async",
            json={"text": "Faulty lease with inverted commencement and expiration dates."},
        )

        assert response.status_code == 202
        job_id = response.json()["id"]

        # Poll until failed
        current_job = None
        for _ in range(30):
            status_res = await client.get(f"/api/v1/jobs/{job_id}")
            current_job = status_res.json()
            if current_job["status"] == "FAILED":
                break
            await asyncio.sleep(0.05)

        assert current_job is not None
        assert current_job["status"] == "FAILED"
        assert current_job["error_code"] == "BUSINESS_RULE_VIOLATION"
        assert "Invalid date range" in current_job["error_message"]


@pytest.mark.asyncio
async def test_list_jobs_endpoint(client: AsyncClient) -> None:
    """Test listing all submitted jobs."""
    response = await client.get("/api/v1/jobs")
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "items" in data
