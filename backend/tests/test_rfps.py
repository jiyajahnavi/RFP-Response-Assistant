from datetime import datetime, timezone
from fastapi import status
from app.models.entities import RFP, RFPQuestion, ApplicationUser, RfpStatus, ResponseStatus


def test_list_rfps_empty(client):
    response = client.get("/api/v1/rfps")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []


def test_list_rfps_and_get_by_id(client, db_session):
    # Setup test user and RFP
    user = ApplicationUser(
        DisplayName="Jane Doe",
        Email="jane.doe@example.com",
        Role="ProposalManager",
    )
    db_session.add(user)
    db_session.commit()

    rfp = RFP(
        Title="Cloud Migration RFP",
        CustomerName="Global Finance Inc",
        Description="Request for cloud migration solution and architecture proposal.",
        DueDate=datetime(2026, 12, 31, 18, 0, 0),
        Status=RfpStatus.IN_PROGRESS.value,
        CreatedBy=user.UserId,
    )
    db_session.add(rfp)
    db_session.commit()

    # Add questions for this RFP
    q1 = RFPQuestion(
        RfpId=rfp.RfpId,
        QuestionText="What is your architecture for Azure disaster recovery?",
        Category="Technical",
        Sequence=1,
    )
    q2 = RFPQuestion(
        RfpId=rfp.RfpId,
        QuestionText="What are your standard SLA commitments?",
        Category="Commercial",
        Sequence=2,
    )
    db_session.add_all([q1, q2])
    db_session.commit()

    # Test list endpoint
    response = client.get("/api/v1/rfps")
    assert response.status_code == status.HTTP_200_OK
    rfp_list = response.json()
    assert len(rfp_list) >= 1
    item = next(r for r in rfp_list if r["RfpId"] == rfp.RfpId)
    assert item["Title"] == "Cloud Migration RFP"
    assert item["CustomerName"] == "Global Finance Inc"

    # Test get by ID endpoint
    detail_response = client.get(f"/api/v1/rfps/{rfp.RfpId}")
    assert detail_response.status_code == status.HTTP_200_OK
    detail_data = detail_response.json()
    assert detail_data["RfpId"] == rfp.RfpId
    assert detail_data["Title"] == "Cloud Migration RFP"
    assert len(detail_data["questions"]) == 2
    assert detail_data["questions"][0]["Sequence"] == 1
    assert detail_data["questions"][0]["QuestionText"] == "What is your architecture for Azure disaster recovery?"


def test_get_rfp_not_found(client):
    response = client.get("/api/v1/rfps/999999")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    error_data = response.json()
    assert "not found" in error_data["message"].lower()
