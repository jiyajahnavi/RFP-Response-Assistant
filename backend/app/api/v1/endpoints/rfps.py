from typing import List
from fastapi import APIRouter, Depends, Query, status, UploadFile, File
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.rfp import (
    RFPResponseSchema,
    RFPDetailResponse,
    RFPCreate,
    RFPUpdate,
    RFPQuestionBrief,
    QuestionCreate,
    DocumentIngestionResponse,
    ErrorDetail,
)
from app.services.rfp_service import RFPService

router = APIRouter()


@router.get(
    "",
    response_model=List[RFPResponseSchema],
    summary="List RFPs",
    description="Retrieves a list of RFPs from the database with pagination.",
)
def list_rfps(
    skip: int = Query(0, ge=0, description="Offset items"),
    limit: int = Query(20, ge=1, le=100, description="Page limit"),
    db: Session = Depends(get_db),
):
    service = RFPService(db)
    return service.list_rfps(skip=skip, limit=limit)


@router.post(
    "",
    response_model=RFPResponseSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create RFP",
    description="Creates a new RFP record.",
)
def create_rfp(
    rfp_in: RFPCreate,
    db: Session = Depends(get_db),
):
    service = RFPService(db)
    return service.create_rfp(rfp_in)


@router.get(
    "/{rfp_id}",
    response_model=RFPDetailResponse,
    responses={
        status.HTTP_404_NOT_FOUND: {"model": ErrorDetail, "description": "RFP not found"}
    },
    summary="Get RFP by ID",
    description="Retrieves an RFP along with its associated questions by its unique ID.",
)
def get_rfp_by_id(
    rfp_id: int,
    db: Session = Depends(get_db),
):
    service = RFPService(db)
    return service.get_rfp_by_id(rfp_id)


@router.put(
    "/{rfp_id}",
    response_model=RFPResponseSchema,
    responses={
        status.HTTP_404_NOT_FOUND: {"model": ErrorDetail, "description": "RFP not found"}
    },
    summary="Update RFP",
    description="Updates existing RFP details.",
)
def update_rfp(
    rfp_id: int,
    rfp_in: RFPUpdate,
    db: Session = Depends(get_db),
):
    service = RFPService(db)
    return service.update_rfp(rfp_id, rfp_in)


@router.delete(
    "/{rfp_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        status.HTTP_404_NOT_FOUND: {"model": ErrorDetail, "description": "RFP not found"}
    },
    summary="Delete RFP",
    description="Deletes an RFP and cascades delete to associated questions.",
)
def delete_rfp(
    rfp_id: int,
    db: Session = Depends(get_db),
):
    service = RFPService(db)
    service.delete_rfp(rfp_id)
    return None


@router.get(
    "/{rfp_id}/questions",
    response_model=List[RFPQuestionBrief],
    responses={
        status.HTTP_404_NOT_FOUND: {"model": ErrorDetail, "description": "RFP not found"}
    },
    summary="List Questions for an RFP",
    description="Lists all questions for a given RFP in sequence.",
)
def list_questions(
    rfp_id: int,
    db: Session = Depends(get_db),
):
    service = RFPService(db)
    return service.list_questions(rfp_id)


@router.post(
    "/{rfp_id}/questions",
    response_model=RFPQuestionBrief,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_404_NOT_FOUND: {"model": ErrorDetail, "description": "RFP or User not found"}
    },
    summary="Add Question to RFP",
    description="Adds a new question to the specified RFP with automatic sequence and category detection if omitted.",
)
def create_question(
    rfp_id: int,
    question_in: QuestionCreate,
    db: Session = Depends(get_db),
):
    service = RFPService(db)
    return service.create_question(rfp_id, question_in)


@router.post(
    "/{rfp_id}/ingest",
    response_model=DocumentIngestionResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_404_NOT_FOUND: {"model": ErrorDetail, "description": "RFP not found"},
        status.HTTP_400_BAD_REQUEST: {"model": ErrorDetail, "description": "Invalid file or parsing error"}
    },
    summary="Ingest RFP Questionnaire Document",
    description="Uploads and extracts questions from PDF, DOCX, or XLSX questionnaire documents with automatic sequence numbering and category classification.",
)
async def ingest_rfp_document(
    rfp_id: int,
    file: UploadFile = File(..., description="PDF, DOCX, or XLSX questionnaire file"),
    db: Session = Depends(get_db),
):
    contents = await file.read()
    service = RFPService(db)
    created_questions = service.ingest_document(rfp_id, file.filename or "unknown", contents)
    return DocumentIngestionResponse(
        filename=file.filename or "unknown",
        rfp_id=rfp_id,
        questions_extracted=len(created_questions),
        questions=[RFPQuestionBrief.model_validate(q) for q in created_questions],
    )
