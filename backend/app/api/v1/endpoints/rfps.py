from typing import List
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.rfp import RFPResponseSchema, RFPDetailResponse, ErrorDetail
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
