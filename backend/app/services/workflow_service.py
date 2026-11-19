import io
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, func

import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from reportlab.lib.pagesizes import letter
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

from app.models.entities import (
    RFP,
    RFPQuestion,
    RFPResponse,
    ResponseVersion,
    ResponseLibrary,
    ApplicationUser,
    ResponseStatus,
    RfpStatus,
    QuestionStatus,
)
from app.core.exceptions import EntityNotFoundException, DomainValidationException

import logging

logger = logging.getLogger("rfp_assistant.services.workflow_export")


class WorkflowService:
    """
    Manages Response Approval State Machine, Audit Trails, and Knowledge Library Promotion.
    State Machine: Draft -> In Review -> Approved -> Rejected
    """

    def __init__(self, db: Session):
        self.db = db

    def get_or_create_response(
        self,
        question_id: int,
        initial_text: str,
        is_ai_generated: bool = False,
        user_id: Optional[int] = None,
    ) -> RFPResponse:
        """
        Creates or returns response for a question.
        Enforces: Responses start in 'Draft'.
        """
        question = self.db.get(RFPQuestion, question_id)
        if not question:
            raise EntityNotFoundException("RFPQuestion", question_id)

        # Check existing response
        stmt = select(RFPResponse).where(RFPResponse.QuestionId == question_id)
        existing = self.db.scalars(stmt).first()

        if existing:
            return existing

        now = datetime.now(timezone.utc)
        response = RFPResponse(
            QuestionId=question_id,
            ResponseText=initial_text,
            IsAIGenerated=is_ai_generated,
            Status=ResponseStatus.DRAFT.value,
            UpdatedBy=user_id,
            UpdatedDate=now,
        )
        self.db.add(response)
        self.db.commit()
        self.db.refresh(response)

        # Create Initial Version 1
        initial_version = ResponseVersion(
            ResponseId=response.ResponseId,
            ResponseText=initial_text,
            VersionNumber=1,
            UpdatedBy=user_id,
            UpdatedDate=now,
        )
        self.db.add(initial_version)

        # Update question status if pending
        if question.Status == QuestionStatus.PENDING.value:
            question.Status = QuestionStatus.ANSWERED.value

        self.db.commit()
        self.db.refresh(response)
        return response

    def update_response_text(
        self,
        response_id: int,
        new_text: str,
        user_id: Optional[int] = None,
    ) -> RFPResponse:
        """
        Update response text, increment version number, and record immutable audit trail.
        """
        response = self.db.get(RFPResponse, response_id)
        if not response:
            raise EntityNotFoundException("RFPResponse", response_id)

        if response.ResponseText == new_text:
            return response

        # Query current maximum version
        max_v_stmt = select(func.max(ResponseVersion.VersionNumber)).where(
            ResponseVersion.ResponseId == response_id
        )
        current_max_ver = self.db.scalar(max_v_stmt) or 0
        new_version_num = current_max_ver + 1

        now = datetime.now(timezone.utc)
        response.ResponseText = new_text
        response.UpdatedBy = user_id
        response.UpdatedDate = now

        # Record immutable audit version
        version_entry = ResponseVersion(
            ResponseId=response_id,
            ResponseText=new_text,
            VersionNumber=new_version_num,
            UpdatedBy=user_id,
            UpdatedDate=now,
        )
        self.db.add(version_entry)
        self.db.commit()
        self.db.refresh(response)
        return response

    def transition_response_status(
        self,
        response_id: int,
        target_status: str,
        reviewer_id: Optional[int] = None,
    ) -> RFPResponse:
        """
        State Machine Transitions:
        Draft -> In Review
        In Review -> Approved OR Rejected
        Rejected -> Draft OR In Review
        Approved -> In Review (re-opening for edits)
        """
        response = self.db.get(RFPResponse, response_id)
        if not response:
            raise EntityNotFoundException("RFPResponse", response_id)

        current = response.Status
        target = target_status.title() if target_status else ""

        valid_statuses = [
            ResponseStatus.DRAFT.value,
            ResponseStatus.IN_REVIEW.value,
            ResponseStatus.APPROVED.value,
            ResponseStatus.REJECTED.value,
        ]

        if target not in valid_statuses:
            raise DomainValidationException(f"Invalid target status '{target_status}'. Must be one of {valid_statuses}")

        now = datetime.now(timezone.utc)

        # Validate reviewer if user_id supplied
        if reviewer_id:
            reviewer = self.db.get(ApplicationUser, reviewer_id)
            if not reviewer:
                raise EntityNotFoundException("ApplicationUser", reviewer_id)

        # Enforce transitions
        if target == ResponseStatus.APPROVED.value:
            response.Status = ResponseStatus.APPROVED.value
            response.ApprovedBy = reviewer_id
            response.ApprovedDate = now

            # Question marks as Reviewed
            if response.question:
                response.question.Status = QuestionStatus.REVIEWED.value
        elif target == ResponseStatus.REJECTED.value:
            response.Status = ResponseStatus.REJECTED.value
            response.ApprovedBy = None
            response.ApprovedDate = None
        elif target == ResponseStatus.IN_REVIEW.value:
            response.Status = ResponseStatus.IN_REVIEW.value
            response.ApprovedBy = None
            response.ApprovedDate = None
        elif target == ResponseStatus.DRAFT.value:
            response.Status = ResponseStatus.DRAFT.value
            response.ApprovedBy = None
            response.ApprovedDate = None

        response.UpdatedDate = now
        self.db.commit()
        self.db.refresh(response)
        return response

    def promote_to_library(
        self,
        response_id: int,
        category: Optional[str] = None,
        technology: Optional[str] = None,
    ) -> ResponseLibrary:
        """
        Promotion Gate Business Invariant:
        ONLY Approved responses can be stored into ResponseLibrary.
        """
        response = self.db.get(RFPResponse, response_id)
        if not response:
            raise EntityNotFoundException("RFPResponse", response_id)

        if response.Status != ResponseStatus.APPROVED.value:
            raise DomainValidationException(
                f"Promotion gate violation: Only Approved responses can enter the ResponseLibrary. Current status is '{response.Status}'."
            )

        question = response.question
        q_text = question.QuestionText if question else "RFP Question"
        cat = category or (question.Category if question else "General")
        source_rfp_id = question.RfpId if question else None

        # Check if already in library
        existing = self.db.scalars(
            select(ResponseLibrary).where(
                ResponseLibrary.Question == q_text,
                ResponseLibrary.Answer == response.ResponseText,
            )
        ).first()

        if existing:
            return existing

        library_entry = ResponseLibrary(
            Question=q_text,
            Answer=response.ResponseText,
            Category=cat,
            Technology=technology or "Standard",
            SourceRfpId=source_rfp_id,
            CreatedDate=datetime.now(timezone.utc),
        )
        self.db.add(library_entry)
        self.db.commit()
        self.db.refresh(library_entry)
        return library_entry

    def get_audit_trail(self, response_id: int) -> List[ResponseVersion]:
        """Fetch all immutable historical versions for a response."""
        response = self.db.get(RFPResponse, response_id)
        if not response:
            raise EntityNotFoundException("RFPResponse", response_id)

        stmt = (
            select(ResponseVersion)
            .where(ResponseVersion.ResponseId == response_id)
            .order_by(ResponseVersion.VersionNumber.desc())
        )
        return list(self.db.scalars(stmt).all())


class ExportAnalyticsService:
    """
    Analytics, SLA Metrics, and Export Services (Word, Excel, PDF).
    """

    def __init__(self, db: Session):
        self.db = db

    def get_analytics(self, rfp_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Calculate proposal completion progress, status counts, SLA, and turnaround metrics.
        """
        if rfp_id:
            rfp = self.db.get(RFP, rfp_id)
            if not rfp:
                raise EntityNotFoundException("RFP", rfp_id)
            questions = rfp.questions
            total_questions = len(questions)

            status_distribution = {}
            category_distribution = {}
            approved_count = 0
            answered_count = 0

            for q in questions:
                # count categories
                c = q.Category or "Uncategorized"
                category_distribution[c] = category_distribution.get(c, 0) + 1

                # inspect responses
                if q.responses:
                    resp = q.responses[0]
                    status_distribution[resp.Status] = status_distribution.get(resp.Status, 0) + 1
                    if resp.Status == ResponseStatus.APPROVED.value:
                        approved_count += 1
                    answered_count += 1
                else:
                    status_distribution["No Response"] = status_distribution.get("No Response", 0) + 1

            completion_percentage = round((approved_count / total_questions * 100), 1) if total_questions > 0 else 0.0

            # SLA check: days remaining until DueDate
            days_remaining = None
            is_overdue = False
            if rfp.DueDate:
                now_date = datetime.now(timezone.utc)
                diff = rfp.DueDate - (now_date.replace(tzinfo=None) if rfp.DueDate.tzinfo is None else now_date)
                days_remaining = diff.days
                if days_remaining < 0:
                    is_overdue = True

            return {
                "rfp_id": rfp.RfpId,
                "title": rfp.Title,
                "customer_name": rfp.CustomerName,
                "total_questions": total_questions,
                "answered_questions": answered_count,
                "approved_questions": approved_count,
                "completion_percentage": completion_percentage,
                "status_distribution": status_distribution,
                "category_distribution": category_distribution,
                "due_date": rfp.DueDate.isoformat() if rfp.DueDate else None,
                "days_remaining": days_remaining,
                "is_overdue": is_overdue,
            }
        else:
            # System-wide overall metrics
            total_rfps = self.db.scalar(select(func.count(RFP.RfpId))) or 0
            total_questions = self.db.scalar(select(func.count(RFPQuestion.QuestionId))) or 0
            total_responses = self.db.scalar(select(func.count(RFPResponse.ResponseId))) or 0
            total_approved = self.db.scalar(
                select(func.count(RFPResponse.ResponseId)).where(RFPResponse.Status == ResponseStatus.APPROVED.value)
            ) or 0
            total_library_items = self.db.scalar(select(func.count(ResponseLibrary.LibraryId))) or 0

            return {
                "total_rfps": total_rfps,
                "total_questions": total_questions,
                "total_responses": total_responses,
                "total_approved_responses": total_approved,
                "total_library_entries": total_library_items,
                "overall_approval_rate": round((total_approved / total_responses * 100), 1) if total_responses > 0 else 0.0,
            }

    def export_docx(self, rfp_id: int) -> io.BytesIO:
        """Generate professionally styled Word (.docx) proposal package."""
        rfp = self.db.get(RFP, rfp_id)
        if not rfp:
            raise EntityNotFoundException("RFP", rfp_id)

        doc = docx.Document()

        # Document Header
        title_p = doc.add_paragraph()
        run = title_p.add_run(f"PROPOSAL RESPONSE: {rfp.Title.upper()}")
        run.bold = True
        run.font.size = Pt(20)
        run.font.color.rgb = RGBColor(15, 76, 129) # Classic Navy

        sub_p = doc.add_paragraph()
        sub_run = sub_p.add_run(f"Prepared for: {rfp.CustomerName} | Date: {datetime.now().strftime('%B %d, %Y')}")
        sub_run.font.size = Pt(11)
        sub_run.font.italic = True
        sub_run.font.color.rgb = RGBColor(100, 100, 100)

        doc.add_paragraph("―" * 50)

        # Overview Metadata
        meta_table = doc.add_table(rows=3, cols=2)
        meta_table.autofit = True
        data = [
            ("Client Name:", rfp.CustomerName),
            ("RFP Status:", rfp.Status),
            ("Target Submission Date:", rfp.DueDate.strftime('%Y-%m-%d') if rfp.DueDate else "N/A"),
        ]
        for idx, (label, val) in enumerate(data):
            r = meta_table.rows[idx]
            r.cells[0].paragraphs[0].add_run(label).bold = True
            r.cells[1].paragraphs[0].add_run(val)

        doc.add_paragraph().add_run("1. Executive Summary & Questionnaire Matrix").bold = True
        doc.add_paragraph(rfp.Description or "This proposal addresses all technical, architectural, and commercial requirements outlined in the client's RFP questionnaire.")

        # Questions & Responses Matrix
        for q in rfp.questions:
            q_header = doc.add_paragraph()
            q_header.paragraph_format.space_before = Pt(14)
            q_run = q_header.add_run(f"Q{q.Sequence}. [{q.Category or 'General'}] {q.QuestionText}")
            q_run.bold = True
            q_run.font.color.rgb = RGBColor(26, 82, 118)

            resp_p = doc.add_paragraph()
            resp_p.paragraph_format.left_indent = Inches(0.25)
            if q.responses:
                resp = q.responses[0]
                resp_run = resp_p.add_run(resp.ResponseText)
                meta_note = doc.add_paragraph()
                meta_note.paragraph_format.left_indent = Inches(0.25)
                note_run = meta_note.add_run(f"Status: {resp.Status} | Verified: {resp.ApprovedDate.strftime('%Y-%m-%d') if resp.ApprovedDate else 'Pending Approval'}")
                note_run.font.size = Pt(8.5)
                note_run.font.italic = True
                note_run.font.color.rgb = RGBColor(120, 120, 120)
            else:
                resp_p.add_run("[Pending Final Draft Response]").italic = True

        out = io.BytesIO()
        doc.save(out)
        out.seek(0)
        return out

    def export_xlsx(self, rfp_id: int) -> io.BytesIO:
        """Generate formatted Excel (.xlsx) questionnaire workbook."""
        rfp = self.db.get(RFP, rfp_id)
        if not rfp:
            raise EntityNotFoundException("RFP", rfp_id)

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "RFP Responses"

        # Headers
        headers = ["Seq", "Category", "Question Text", "Response Text", "Status", "AI Draft", "Reviewed By", "Approval Date"]
        ws.append(headers)

        header_fill = PatternFill(start_color="1A365D", end_color="1A365D", fill_type="solid")
        header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        border = Border(
            left=Side(style='thin', color='CCCCCC'),
            right=Side(style='thin', color='CCCCCC'),
            top=Side(style='thin', color='CCCCCC'),
            bottom=Side(style='thin', color='CCCCCC'),
        )

        for col_num in range(1, len(headers) + 1):
            cell = ws.cell(row=1, column=col_num)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

        for q in rfp.questions:
            resp_text = ""
            status = "No Response"
            is_ai = "No"
            reviewed_by = "N/A"
            approval_date = "N/A"

            if q.responses:
                r = q.responses[0]
                resp_text = r.ResponseText
                status = r.Status
                is_ai = "Yes" if r.IsAIGenerated else "No"
                if r.approver:
                    reviewed_by = r.approver.DisplayName
                if r.ApprovedDate:
                    approval_date = r.ApprovedDate.strftime("%Y-%m-%d")

            row_data = [
                q.Sequence,
                q.Category or "General",
                q.QuestionText,
                resp_text,
                status,
                is_ai,
                reviewed_by,
                approval_date,
            ]
            ws.append(row_data)

        # Style data rows & auto-size columns
        for row in ws.iter_rows(min_row=2, max_row=ws.max_row, min_col=1, max_col=len(headers)):
            for cell in row:
                cell.border = border
                cell.alignment = Alignment(vertical="top", wrap_text=True)

        ws.column_dimensions["A"].width = 6
        ws.column_dimensions["B"].width = 22
        ws.column_dimensions["C"].width = 45
        ws.column_dimensions["D"].width = 60
        ws.column_dimensions["E"].width = 14
        ws.column_dimensions["F"].width = 10
        ws.column_dimensions["G"].width = 18
        ws.column_dimensions["H"].width = 15

        out = io.BytesIO()
        wb.save(out)
        out.seek(0)
        return out

    def export_pdf(self, rfp_id: int) -> io.BytesIO:
        """Generate formatted PDF client proposal document using ReportLab."""
        rfp = self.db.get(RFP, rfp_id)
        if not rfp:
            raise EntityNotFoundException("RFP", rfp_id)

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=40,
            leftMargin=40,
            topMargin=40,
            bottomMargin=40,
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "DocTitle",
            parent=styles["Heading1"],
            fontSize=20,
            leading=24,
            textColor=colors.HexColor("#0F4C81"),
            spaceAfter=6,
        )
        subtitle_style = ParagraphStyle(
            "DocSubtitle",
            parent=styles["Normal"],
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#555555"),
            spaceAfter=15,
        )
        q_style = ParagraphStyle(
            "QuestionStyle",
            parent=styles["Heading3"],
            fontSize=11,
            leading=15,
            textColor=colors.HexColor("#1A365D"),
            spaceBefore=10,
            spaceAfter=4,
        )
        a_style = ParagraphStyle(
            "AnswerStyle",
            parent=styles["Normal"],
            fontSize=9.5,
            leading=14,
            textColor=colors.HexColor("#222222"),
            leftIndent=12,
            spaceAfter=4,
        )
        meta_style = ParagraphStyle(
            "MetaStyle",
            parent=styles["Normal"],
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#777777"),
            leftIndent=12,
            spaceAfter=8,
        )

        elements = []
        elements.append(Paragraph(f"PROPOSAL PACKAGE: {rfp.Title}", title_style))
        elements.append(Paragraph(
            f"Client: <b>{rfp.CustomerName}</b> &nbsp;|&nbsp; Due Date: <b>{rfp.DueDate.strftime('%Y-%m-%d') if rfp.DueDate else 'N/A'}</b> &nbsp;|&nbsp; Generated: <b>{datetime.now().strftime('%Y-%m-%d')}</b>",
            subtitle_style
        ))
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#CCCCCC"), spaceAfter=15))

        elements.append(Paragraph("<b>Executive Summary:</b> " + (rfp.Description or "Formal RFP response submission."), a_style))
        elements.append(Spacer(1, 15))

        for q in rfp.questions:
            q_text = f"Q{q.Sequence}. [{q.Category or 'General'}] {q.QuestionText}"
            elements.append(Paragraph(q_text, q_style))

            if q.responses:
                resp = q.responses[0]
                elements.append(Paragraph(resp.ResponseText.replace("\n", "<br/>"), a_style))
                meta_info = f"Status: <b>{resp.Status}</b> &nbsp;|&nbsp; AI Generated: <b>{'Yes' if resp.IsAIGenerated else 'No'}</b>"
                if resp.ApprovedDate:
                    meta_info += f" &nbsp;|&nbsp; Approved: {resp.ApprovedDate.strftime('%Y-%m-%d')}"
                elements.append(Paragraph(meta_info, meta_style))
            else:
                elements.append(Paragraph("<i>[Pending draft response]</i>", a_style))

            elements.append(Spacer(1, 6))

        doc.build(elements)
        buffer.seek(0)
        return buffer
