from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field


class HealthResponse(BaseModel):
    status: str
    environment: str
    database_connected: bool
    timestamp: datetime
    version: str = "v1"


# User Schemas
class ApplicationUserResponse(BaseModel):
    UserId: int
    DisplayName: str
    Email: str
    Role: str

    model_config = ConfigDict(from_attributes=True)


class ApplicationUserCreate(BaseModel):
    DisplayName: str = Field(..., min_length=1, max_length=100)
    Email: str = Field(..., max_length=255)
    Role: str = Field(default="Contributor", max_length=50)


# Question Schemas
class QuestionBase(BaseModel):
    QuestionText: str = Field(..., min_length=3, description="The content of the RFP question")
    Category: Optional[str] = Field(default=None, max_length=100)
    Sequence: Optional[int] = Field(default=None, ge=1)
    Status: str = Field(default="Pending", max_length=50)
    AssignedTo: Optional[int] = Field(default=None, description="UserId of SME assigned")


class QuestionCreate(QuestionBase):
    pass


class QuestionUpdate(BaseModel):
    QuestionText: Optional[str] = None
    Category: Optional[str] = None
    Sequence: Optional[int] = None
    Status: Optional[str] = None
    AssignedTo: Optional[int] = None


class QuestionAssignRequest(BaseModel):
    AssignedTo: Optional[int] = Field(..., description="UserId of the Subject Matter Expert (SME)")


class RFPQuestionBrief(BaseModel):
    QuestionId: int
    RfpId: int
    QuestionText: str
    Category: Optional[str] = None
    Sequence: int
    Status: str
    AssignedTo: Optional[int] = None
    assigned_user: Optional[ApplicationUserResponse] = None
    CreatedDate: datetime

    model_config = ConfigDict(from_attributes=True)


# RFP Schemas
class RFPBase(BaseModel):
    Title: str = Field(..., min_length=1, max_length=255, description="Title of the RFP")
    CustomerName: str = Field(..., min_length=1, max_length=255, description="Client or Customer organization name")
    Description: Optional[str] = None
    DueDate: Optional[datetime] = None
    Status: str = Field(default="Draft", max_length=50)


class RFPCreate(RFPBase):
    CreatedBy: Optional[int] = None


class RFPUpdate(BaseModel):
    Title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    CustomerName: Optional[str] = Field(default=None, min_length=1, max_length=255)
    Description: Optional[str] = None
    DueDate: Optional[datetime] = None
    Status: Optional[str] = Field(default=None, max_length=50)


class RFPResponseSchema(RFPBase):
    RfpId: int
    CreatedBy: Optional[int] = None
    CreatedDate: datetime
    UpdatedDate: datetime

    model_config = ConfigDict(from_attributes=True)


class RFPDetailResponse(RFPResponseSchema):
    questions: List[RFPQuestionBrief] = []

    model_config = ConfigDict(from_attributes=True)


# Document Ingestion Schema
class DocumentIngestionResponse(BaseModel):
    filename: str
    rfp_id: int
    questions_extracted: int
    questions: List[RFPQuestionBrief]


class ErrorDetail(BaseModel):
    message: str
    details: Optional[dict] = None
