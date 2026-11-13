from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field


class HealthResponse(BaseModel):
    status: str
    environment: str
    database_connected: bool
    timestamp: datetime
    version: str = "v1"


class RFPQuestionBrief(BaseModel):
    QuestionId: int
    RfpId: int
    QuestionText: str
    Category: Optional[str] = None
    Sequence: int
    Status: str
    CreatedDate: datetime

    model_config = ConfigDict(from_attributes=True)


class RFPBase(BaseModel):
    Title: str = Field(..., max_length=255, description="Title of the RFP")
    CustomerName: str = Field(..., max_length=255, description="Client or Customer organization name")
    Description: Optional[str] = None
    DueDate: Optional[datetime] = None
    Status: str = Field(default="Draft", max_length=50)


class RFPCreate(RFPBase):
    CreatedBy: Optional[int] = None


class RFPResponseSchema(RFPBase):
    RfpId: int
    CreatedBy: Optional[int] = None
    CreatedDate: datetime
    UpdatedDate: datetime

    model_config = ConfigDict(from_attributes=True)


class RFPDetailResponse(RFPResponseSchema):
    questions: List[RFPQuestionBrief] = []

    model_config = ConfigDict(from_attributes=True)


class ErrorDetail(BaseModel):
    message: str
    details: Optional[dict] = None
