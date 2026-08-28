from datetime import date
from typing import Literal, Optional
from pydantic import BaseModel, Field, field_validator


class LLMContractExtraction(BaseModel):
    """Pydantic v2 schema enforced during LLM Structured Outputs extraction."""
    lessor: str = Field(
        ...,
        description="Full legal name of the Landlord (Lessor)",
    )
    lessee: str = Field(
        ...,
        description="Full legal name of the Tenant (Lessee)",
    )
    commencement_date: date = Field(
        ...,
        description="Lease start date in ISO 8601 format (YYYY-MM-DD)",
    )
    expiration_date: date = Field(
        ...,
        description="Lease end/expiration date in ISO 8601 format (YYYY-MM-DD)",
    )
    monthly_rent: float = Field(
        ...,
        description="Agreed monthly rent amount as a float/decimal",
    )
    currency: str = Field(
        ...,
        description="3-letter ISO 4217 currency code (e.g., USD, AED, EUR, GBP)",
    )
    termination_notice_period: int = Field(
        ...,
        description="Early termination notice period in integer number of days",
    )


class ExtractRequest(BaseModel):
    """Client request schema for contract extraction."""
    text: str = Field(
        ...,
        min_length=10,
        max_length=50000,
        description="Raw unstructured text summary or full text of the legal contract/lease.",
    )
    provider: Optional[Literal["gemini", "openai"]] = Field(
        default=None,
        description="Optional LLM provider override ('gemini' or 'openai'). Defaults to server configuration.",
    )
    model: Optional[str] = Field(
        default=None,
        description="Optional LLM model override (e.g., 'gemini-2.5-flash', 'gpt-4o-mini', 'gpt-4o').",
    )

    @field_validator("text")
    @classmethod
    def validate_non_empty_text(cls, v: str) -> str:
        clean = v.strip()
        if not clean or len(clean) < 10:
            raise ValueError("Contract text must contain at least 10 non-whitespace characters.")
        return clean
