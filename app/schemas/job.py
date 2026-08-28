from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.models.job import JobStatus
from app.schemas.contract import ContractResponse


class JobResponse(BaseModel):
    """Schema for returning asynchronous extraction job status and result."""
    id: str = Field(..., description="Unique UUID of the background job")
    status: JobStatus = Field(..., description="Current status of the job: PENDING, PROCESSING, COMPLETED, FAILED")
    provider: Optional[str] = Field(default=None, description="LLM provider used")
    model: Optional[str] = Field(default=None, description="Model used")
    contract_id: Optional[int] = Field(default=None, description="ID of the created contract upon successful extraction")
    contract: Optional[ContractResponse] = Field(default=None, description="Full contract details if completed")
    error_message: Optional[str] = Field(default=None, description="Error message if extraction or validation failed")
    error_code: Optional[str] = Field(default=None, description="Error classification code if failed")
    created_at: datetime = Field(..., description="Timestamp when the job was submitted")
    completed_at: Optional[datetime] = Field(default=None, description="Timestamp when the job finished")

    model_config = ConfigDict(from_attributes=True)


class JobListResponse(BaseModel):
    """Schema for listing asynchronous jobs."""
    total: int = Field(..., description="Total number of jobs")
    items: List[JobResponse] = Field(..., description="List of jobs")
