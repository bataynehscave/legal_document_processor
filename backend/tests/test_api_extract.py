from datetime import date
import pytest
from unittest.mock import patch
from httpx import AsyncClient

from app.schemas.extraction import LLMContractExtraction
from tests.conftest import MockLLMClient

MOCK_LEASE_TEXT = (
    "MEMORANDUM OF LEASE\n"
    "This agreement is entered into this 12th day of May, 2024, by and between Apex Holdings LLC "
    "(hereafter the Landlord) and Vertex Tech Solutions Corp (hereafter the Tenant). The property "
    "located at Suite 404, Dubai Sports City, is leased for a term starting on June 1st, 2024, and "
    "ending exactly two years later on May 31st, 2026. The agreed monthly consideration is 12500.00 "
    "AED, payable on the first of each month. Either party may terminate this agreement early by "
    "providing at least 90 days written notice to the other party."
)


@pytest.mark.asyncio
async def test_extract_valid_contract_section_5_sample(client: AsyncClient) -> None:
    """Test full extraction and persistence of Section 5 sample lease agreement."""
    mock_extracted = LLMContractExtraction(
        lessor="Apex Holdings LLC",
        lessee="Vertex Tech Solutions Corp",
        commencement_date=date(2024, 6, 1),
        expiration_date=date(2026, 5, 31),
        monthly_rent=12500.00,
        currency="AED",
        termination_notice_period=90,
    )

    mock_client = MockLLMClient(response=mock_extracted)

    with patch("app.services.contract_service.get_llm_client", return_value=mock_client):
        response = await client.post(
            "/api/v1/extract",
            json={"text": MOCK_LEASE_TEXT},
        )

    assert response.status_code == 201
    data = response.json()

    assert data["id"] == 1
    assert data["lessor"] == "Apex Holdings LLC"
    assert data["lessee"] == "Vertex Tech Solutions Corp"
    assert data["commencement_date"] == "2024-06-01"
    assert data["expiration_date"] == "2026-05-31"
    assert data["monthly_rent"] == 12500.00
    assert data["currency"] == "AED"
    assert data["termination_notice_period"] == 90
    # 2024 is leap year: June 1, 2024 to May 31, 2026 = 729 days
    assert data["contract_duration_days"] == 729
    assert "created_at" in data

    # Verify the contract can now be fetched via GET /api/v1/contracts/1
    get_res = await client.get("/api/v1/contracts/1")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == 1
    assert get_res.json()["lessor"] == "Apex Holdings LLC"



