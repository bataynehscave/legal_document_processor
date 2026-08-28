from datetime import date
from unittest.mock import patch
import pytest
from httpx import AsyncClient

from app.schemas.extraction import LLMContractExtraction
from tests.conftest import MockLLMClient


@pytest.mark.asyncio
async def test_expiration_before_commencement_date_returns_422(client: AsyncClient) -> None:
    """Requirement 4.2: If Expiration Date is before Commencement Date, flag as INVALID (HTTP 422)."""
    invalid_dates_extraction = LLMContractExtraction(
        lessor="Landlord Corp",
        lessee="Tenant Ltd",
        commencement_date=date(2025, 6, 1),
        expiration_date=date(2024, 6, 1),  # Invalid: 1 year prior to start
        monthly_rent=5000.00,
        currency="USD",
        termination_notice_period=30,
    )
    mock_client = MockLLMClient(response=invalid_dates_extraction)

    with patch("app.services.contract_service.get_llm_client", return_value=mock_client):
        response = await client.post(
            "/api/v1/extract",
            json={"text": "Lease agreement from June 2025 ending June 2024..."},
        )

    assert response.status_code == 422
    data = response.json()
    assert data["error_code"] == "BUSINESS_RULE_VIOLATION"
    assert "cannot be prior to commencement date" in data["detail"]
    assert data["details"]["field"] == "expiration_date"

    # Verify no invalid record was persisted in database
    list_res = await client.get("/api/v1/contracts")
    assert list_res.status_code == 200
    assert list_res.json()["total"] == 0


@pytest.mark.asyncio
async def test_negative_monthly_rent_returns_422(client: AsyncClient) -> None:
    """Requirement 4.2: If Monthly Rent is negative, flag as INVALID (HTTP 422)."""
    negative_rent_extraction = LLMContractExtraction(
        lessor="Landlord Corp",
        lessee="Tenant Ltd",
        commencement_date=date(2024, 1, 1),
        expiration_date=date(2025, 1, 1),
        monthly_rent=-1200.50,  # Invalid negative rent
        currency="USD",
        termination_notice_period=30,
    )
    mock_client = MockLLMClient(response=negative_rent_extraction)

    with patch("app.services.contract_service.get_llm_client", return_value=mock_client):
        response = await client.post(
            "/api/v1/extract",
            json={"text": "Lease agreement with negative rent clause..."},
        )

    assert response.status_code == 422
    data = response.json()
    assert data["error_code"] == "BUSINESS_RULE_VIOLATION"
    assert "cannot be negative" in data["detail"]
    assert data["details"]["field"] == "monthly_rent"

    # Verify no invalid record was persisted in database
    list_res = await client.get("/api/v1/contracts")
    assert list_res.json()["total"] == 0


@pytest.mark.asyncio
async def test_negative_notice_period_returns_422(client: AsyncClient) -> None:
    """Test business validation for negative notice period."""
    negative_notice_extraction = LLMContractExtraction(
        lessor="Landlord Corp",
        lessee="Tenant Ltd",
        commencement_date=date(2024, 1, 1),
        expiration_date=date(2025, 1, 1),
        monthly_rent=3000.00,
        currency="EUR",
        termination_notice_period=-15,  # Invalid negative days
    )
    mock_client = MockLLMClient(response=negative_notice_extraction)

    with patch("app.services.contract_service.get_llm_client", return_value=mock_client):
        response = await client.post(
            "/api/v1/extract",
            json={"text": "Lease agreement with negative notice period..."},
        )

    assert response.status_code == 422
    data = response.json()
    assert data["error_code"] == "BUSINESS_RULE_VIOLATION"
    assert "cannot be negative" in data["detail"]


@pytest.mark.asyncio
async def test_invalid_currency_code_returns_422(client: AsyncClient) -> None:
    """Test business validation for invalid currency code format."""
    invalid_currency_extraction = LLMContractExtraction(
        lessor="Landlord Corp",
        lessee="Tenant Ltd",
        commencement_date=date(2024, 1, 1),
        expiration_date=date(2025, 1, 1),
        monthly_rent=3000.00,
        currency="US_DOLLAR",  # Invalid > 3 letters
        termination_notice_period=30,
    )
    mock_client = MockLLMClient(response=invalid_currency_extraction)

    with patch("app.services.contract_service.get_llm_client", return_value=mock_client):
        response = await client.post(
            "/api/v1/extract",
            json={"text": "Lease agreement with invalid currency..."},
        )

    assert response.status_code == 422
    assert response.json()["error_code"] == "BUSINESS_RULE_VIOLATION"


@pytest.mark.asyncio
async def test_empty_contract_text_payload_returns_422(client: AsyncClient) -> None:
    """Test request body validation rejects empty or whitespace-only contract text."""
    response = await client.post(
        "/api/v1/extract",
        json={"text": "     "},
    )
    assert response.status_code == 422
    data = response.json()
    assert data["error_code"] == "REQUEST_VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_zero_rent_is_valid(client: AsyncClient) -> None:
    """Test zero rent (e.g. grace/rent-free period) is accepted and persisted."""
    zero_rent_extraction = LLMContractExtraction(
        lessor="Charity Landlord",
        lessee="Nonprofit Org",
        commencement_date=date(2024, 1, 1),
        expiration_date=date(2025, 1, 1),
        monthly_rent=0.0,
        currency="USD",
        termination_notice_period=30,
    )
    mock_client = MockLLMClient(response=zero_rent_extraction)

    with patch("app.services.contract_service.get_llm_client", return_value=mock_client):
        response = await client.post(
            "/api/v1/extract",
            json={"text": "Rent free commercial agreement for charity..."},
        )

    assert response.status_code == 201
    assert response.json()["monthly_rent"] == 0.0
