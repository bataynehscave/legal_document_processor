from datetime import date, datetime
from typing import Any, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ContractResponse(BaseModel):
    """Schema for returning successfully processed and persisted contract details."""
    id: int = Field(..., description="Unique database identifier for the contract")
    lessor: str = Field(..., description="Full legal name of the Landlord (Lessor)")
    lessee: str = Field(..., description="Full legal name of the Tenant (Lessee)")
    commencement_date: date = Field(..., description="Lease start date (YYYY-MM-DD)")
    expiration_date: date = Field(..., description="Lease end date (YYYY-MM-DD)")
    monthly_rent: float = Field(..., description="Monthly rent amount")
    currency: str = Field(..., description="3-letter ISO 4217 currency code")
    termination_notice_period: int = Field(..., description="Termination notice period in days")
    contract_duration_days: int = Field(..., description="Calculated contract duration in days")
    created_at: datetime = Field(..., description="Timestamp of contract creation")

    model_config = ConfigDict(from_attributes=True)


class ContractListResponse(BaseModel):
    """Schema for listing multiple contracts with pagination metadata."""
    total: int = Field(..., description="Total count of contracts matching the query")
    items: List[ContractResponse] = Field(..., description="List of contract records")


class ErrorResponse(BaseModel):
    """Standardized error response schema."""
    detail: str = Field(..., description="Human-readable error explanation")
    error_code: str = Field(..., description="Domain error classification code")
    details: Optional[Any] = Field(default=None, description="Optional granular diagnostics or field errors")
