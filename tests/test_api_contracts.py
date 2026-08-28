from datetime import date
from unittest.mock import patch
import pytest
from httpx import AsyncClient

from app.schemas.extraction import LLMContractExtraction
from tests.conftest import MockLLMClient


@pytest.mark.asyncio
async def test_get_contracts_empty_initially(client: AsyncClient) -> None:
    """Test GET /api/v1/contracts returns empty list when no contracts exist."""
    response = await client.get("/api/v1/contracts")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["items"] == []


@pytest.mark.asyncio
async def test_get_contract_by_id_not_found_returns_404(client: AsyncClient) -> None:
    """Requirement 4.4: Fetch non-existent contract returns HTTP 404."""
    response = await client.get("/api/v1/contracts/9999")
    assert response.status_code == 404
    data = response.json()
    assert data["error_code"] == "CONTRACT_NOT_FOUND"
    assert "9999 not found" in data["detail"]


@pytest.mark.asyncio
async def test_contracts_list_and_pagination(client: AsyncClient) -> None:
    """Requirement 4.4: List all successfully processed contracts with pagination."""
    # Seed two contracts via extract endpoint
    mock_1 = LLMContractExtraction(
        lessor="First Landlord LLC",
        lessee="First Tenant Inc",
        commencement_date=date(2024, 1, 1),
        expiration_date=date(2025, 1, 1),
        monthly_rent=1000.00,
        currency="USD",
        termination_notice_period=30,
    )
    mock_2 = LLMContractExtraction(
        lessor="Second Landlord LLC",
        lessee="Second Tenant Inc",
        commencement_date=date(2024, 6, 1),
        expiration_date=date(2026, 6, 1),
        monthly_rent=2000.00,
        currency="AED",
        termination_notice_period=60,
    )

    with patch("app.services.contract_service.get_llm_client", return_value=MockLLMClient(response=mock_1)):
        res1 = await client.post("/api/v1/extract", json={"text": "First contract text here..."})
        assert res1.status_code == 201

    with patch("app.services.contract_service.get_llm_client", return_value=MockLLMClient(response=mock_2)):
        res2 = await client.post("/api/v1/extract", json={"text": "Second contract text here..."})
        assert res2.status_code == 201

    # List all
    list_res = await client.get("/api/v1/contracts")
    assert list_res.status_code == 200
    list_data = list_res.json()
    assert list_data["total"] == 2
    assert len(list_data["items"]) == 2

    # Pagination: limit=1
    page1 = await client.get("/api/v1/contracts?limit=1&skip=0")
    assert page1.status_code == 200
    p1_data = page1.json()
    assert p1_data["total"] == 2
    assert len(p1_data["items"]) == 1
    assert p1_data["items"][0]["lessor"] == "Second Landlord LLC"

    # Pagination: limit=1, skip=1
    page2 = await client.get("/api/v1/contracts?limit=1&skip=1")
    assert page2.status_code == 200
    p2_data = page2.json()
    assert p2_data["total"] == 2
    assert len(p2_data["items"]) == 1
    assert p2_data["items"][0]["lessor"] == "First Landlord LLC"

    # Fetch individual contracts by ID
    get_res_1 = await client.get("/api/v1/contracts/1")
    assert get_res_1.status_code == 200
    assert get_res_1.json()["lessor"] == "First Landlord LLC"

    get_res_2 = await client.get("/api/v1/contracts/2")
    assert get_res_2.status_code == 200
    assert get_res_2.json()["lessor"] == "Second Landlord LLC"
