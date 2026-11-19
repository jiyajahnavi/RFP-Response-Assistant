from typing import Optional
from fastapi import APIRouter, Depends, Query, status, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.rfp import AnalyticsResponse, ErrorDetail
from app.services.workflow_service import ExportAnalyticsService

router = APIRouter()


@router.get(
    "/analytics",
    response_model=AnalyticsResponse,
    summary="Get RFP / System Analytics",
    description="Retrieves progress metrics, SLA status, completion percentage, and category breakdown.",
)
def get_analytics(
    rfp_id: Optional[int] = Query(None, description="Optional RFP ID for specific proposal analytics"),
    db: Session = Depends(get_db),
):
    service = ExportAnalyticsService(db)
    return service.get_analytics(rfp_id=rfp_id)


@router.get(
    "/export/{rfp_id}/docx",
    summary="Export Proposal to Word (.docx)",
    description="Exports formatted proposal questionnaire and client answers into a Microsoft Word document.",
)
def export_rfp_docx(
    rfp_id: int,
    db: Session = Depends(get_db),
):
    service = ExportAnalyticsService(db)
    file_stream = service.export_docx(rfp_id)
    filename = f"RFP_{rfp_id}_Proposal_Package.docx"
    return StreamingResponse(
        file_stream,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "/export/{rfp_id}/xlsx",
    summary="Export Proposal to Excel (.xlsx)",
    description="Exports proposal questionnaire and responses into a styled Microsoft Excel spreadsheet.",
)
def export_rfp_xlsx(
    rfp_id: int,
    db: Session = Depends(get_db),
):
    service = ExportAnalyticsService(db)
    file_stream = service.export_xlsx(rfp_id)
    filename = f"RFP_{rfp_id}_Questionnaire.xlsx"
    return StreamingResponse(
        file_stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "/export/{rfp_id}/pdf",
    summary="Export Proposal to PDF",
    description="Exports styled, client-ready proposal package into a formatted PDF document.",
)
def export_rfp_pdf(
    rfp_id: int,
    db: Session = Depends(get_db),
):
    service = ExportAnalyticsService(db)
    file_stream = service.export_pdf(rfp_id)
    filename = f"RFP_{rfp_id}_Proposal_Package.pdf"
    return StreamingResponse(
        file_stream,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
