from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.rfp import (
    RFPQuestionBrief,
    QuestionUpdate,
    QuestionAssignRequest,
    ErrorDetail,
)
from app.services.rfp_service import RFPService

router = APIRouter()


@router.get(
    "/{question_id}",
    response_model=RFPQuestionBrief,
    responses={
        status.HTTP_404_NOT_FOUND: {"model": ErrorDetail, "description": "Question not found"}
    },
    summary="Get Question by ID",
    description="Retrieves a single question and its SME assignment details.",
)
def get_question_by_id(
    question_id: int,
    db: Session = Depends(get_db),
):
    service = RFPService(db)
    return service.get_question_by_id(question_id)


@router.put(
    "/{question_id}",
    response_model=RFPQuestionBrief,
    responses={
        status.HTTP_404_NOT_FOUND: {"model": ErrorDetail, "description": "Question not found"}
    },
    summary="Update Question",
    description="Updates text, category, sequence, status, or SME assignment of a question.",
)
def update_question(
    question_id: int,
    question_in: QuestionUpdate,
    db: Session = Depends(get_db),
):
    service = RFPService(db)
    return service.update_question(question_id, question_in)


@router.delete(
    "/{question_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        status.HTTP_404_NOT_FOUND: {"model": ErrorDetail, "description": "Question not found"}
    },
    summary="Delete Question",
    description="Deletes a question by its unique ID.",
)
def delete_question(
    question_id: int,
    db: Session = Depends(get_db),
):
    service = RFPService(db)
    service.delete_question(question_id)
    return None


@router.patch(
    "/{question_id}/assign",
    response_model=RFPQuestionBrief,
    responses={
        status.HTTP_404_NOT_FOUND: {"model": ErrorDetail, "description": "Question or User not found"}
    },
    summary="Assign Question to SME",
    description="Assigns or unassigns a Subject Matter Expert (SME) to a question.",
)
def assign_question_sme(
    question_id: int,
    assign_in: QuestionAssignRequest,
    db: Session = Depends(get_db),
):
    service = RFPService(db)
    return service.assign_question(question_id, assign_in.AssignedTo)
