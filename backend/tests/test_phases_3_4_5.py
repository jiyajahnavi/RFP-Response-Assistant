import io
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.entities import RFP, RFPQuestion, RFPResponse, ResponseLibrary, ApplicationUser
from app.services.workflow_service import WorkflowService, ExportAnalyticsService
from app.services.ai_service import AIService
from app.core.exceptions import DomainValidationException


def test_ai_draft_generation_and_rules(client: TestClient, db_session: Session, monkeypatch):
    """Verify Phase 3 AI drafting, confidence, citations, and status='Draft'."""
    # Seed library entry
    lib_entry = ResponseLibrary(
        Question="How do you handle SOC 2 compliance and encryption?",
        Answer="We maintain SOC 2 Type II compliance and AES-256 encryption at rest and TLS 1.3 in transit.",
        Category="Security & Compliance",
        Technology="Enterprise Cloud",
    )
    db_session.add(lib_entry)

    # Seed RFP and question
    rfp = RFP(Title="Healthcare System RFP", CustomerName="HealthCorp", Status="Draft")
    db_session.add(rfp)
    db_session.commit()
    db_session.refresh(rfp)

    q = RFPQuestion(
        RfpId=rfp.RfpId,
        QuestionText="Describe your SOC 2 compliance certifications and data encryption methods.",
        Category="Security & Compliance",
        Sequence=1,
    )
    db_session.add(q)
    db_session.commit()
    db_session.refresh(q)

    # Test Semantic Library Search
    ai_service = AIService(db_session)
    search_results = ai_service.search_response_library("encryption and SOC 2 certifications")
    assert len(search_results) > 0
    assert search_results[0]["library_id"] == lib_entry.LibraryId
    assert search_results[0]["confidence_score"] > 0

    # Test AI Draft Generation endpoint
    response = client.post(
        f"/api/v1/questions/{q.QuestionId}/generate-draft",
        json={"ContextNotes": "Targeting HIPAA compliant cloud."}
    )
    assert response.status_code == 200
    data = response.json()
    assert "draft_text" in data
    assert data["status"] == "Draft"  # Invariant: AI answers initiate strictly in 'Draft'
    assert data["is_ai_generated"] is True  # Invariant: IsAIGenerated=True
    assert data["confidence_score"] >= 0.5
    assert len(data["citations"]) > 0


def test_workflow_state_machine_and_audit_trail(client: TestClient, db_session: Session):
    """Verify Phase 4 approval state machine, immutable audit trail, and promotion gate."""
    # Seed user
    reviewer = ApplicationUser(DisplayName="Jane Reviewer", Email="jane@example.com", Role="Reviewer")
    author = ApplicationUser(DisplayName="John Contributor", Email="john@example.com", Role="Contributor")
    db_session.add_all([reviewer, author])
    db_session.commit()
    db_session.refresh(reviewer)
    db_session.refresh(author)

    # Seed RFP & Question
    rfp = RFP(Title="Banking Security RFP", CustomerName="BankOfGlobal", Status="Draft")
    db_session.add(rfp)
    db_session.commit()
    db_session.refresh(rfp)

    q = RFPQuestion(
        RfpId=rfp.RfpId,
        QuestionText="What is your disaster recovery RTO and RPO?",
        Category="Support & SLA",
        Sequence=1,
    )
    db_session.add(q)
    db_session.commit()
    db_session.refresh(q)

    # 1. Create Initial Response (Draft)
    resp = client.post(
        f"/api/v1/questions/{q.QuestionId}/response",
        json={"ResponseText": "Initial draft: RTO is 4 hours, RPO is 1 hour.", "UpdatedBy": author.UserId}
    )
    assert resp.status_code == 201
    resp_data = resp.json()
    resp_id = resp_data["ResponseId"]
    assert resp_data["Status"] == "Draft"

    # 2. Update response text -> check immutable versioning
    upd = client.put(
        f"/api/v1/responses/{resp_id}",
        json={"ResponseText": "Revised draft: RTO is guaranteed under 2 hours, RPO is 15 minutes.", "UpdatedBy": author.UserId}
    )
    assert upd.status_code == 200

    # Check versions endpoint
    ver_res = client.get(f"/api/v1/responses/{resp_id}/versions")
    assert ver_res.status_code == 200
    versions = ver_res.json()
    assert len(versions) == 2
    assert versions[0]["VersionNumber"] == 2
    assert versions[1]["VersionNumber"] == 1

    # 3. Promotion Gate Test: Attempt to promote unapproved response -> must fail with 400
    promo_fail = client.post(f"/api/v1/responses/{resp_id}/promote", json={})
    assert promo_fail.status_code == 400
    assert "Promotion gate violation" in promo_fail.json()["message"]

    # 4. State Machine: Draft -> In Review -> Approved
    review_res = client.patch(
        f"/api/v1/responses/{resp_id}/status",
        json={"Status": "In Review"}
    )
    assert review_res.status_code == 200
    assert review_res.json()["Status"] == "In Review"

    approve_res = client.patch(
        f"/api/v1/responses/{resp_id}/status",
        json={"Status": "Approved", "ReviewerId": reviewer.UserId}
    )
    assert approve_res.status_code == 200
    approved_data = approve_res.json()
    assert approved_data["Status"] == "Approved"
    assert approved_data["ApprovedBy"] == reviewer.UserId
    assert approved_data["ApprovedDate"] is not None

    # 5. Promotion Gate Test: Now approved -> promotion succeeds!
    promo_success = client.post(
        f"/api/v1/responses/{resp_id}/promote",
        json={"Category": "Support & SLA", "Technology": "Disaster Recovery"}
    )
    assert promo_success.status_code == 201
    promo_data = promo_success.json()
    assert promo_data["Question"] == q.QuestionText
    assert promo_data["Answer"] == "Revised draft: RTO is guaranteed under 2 hours, RPO is 15 minutes."
    assert promo_data["Category"] == "Support & SLA"


def test_phase5_analytics_and_document_exports(client: TestClient, db_session: Session):
    """Verify Phase 5 proposal progress analytics and formatted exports (DOCX, XLSX, PDF)."""
    # Seed RFP with questions and responses
    rfp = RFP(Title="Enterprise CRM Modernization", CustomerName="Acme Corp", Description="Full RFP", Status="In Progress")
    db_session.add(rfp)
    db_session.commit()
    db_session.refresh(rfp)

    q1 = RFPQuestion(RfpId=rfp.RfpId, QuestionText="What cloud hosting providers do you support?", Category="Technical Architecture & Infrastructure", Sequence=1)
    q2 = RFPQuestion(RfpId=rfp.RfpId, QuestionText="Provide tiered pricing schedule.", Category="Pricing & Commercials", Sequence=2)
    db_session.add_all([q1, q2])
    db_session.commit()
    db_session.refresh(q1)
    db_session.refresh(q2)

    # Approve response for Q1
    resp1 = RFPResponse(
        QuestionId=q1.QuestionId,
        ResponseText="We support multi-cloud deployment across AWS, Azure, and Google Cloud Platform.",
        Status="Approved",
        IsAIGenerated=True,
    )
    db_session.add(resp1)
    db_session.commit()

    # 1. Analytics Check
    analytics_res = client.get(f"/api/v1/analytics?rfp_id={rfp.RfpId}")
    assert analytics_res.status_code == 200
    a_data = analytics_res.json()
    assert a_data["total_questions"] == 2
    assert a_data["answered_questions"] == 1
    assert a_data["approved_questions"] == 1
    assert a_data["completion_percentage"] == 50.0

    # Overall system analytics
    sys_analytics = client.get("/api/v1/analytics")
    assert sys_analytics.status_code == 200
    assert sys_analytics.json()["total_rfps"] >= 1

    # 2. Word (.docx) export
    docx_res = client.get(f"/api/v1/export/{rfp.RfpId}/docx")
    assert docx_res.status_code == 200
    assert "application/vnd.openxmlformats-officedocument.wordprocessingml.document" in docx_res.headers["content-type"]
    assert len(docx_res.content) > 1000

    # 3. Excel (.xlsx) export
    xlsx_res = client.get(f"/api/v1/export/{rfp.RfpId}/xlsx")
    assert xlsx_res.status_code == 200
    assert "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" in xlsx_res.headers["content-type"]
    assert len(xlsx_res.content) > 1000

    # 4. PDF export
    pdf_res = client.get(f"/api/v1/export/{rfp.RfpId}/pdf")
    assert pdf_res.status_code == 200
    assert "application/pdf" in pdf_res.headers["content-type"]
    assert pdf_res.content.startswith(b"%PDF")
