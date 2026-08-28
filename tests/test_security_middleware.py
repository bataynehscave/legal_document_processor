import pytest
from httpx import AsyncClient

from app.core.config import settings


@pytest.mark.asyncio
async def test_security_and_tracing_headers_present(client: AsyncClient) -> None:
    """Verify that every response carries security headers and request tracing ID."""
    response = await client.get("/health")
    assert response.status_code == 200

    headers = response.headers
    assert "X-Request-ID" in headers
    assert "X-Process-Time-Ms" in headers
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert headers["X-Frame-Options"] == "DENY"
    assert "max-age=31536000" in headers["Strict-Transport-Security"]


@pytest.mark.asyncio
async def test_payload_size_limit_guard_returns_413(client: AsyncClient) -> None:
    """Verify that payloads exceeding MAX_PAYLOAD_BYTES return HTTP 413."""
    # Send a payload that exceeds the max bytes
    large_text = "X" * (settings.MAX_PAYLOAD_BYTES + 500)
    response = await client.post(
        "/api/v1/extract",
        content=large_text,
        headers={"Content-Type": "application/json", "Content-Length": str(len(large_text))},
    )

    assert response.status_code == 413
    data = response.json()
    assert data["error_code"] == "PAYLOAD_TOO_LARGE"
    assert "Payload too large" in data["detail"]
