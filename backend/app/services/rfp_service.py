import logging
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from app.repositories.rfp_repository import RFPRepository
from app.models.entities import RFP, RFPQuestion, ApplicationUser
from app.schemas.rfp import (
    RFPCreate,
    RFPUpdate,
    QuestionCreate,
    QuestionUpdate,
)
from app.core.exceptions import EntityNotFoundException, DomainValidationException
from app.utils.classifier import classify_question
from app.utils.document_parser import parse_document

logger = logging.getLogger("rfp_assistant.services.rfp")


class RFPService:
    """Service layer handling RFP and Question business logic."""

    def __init__(self, db: Session):
        self.repository = RFPRepository(db)

    # --- RFP Operations ---
    def list_rfps(self, skip: int = 0, limit: int = 100) -> List[RFP]:
        logger.info("Listing RFPs: skip=%d, limit=%d", skip, limit)
        return self.repository.get_all(skip=skip, limit=limit)

    def get_rfp_by_id(self, rfp_id: int) -> RFP:
        logger.info("Fetching RFP with id: %d", rfp_id)
        rfp = self.repository.get_by_id(rfp_id)
        if not rfp:
            logger.warning("RFP with id %d not found", rfp_id)
            raise EntityNotFoundException("RFP", rfp_id)
        return rfp

    def create_rfp(self, rfp_in: RFPCreate) -> RFP:
        logger.info("Creating new RFP for customer: %s", rfp_in.CustomerName)
        if rfp_in.CreatedBy is not None:
            user = self.repository.get_user_by_id(rfp_in.CreatedBy)
            if not user:
                raise EntityNotFoundException("ApplicationUser", rfp_in.CreatedBy)

        rfp = RFP(
            Title=rfp_in.Title,
            CustomerName=rfp_in.CustomerName,
            Description=rfp_in.Description,
            DueDate=rfp_in.DueDate,
            Status=rfp_in.Status,
            CreatedBy=rfp_in.CreatedBy,
        )
        return self.repository.create(rfp)

    def update_rfp(self, rfp_id: int, rfp_in: RFPUpdate) -> RFP:
        logger.info("Updating RFP with id: %d", rfp_id)
        rfp = self.get_rfp_by_id(rfp_id)

        update_data = rfp_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(rfp, field, value)

        return self.repository.update(rfp)

    def delete_rfp(self, rfp_id: int) -> None:
        logger.info("Deleting RFP with id: %d", rfp_id)
        rfp = self.get_rfp_by_id(rfp_id)
        self.repository.delete(rfp)

    # --- Question Operations ---
    def list_questions(self, rfp_id: int) -> List[RFPQuestion]:
        # Validate RFP exists
        self.get_rfp_by_id(rfp_id)
        return self.repository.get_questions_by_rfp(rfp_id)

    def get_question_by_id(self, question_id: int) -> RFPQuestion:
        q = self.repository.get_question_by_id(question_id)
        if not q:
            raise EntityNotFoundException("RFPQuestion", question_id)
        return q

    def create_question(self, rfp_id: int, q_in: QuestionCreate) -> RFPQuestion:
        # Validate RFP exists
        self.get_rfp_by_id(rfp_id)

        # Validate AssignedTo SME if provided
        if q_in.AssignedTo is not None:
            self.validate_sme_user(q_in.AssignedTo)

        # Determine sequence automatically if not given
        sequence = q_in.Sequence
        if sequence is None:
            sequence = self.repository.get_max_sequence(rfp_id) + 1

        # Classify automatically if category is omitted
        category = q_in.Category or classify_question(q_in.QuestionText)

        question = RFPQuestion(
            RfpId=rfp_id,
            QuestionText=q_in.QuestionText,
            Category=category,
            Sequence=sequence,
            Status=q_in.Status,
            AssignedTo=q_in.AssignedTo,
        )
        return self.repository.create_question(question)

    def update_question(self, question_id: int, q_in: QuestionUpdate) -> RFPQuestion:
        question = self.get_question_by_id(question_id)

        update_data = q_in.model_dump(exclude_unset=True)
        if "AssignedTo" in update_data and update_data["AssignedTo"] is not None:
            self.validate_sme_user(update_data["AssignedTo"])

        if "QuestionText" in update_data and "Category" not in update_data:
            # If question text changes and category was not explicitly updated, re-classify
            question.Category = classify_question(update_data["QuestionText"])

        for field, value in update_data.items():
            setattr(question, field, value)

        return self.repository.update_question(question)

    def delete_question(self, question_id: int) -> None:
        question = self.get_question_by_id(question_id)
        self.repository.delete_question(question)

    def assign_question(self, question_id: int, user_id: Optional[int]) -> RFPQuestion:
        question = self.get_question_by_id(question_id)
        if user_id is not None:
            self.validate_sme_user(user_id)
        question.AssignedTo = user_id
        return self.repository.update_question(question)

    def validate_sme_user(self, user_id: int) -> ApplicationUser:
        user = self.repository.get_user_by_id(user_id)
        if not user:
            raise EntityNotFoundException("ApplicationUser", user_id)
        return user

    # --- Document Ingestion ---
    def ingest_document(self, rfp_id: int, filename: str, file_bytes: bytes) -> List[RFPQuestion]:
        """
        Parses questions from uploaded PDF, DOCX, or XLSX file,
        applies classification, automatically numbers sequences, and saves to the database.
        """
        self.get_rfp_by_id(rfp_id)
        parsed_items = parse_document(filename, file_bytes)

        if not parsed_items:
            raise DomainValidationException("No questions could be extracted from the uploaded document.")

        current_max_seq = self.repository.get_max_sequence(rfp_id)
        questions_to_create = []

        for idx, item in enumerate(parsed_items, start=1):
            q = RFPQuestion(
                RfpId=rfp_id,
                QuestionText=item["QuestionText"],
                Category=item["Category"],
                Sequence=current_max_seq + idx,
                Status="Pending",
            )
            questions_to_create.append(q)

        return self.repository.create_questions_batch(questions_to_create)
