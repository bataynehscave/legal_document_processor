from datetime import date
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.contract import Contract


@pytest.mark.asyncio
async def test_contract_search_and_filters(client: AsyncClient, db_session: AsyncSession) -> None:
    """Test searching by party names, filtering by currency and rent range."""
    c1 = Contract(
        lessor="Emaar Properties PJSC",
        lessee="Global Retail Solutions",
        commencement_date=date(2024, 1, 1),
        expiration_date=date(2025, 1, 1),
        monthly_rent=15000.0,
        currency="AED",
        termination_notice_period=60,
        contract_duration_days=366,
        raw_text="Contract 1",
    )
    c2 = Contract(
        lessor="Aldar Properties",
        lessee="Tech Innovators Inc",
        commencement_date=date(2024, 6, 1),
        expiration_date=date(2025, 6, 1),
        monthly_rent=8000.0,
        currency="USD",
        termination_notice_period=30,
        contract_duration_days=365,
        raw_text="Contract 2",
    )
    c3 = Contract(
        lessor="Dubai Silicon Oasis",
        lessee="Emaar Hospitality Group",
        commencement_date=date(2024, 3, 1),
        expiration_date=date(2026, 3, 1),
        monthly_rent=30000.0,
        currency="AED",
        termination_notice_period=90,
        contract_duration_days=730,
        raw_text="Contract 3",
    )
    db_session.add_all([c1, c2, c3])
    await db_session.commit()

    # 1. Search by name 'Emaar' (matches c1 lessor and c3 lessee)
    res_search = await client.get("/api/v1/contracts?search=Emaar")
    assert res_search.status_code == 200
    search_data = res_search.json()
    assert search_data["total"] == 2
    parties = [item["lessor"] for item in search_data["items"]] + [item["lessee"] for item in search_data["items"]]
    assert any("Emaar Properties" in p for p in parties)

    # 2. Filter by Currency 'USD'
    res_currency = await client.get("/api/v1/contracts?currency=USD")
    assert res_currency.status_code == 200
    usd_data = res_currency.json()
    assert usd_data["total"] == 1
    assert usd_data["items"][0]["lessor"] == "Aldar Properties"

    # 3. Filter by Rent Range (,000 to ,000)
    res_rent = await client.get("/api/v1/contracts?min_rent=10000&max_rent=20000")
    assert res_rent.status_code == 200
    rent_data = res_rent.json()
    assert rent_data["total"] == 1
    assert rent_data["items"][0]["monthly_rent"] == 15000.0


@pytest.mark.asyncio
async def test_contract_deletion(client: AsyncClient, db_session: AsyncSession) -> None:
    """Test deleting a contract by ID."""
    contract = Contract(
        lessor="Temporary Landlord",
        lessee="Temporary Tenant",
        commencement_date=date(2024, 1, 1),
        expiration_date=date(2024, 12, 31),
        monthly_rent=5000.0,
        currency="USD",
        termination_notice_period=30,
        contract_duration_days=365,
        raw_text="Temporary text",
    )
    db_session.add(contract)
    await db_session.commit()
    await db_session.refresh(contract)
    contract_id = contract.id

    # Delete contract
    delete_res = await client.delete(f"/api/v1/contracts/{contract_id}")
    assert delete_res.status_code == 204

    # Subsequent GET returns 404
    get_res = await client.get(f"/api/v1/contracts/{contract_id}")
    assert get_res.status_code == 404

    # Deleting nonexistent returns 404
    delete_res_404 = await client.delete(f"/api/v1/contracts/{contract_id}")
    assert delete_res_404.status_code == 404
