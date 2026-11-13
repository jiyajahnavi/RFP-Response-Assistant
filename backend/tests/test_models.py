from datetime import datetime, timezone
import pytest
from app.models.entities import (
    ApplicationUser,
    RFP,
    RFPQuestion,
    RFPResponse,
    ResponseVersion,
    ResponseLibrary,
    RfpStatus,
    ResponseStatus,
)


def test_models_relationships_and_constraints(db_session):
    # 1. User
    user = ApplicationUser(
        DisplayName="Admin User",
        Email="admin@company.com",
        Role="Administrator",
    )
    db_session.add(user)
    db_session.commit()
    assert user.UserId is not None

    # 2. RFP
    rfp = RFP(
        Title="Enterprise AI Suite",
        CustomerName="Acme Corp",
        Description="AI procurement proposal",
        DueDate=datetime(2027, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
        Status=RfpStatus.DRAFT.value,
        CreatedBy=user.UserId,
    )
    db_session.add(rfp)
    db_session.commit()
    assert rfp.RfpId is not None

    # 3. Question (belongs to RFP)
    question = RFPQuestion(
        RfpId=rfp.RfpId,
        QuestionText="How is customer data isolated and protected?",
        Category="Security",
        Sequence=1,
    )
    db_session.add(question)
    db_session.commit()
    assert question.QuestionId is not None
    assert question.rfp.Title == "Enterprise AI Suite"

    # 4. Response (AI-generated, starts in Draft status per business rule)
    ai_response = RFPResponse(
        QuestionId=question.QuestionId,
        ResponseText="All customer data is encrypted in transit using TLS 1.3 and at rest with AES-256.",
        IsAIGenerated=True,
        Status=ResponseStatus.DRAFT.value,
        UpdatedBy=user.UserId,
    )
    db_session.add(ai_response)
    db_session.commit()
    assert ai_response.ResponseId is not None
    assert ai_response.IsAIGenerated is True
    assert ai_response.Status == ResponseStatus.DRAFT.value

    # 5. ResponseVersion tracking
    version1 = ResponseVersion(
        ResponseId=ai_response.ResponseId,
        ResponseText=ai_response.ResponseText,
        VersionNumber=1,
        UpdatedBy=user.UserId,
    )
    db_session.add(version1)
    db_session.commit()
    assert version1.VersionId is not None
    assert len(ai_response.versions) == 1

    # 6. ResponseLibrary (Approved response entered into library)
    # Simulate approval
    ai_response.Status = ResponseStatus.APPROVED.value
    ai_response.ApprovedBy = user.UserId
    ai_response.ApprovedDate = datetime.now(timezone.utc)
    db_session.commit()

    library_item = ResponseLibrary(
        Question=question.QuestionText,
        Answer=ai_response.ResponseText,
        Category=question.Category,
        Technology="Security",
        SourceRfpId=rfp.RfpId,
    )
    db_session.add(library_item)
    db_session.commit()
    assert library_item.LibraryId is not None
    assert library_item.source_rfp.RfpId == rfp.RfpId
