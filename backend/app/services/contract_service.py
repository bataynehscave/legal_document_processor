import logging
from typing import List, Optional, Tuple
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    BusinessRuleValidationError,
    ContractNotFoundError,
)
from app.models.contract import Contract
from app.schemas.extraction import LLMContractExtraction
from app.services.llm.base import BaseLLMClient
from app.services.llm.factory import get_llm_client

logger = logging.getLogger(__name__)


class ContractService:
    """Service handling legal contract processing, business logic validation, search, and database operations."""

    @staticmethod
    def validate_and_compute_duration(extraction: LLMContractExtraction) -> int:
        """Perform deterministic business logic validation and calculate contract duration in days.

        Raises:
            BusinessRuleValidationError: If any business rule is violated (mapped to HTTP 422).
        """
        # Rule 1: Expiration date must not precede Commencement date
        if extraction.expiration_date < extraction.commencement_date:
            raise BusinessRuleValidationError(
                message=(
                    f"Invalid date range: Expiration date ({extraction.expiration_date}) "
                    f"cannot be prior to commencement date ({extraction.commencement_date})."
                ),
                details={
                    "field": "expiration_date",
                    "commencement_date": str(extraction.commencement_date),
                    "expiration_date": str(extraction.expiration_date),
                },
            )

        # Rule 2: Monthly rent cannot be negative
        if extraction.monthly_rent < 0:
            raise BusinessRuleValidationError(
                message=f"Invalid financial value: Monthly rent ({extraction.monthly_rent}) cannot be negative.",
                details={"field": "monthly_rent", "monthly_rent": extraction.monthly_rent},
            )

        # Rule 3: Termination notice period cannot be negative
        if extraction.termination_notice_period < 0:
            raise BusinessRuleValidationError(
                message=(
                    f"Invalid notice period: Termination notice period "
                    f"({extraction.termination_notice_period}) cannot be negative."
                ),
                details={
                    "field": "termination_notice_period",
                    "termination_notice_period": extraction.termination_notice_period,
                },
            )

        # Rule 4: Currency code must be a 3-letter ISO code
        currency_clean = extraction.currency.strip().upper()
        if len(currency_clean) != 3 or not currency_clean.isalpha():
            raise BusinessRuleValidationError(
                message=f"Invalid currency: '{extraction.currency}' must be a valid 3-letter ISO 4217 code.",
                details={"field": "currency", "currency": extraction.currency},
            )

        # Rule 5: Parties must not be empty
        if not extraction.lessor.strip():
            raise BusinessRuleValidationError(
                message="Lessor name cannot be empty.",
                details={"field": "lessor"},
            )
        if not extraction.lessee.strip():
            raise BusinessRuleValidationError(
                message="Lessee name cannot be empty.",
                details={"field": "lessee"},
            )

        # Calculate contract duration using standard Python datetime math
        duration_days = (extraction.expiration_date - extraction.commencement_date).days
        return duration_days

    @classmethod
    async def process_and_store_contract(
        cls,
        db: AsyncSession,
        raw_text: str,
        llm_client: Optional[BaseLLMClient] = None,
    ) -> Contract:
        """Run the extraction pipeline, perform deterministic validation, and persist valid contract."""
        client = llm_client or get_llm_client()
        logger.info("Triggering LLM extraction via Gemini")

        # Step 1: LLM Structured Output extraction
        extraction: LLMContractExtraction = await client.extract_contract_data(text=raw_text)

        # Step 2: Deterministic business calculations & validation
        duration_days = cls.validate_and_compute_duration(extraction)

        # Step 3: Persist only successfully validated contracts to SQLite
        contract = Contract(
            lessor=extraction.lessor.strip(),
            lessee=extraction.lessee.strip(),
            commencement_date=extraction.commencement_date,
            expiration_date=extraction.expiration_date,
            monthly_rent=float(extraction.monthly_rent),
            currency=extraction.currency.strip().upper(),
            termination_notice_period=int(extraction.termination_notice_period),
            contract_duration_days=duration_days,
            raw_text=raw_text,
        )

        db.add(contract)
        await db.commit()
        await db.refresh(contract)
        logger.info("Successfully persisted contract ID=%d", contract.id)
        return contract

    @staticmethod
    async def get_contract_by_id(db: AsyncSession, contract_id: int) -> Contract:
        """Fetch a single contract by ID, or raise ContractNotFoundError (HTTP 404)."""
        stmt = select(Contract).where(Contract.id == contract_id)
        result = await db.execute(stmt)
        contract = result.scalar_one_or_none()
        if not contract:
            raise ContractNotFoundError(contract_id=contract_id)
        return contract

    @staticmethod
    async def delete_contract(db: AsyncSession, contract_id: int) -> None:
        """Delete a contract by ID, or raise ContractNotFoundError (HTTP 404)."""
        stmt = select(Contract).where(Contract.id == contract_id)
        result = await db.execute(stmt)
        contract = result.scalar_one_or_none()
        if not contract:
            raise ContractNotFoundError(contract_id=contract_id)
        await db.delete(contract)
        await db.commit()
        logger.info("Deleted contract ID=%d", contract_id)

    @staticmethod
    async def list_contracts(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
        currency: Optional[str] = None,
        min_rent: Optional[float] = None,
        max_rent: Optional[float] = None,
    ) -> Tuple[List[Contract], int]:
        """Fetch filtered and paginated list of contracts ordered by creation date descending."""
        filters = []
        if search:
            search_pattern = f"%{search.strip()}%"
            filters.append(
                or_(
                    Contract.lessor.ilike(search_pattern),
                    Contract.lessee.ilike(search_pattern),
                )
            )
        if currency:
            filters.append(Contract.currency == currency.strip().upper())
        if min_rent is not None:
            filters.append(Contract.monthly_rent >= min_rent)
        if max_rent is not None:
            filters.append(Contract.monthly_rent <= max_rent)

        # Total count query
        count_stmt = select(func.count()).select_from(Contract)
        if filters:
            count_stmt = count_stmt.where(*filters)
        total = (await db.execute(count_stmt)).scalar() or 0

        # Items query
        items_stmt = select(Contract).order_by(Contract.created_at.desc())
        if filters:
            items_stmt = items_stmt.where(*filters)
        items_stmt = items_stmt.offset(skip).limit(limit)

        result = await db.execute(items_stmt)
        items = list(result.scalars().all())
        return items, total
