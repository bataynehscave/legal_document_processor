from typing import Optional
from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.contract import (
    ContractListResponse,
    ContractResponse,
    ErrorResponse,
)
from app.services.contract_service import ContractService

router = APIRouter()


@router.get(
    "",
    response_model=ContractListResponse,
    status_code=status.HTTP_200_OK,
    summary="List stored contracts",
    description="Retrieve paginated list of successfully processed contracts with optional search, currency filter, and rent range filters.",
    responses={
        200: {"model": ContractListResponse, "description": "Contracts retrieved successfully."},
    },
)
async def list_contracts(
    skip: int = Query(default=0, ge=0, description="Number of records to skip for pagination"),
    limit: int = Query(default=10, ge=1, le=100, description="Maximum number of records to return"),
    search: Optional[str] = Query(default=None, description="Search keyword in lessor or lessee party names"),
    currency: Optional[str] = Query(default=None, description="Filter by 3-letter ISO currency code"),
    min_rent: Optional[float] = Query(default=None, ge=0, description="Filter by minimum monthly rent"),
    max_rent: Optional[float] = Query(default=None, ge=0, description="Filter by maximum monthly rent"),
    db: AsyncSession = Depends(get_db),
) -> ContractListResponse:
    items, total = await ContractService.list_contracts(
        db=db,
        skip=skip,
        limit=limit,
        search=search,
        currency=currency,
        min_rent=min_rent,
        max_rent=max_rent,
    )
    return ContractListResponse(
        total=total,
        items=[ContractResponse.model_validate(c) for c in items],
    )


@router.get(
    "/{id}",
    response_model=ContractResponse,
    status_code=status.HTTP_200_OK,
    summary="Get contract by ID",
    description="Retrieve a single successfully processed contract by its primary key ID.",
    responses={
        200: {"model": ContractResponse, "description": "Contract retrieved successfully."},
        404: {"model": ErrorResponse, "description": "Contract ID not found."},
    },
)
async def get_contract_by_id(
    contract_id: int = Path(..., alias="id", ge=1, description="Unique primary key ID of the contract"),
    db: AsyncSession = Depends(get_db),
) -> ContractResponse:
    contract = await ContractService.get_contract_by_id(db=db, contract_id=contract_id)
    return ContractResponse.model_validate(contract)


@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete contract by ID",
    description="Delete a single contract by its primary key ID.",
    responses={
        204: {"description": "Contract successfully deleted."},
        404: {"model": ErrorResponse, "description": "Contract ID not found."},
    },
)
async def delete_contract_by_id(
    contract_id: int = Path(..., alias="id", ge=1, description="Unique primary key ID of the contract to delete"),
    db: AsyncSession = Depends(get_db),
) -> None:
    await ContractService.delete_contract(db=db, contract_id=contract_id)
