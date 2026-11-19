from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core.database import get_db
from app.models.entities import ResponseLibrary
from app.schemas.rfp import (
    ResponseLibraryItem,
    ResponseLibraryCreate,
    LibrarySearchResponse,
    ErrorDetail,
)
from app.services.ai_service import AIService

router = APIRouter()


@router.get(
    "",
    response_model=List[ResponseLibraryItem],
    summary="List Response Library Entries",
    description="Returns verified historical Q&A responses in the library.",
)
def list_library_entries(
    category: Optional[str] = Query(None, description="Filter by category"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    stmt = select(ResponseLibrary)
    if category:
        stmt = stmt.where(ResponseLibrary.Category == category)
    stmt = stmt.offset(skip).limit(limit).order_by(ResponseLibrary.CreatedDate.desc())
    return list(db.scalars(stmt).all())


@router.post(
    "",
    response_model=ResponseLibraryItem,
    status_code=status.HTTP_201_CREATED,
    summary="Add Response to Library",
    description="Manually registers an approved standard response into the historical library.",
)
def add_library_entry(
    entry_in: ResponseLibraryCreate,
    db: Session = Depends(get_db),
):
    entry = ResponseLibrary(
        Question=entry_in.Question,
        Answer=entry_in.Answer,
        Category=entry_in.Category or "General",
        Technology=entry_in.Technology or "Standard",
        SourceRfpId=entry_in.SourceRfpId,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


@router.get(
    "/search",
    response_model=List[LibrarySearchResponse],
    summary="Semantic Search in Response Library",
    description="Searches the response library using semantic vector similarity and keyword ranking.",
)
def search_library(
    q: str = Query(..., min_length=2, description="Search query string"),
    category: Optional[str] = Query(None, description="Category filter"),
    top_k: int = Query(5, ge=1, le=20),
    db: Session = Depends(get_db),
):
    ai_service = AIService(db)
    return ai_service.search_response_library(query=q, category=category, top_k=top_k)
