from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core.database import get_db
from app.models.entities import RFPQuestion, RFPResponse, ResponseVersion
from app.schemas.rfp import (
    RFPResponseDetail,
    ResponseCreateRequest,
    ResponseUpdateRequest,
    ResponseStatusUpdateRequest,
    ResponseVersionResponse,
    AIGenerateDraftRequest,
    AIGenerateDraftResponse,
    PromoteToLibraryRequest,
    ResponseLibraryItem,
    ErrorDetail,
)
from app.services.workflow_service import WorkflowService
from app.services.ai_service import AIService
from app.core.exceptions import EntityNotFoundException

router = APIRouter()


@router.post(
    "/questions/{question_id}/generate-draft",
    response_model=AIGenerateDraftResponse,
    summary="AI Generate Draft Response",
    description="Generates an enterprise-ready RFP answer draft using Gemini with RAG citation. Enforces IsAIGenerated=True and Status='Draft'.",
)
def generate_ai_draft_response(
    question_id: int,
    request: AIGenerateDraftRequest = AIGenerateDraftRequest(),
    db: Session = Depends(get_db),
):
    question = db.get(RFPQuestion, question_id)
    if not question:
        raise EntityNotFoundException("RFPQuestion", question_id)

    ai_service = AIService(db)
    ai_result = ai_service.generate_draft_response(
        question_text=question.QuestionText,
        category=question.Category,
        context_notes=request.ContextNotes,
    )

    # Automatically save as response draft or update current draft
    workflow_service = WorkflowService(db)
    stmt = select(RFPResponse).where(RFPResponse.QuestionId == question_id)
    existing_resp = db.scalars(stmt).first()

    if existing_resp:
        resp = workflow_service.update_response_text(
            response_id=existing_resp.ResponseId,
            new_text=ai_result["draft_text"],
        )
        resp.IsAIGenerated = True
        resp.Status = "Draft"
        db.commit()
        db.refresh(resp)
    else:
        resp = workflow_service.get_or_create_response(
            question_id=question_id,
            initial_text=ai_result["draft_text"],
            is_ai_generated=True,
        )

    return AIGenerateDraftResponse(
        draft_text=ai_result["draft_text"],
        confidence_score=ai_result["confidence_score"],
        citations=ai_result["citations"],
        status=resp.Status,
        is_ai_generated=resp.IsAIGenerated,
        saved_response=resp,
    )


@router.get(
    "/questions/{question_id}/response",
    response_model=Optional[RFPResponseDetail],
    summary="Get Response for Question",
    description="Fetches current response with its version history.",
)
def get_response_for_question(
    question_id: int,
    db: Session = Depends(get_db),
):
    question = db.get(RFPQuestion, question_id)
    if not question:
        raise EntityNotFoundException("RFPQuestion", question_id)

    stmt = select(RFPResponse).where(RFPResponse.QuestionId == question_id)
    return db.scalars(stmt).first()


@router.post(
    "/questions/{question_id}/response",
    response_model=RFPResponseDetail,
    status_code=status.HTTP_201_CREATED,
    summary="Create or Save Response",
    description="Creates a manual draft response for a question and records version 1.",
)
def create_response_for_question(
    question_id: int,
    req: ResponseCreateRequest,
    db: Session = Depends(get_db),
):
    workflow_service = WorkflowService(db)
    return workflow_service.get_or_create_response(
        question_id=question_id,
        initial_text=req.ResponseText,
        is_ai_generated=False,
        user_id=req.UpdatedBy,
    )


@router.put(
    "/responses/{response_id}",
    response_model=RFPResponseDetail,
    summary="Update Response Text (Audit Versioned)",
    description="Edits response text and records an immutable audit version in ResponseVersion.",
)
def update_response_text(
    response_id: int,
    req: ResponseUpdateRequest,
    db: Session = Depends(get_db),
):
    workflow_service = WorkflowService(db)
    return workflow_service.update_response_text(
        response_id=response_id,
        new_text=req.ResponseText,
        user_id=req.UpdatedBy,
    )


@router.patch(
    "/responses/{response_id}/status",
    response_model=RFPResponseDetail,
    summary="Advance Response Approval Workflow State",
    description="State machine transition: Draft -> In Review -> Approved -> Rejected.",
)
def update_response_status(
    response_id: int,
    req: ResponseStatusUpdateRequest,
    db: Session = Depends(get_db),
):
    workflow_service = WorkflowService(db)
    return workflow_service.transition_response_status(
        response_id=response_id,
        target_status=req.Status,
        reviewer_id=req.ReviewerId,
    )


@router.get(
    "/responses/{response_id}/versions",
    response_model=List[ResponseVersionResponse],
    summary="Get Response Audit Versions",
    description="Returns complete version history and audit log for a given response.",
)
def get_response_versions(
    response_id: int,
    db: Session = Depends(get_db),
):
    workflow_service = WorkflowService(db)
    return workflow_service.get_audit_trail(response_id)


@router.post(
    "/responses/{response_id}/promote",
    response_model=ResponseLibraryItem,
    status_code=status.HTTP_201_CREATED,
    summary="Promote Approved Response to Knowledge Library",
    description="Promotion Gate: Only approved responses can be ingested into ResponseLibrary.",
)
def promote_response_to_library(
    response_id: int,
    req: PromoteToLibraryRequest = PromoteToLibraryRequest(),
    db: Session = Depends(get_db),
):
    workflow_service = WorkflowService(db)
    return workflow_service.promote_to_library(
        response_id=response_id,
        category=req.Category,
        technology=req.Technology,
    )
