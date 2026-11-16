import io
import pytest
from app.models.entities import RFP, RFPQuestion, ApplicationUser
from app.utils.classifier import classify_question
from app.utils.document_parser import parse_docx, parse_xlsx, extract_questions_from_text


def test_question_classifier():
    assert classify_question("Does the solution support SOC 2 and HIPAA compliance encryption?") == "Security & Compliance"
    assert classify_question("What is your cloud infrastructure architecture and Kubernetes deployment?") == "Technical Architecture & Infrastructure"
    assert classify_question("What is the annual pricing licensing cost and subscription discount?") == "Pricing & Commercials"
    assert classify_question("What is your SLA support response time for critical downtime incidents?") == "Support & SLA"
    assert classify_question("Can you describe your company history, customer references, and project team?") == "Company & Experience"
    assert classify_question("Can you explain how this works?") == "General"


def test_rfp_crud_flow(client, db_session):
    # 1. Create RFP
    create_payload = {
        "Title": "Healthcare Cloud Modernization",
        "CustomerName": "Apex Health Systems",
        "Description": "Modernizing legacy EHR to HIPAA compliant cloud",
        "Status": "Draft"
    }
    res = client.post("/api/v1/rfps", json=create_payload)
    assert res.status_code == 201
    rfp_data = res.json()
    rfp_id = rfp_data["RfpId"]
    assert rfp_data["Title"] == "Healthcare Cloud Modernization"
    assert rfp_data["CustomerName"] == "Apex Health Systems"

    # 2. Update RFP
    update_payload = {
        "Title": "Healthcare Cloud Modernization - Updated",
        "Status": "In Progress"
    }
    res = client.put(f"/api/v1/rfps/{rfp_id}", json=update_payload)
    assert res.status_code == 200
    assert res.json()["Title"] == "Healthcare Cloud Modernization - Updated"
    assert res.json()["Status"] == "In Progress"

    # 3. Add Questions with auto-sequence and auto-classification
    q1_payload = {
        "QuestionText": "What data encryption and HIPAA compliance standards do you maintain?"
    }
    res = client.post(f"/api/v1/rfps/{rfp_id}/questions", json=q1_payload)
    assert res.status_code == 201
    q1_data = res.json()
    assert q1_data["Sequence"] == 1
    assert q1_data["Category"] == "Security & Compliance"

    q2_payload = {
        "QuestionText": "What are the subscription licensing fee and commercial pricing terms?"
    }
    res = client.post(f"/api/v1/rfps/{rfp_id}/questions", json=q2_payload)
    assert res.status_code == 201
    q2_data = res.json()
    assert q2_data["Sequence"] == 2
    assert q2_data["Category"] == "Pricing & Commercials"

    # 4. List Questions
    res = client.get(f"/api/v1/rfps/{rfp_id}/questions")
    assert res.status_code == 200
    questions = res.json()
    assert len(questions) == 2
    assert questions[0]["Sequence"] == 1
    assert questions[1]["Sequence"] == 2

    # 5. Get Question by ID
    q1_id = q1_data["QuestionId"]
    res = client.get(f"/api/v1/questions/{q1_id}")
    assert res.status_code == 200
    assert res.json()["QuestionId"] == q1_id

    # 6. Assign SME to Question
    user = ApplicationUser(DisplayName="Dr. Alice Smith", Email="alice@example.com", Role="SME")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    assign_payload = {"AssignedTo": user.UserId}
    res = client.patch(f"/api/v1/questions/{q1_id}/assign", json=assign_payload)
    assert res.status_code == 200
    assigned_q = res.json()
    assert assigned_q["AssignedTo"] == user.UserId
    assert assigned_q["assigned_user"]["DisplayName"] == "Dr. Alice Smith"

    # 7. Update Question details
    res = client.put(f"/api/v1/questions/{q1_id}", json={"Status": "Answered"})
    assert res.status_code == 200
    assert res.json()["Status"] == "Answered"

    # 8. Delete Question
    res = client.delete(f"/api/v1/questions/{q2_data['QuestionId']}")
    assert res.status_code == 204

    # Confirm deletion
    res = client.get(f"/api/v1/questions/{q2_data['QuestionId']}")
    assert res.status_code == 404

    # 9. Delete RFP (Cascade verify)
    res = client.delete(f"/api/v1/rfps/{rfp_id}")
    assert res.status_code == 204

    # Confirm RFP deleted
    res = client.get(f"/api/v1/rfps/{rfp_id}")
    assert res.status_code == 404


def test_document_ingestion_api(client, db_session):
    # Create an RFP
    rfp = RFP(Title="Fintech Security RFP", CustomerName="Global Bank Corp", Status="Draft")
    db_session.add(rfp)
    db_session.commit()
    db_session.refresh(rfp)

    # Create dummy XLSX document in-memory
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Questions"
    ws.append(["Requirement / Question", "Category"])
    ws.append(["Does your platform support multi-factor authentication (MFA) and SOC 2?", "Security & Compliance"])
    ws.append(["What is the guaranteed SLA uptime and disaster recovery response time?", "Support & SLA"])
    ws.append(["Describe your technical cloud architecture and database scalability.", ""])

    xlsx_stream = io.BytesIO()
    wb.save(xlsx_stream)
    xlsx_bytes = xlsx_stream.getvalue()

    # Upload document
    res = client.post(
        f"/api/v1/rfps/{rfp.RfpId}/ingest",
        files={"file": ("fintech_rfp.xlsx", xlsx_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
    )
    assert res.status_code == 201
    ingest_data = res.json()
    assert ingest_data["questions_extracted"] == 3
    assert len(ingest_data["questions"]) == 3

    # Check auto-numbering sequence and categories
    q_list = ingest_data["questions"]
    assert q_list[0]["Sequence"] == 1
    assert q_list[0]["Category"] == "Security & Compliance"
    assert q_list[1]["Sequence"] == 2
    assert q_list[1]["Category"] == "Support & SLA"
    assert q_list[2]["Sequence"] == 3
    assert q_list[2]["Category"] == "Technical Architecture & Infrastructure"
