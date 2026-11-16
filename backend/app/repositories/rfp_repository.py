import logging
from typing import List, Optional
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select, func
from app.models.entities import RFP, RFPQuestion, ApplicationUser

logger = logging.getLogger("rfp_assistant.repositories.rfp")


class RFPRepository:
    """Repository class encapsulating database operations for RFPs and Questions."""

    def __init__(self, db: Session):
        self.db = db

    def get_all(self, skip: int = 0, limit: int = 100) -> List[RFP]:
        """Fetch list of RFPs with pagination."""
        query = select(RFP).offset(skip).limit(limit).order_by(RFP.CreatedDate.desc())
        return list(self.db.scalars(query).all())

    def get_by_id(self, rfp_id: int) -> Optional[RFP]:
        """Fetch a single RFP by primary key including questions and assigned user."""
        query = (
            select(RFP)
            .options(
                selectinload(RFP.questions).selectinload(RFPQuestion.assigned_user)
            )
            .where(RFP.RfpId == rfp_id)
        )
        return self.db.scalars(query).first()

    def create(self, rfp: RFP) -> RFP:
        """Add new RFP to database."""
        self.db.add(rfp)
        self.db.commit()
        self.db.refresh(rfp)
        return rfp

    def update(self, rfp: RFP) -> RFP:
        """Update existing RFP."""
        self.db.commit()
        self.db.refresh(rfp)
        return rfp

    def delete(self, rfp: RFP) -> None:
        """Delete RFP and cascade delete questions."""
        self.db.delete(rfp)
        self.db.commit()

    # Question methods
    def get_question_by_id(self, question_id: int) -> Optional[RFPQuestion]:
        """Fetch single question with its assigned user."""
        query = (
            select(RFPQuestion)
            .options(selectinload(RFPQuestion.assigned_user))
            .where(RFPQuestion.QuestionId == question_id)
        )
        return self.db.scalars(query).first()

    def get_questions_by_rfp(self, rfp_id: int) -> List[RFPQuestion]:
        """Fetch all questions for an RFP ordered by sequence."""
        query = (
            select(RFPQuestion)
            .options(selectinload(RFPQuestion.assigned_user))
            .where(RFPQuestion.RfpId == rfp_id)
            .order_by(RFPQuestion.Sequence)
        )
        return list(self.db.scalars(query).all())

    def get_max_sequence(self, rfp_id: int) -> int:
        """Get the highest question sequence number in an RFP."""
        query = select(func.max(RFPQuestion.Sequence)).where(RFPQuestion.RfpId == rfp_id)
        result = self.db.scalar(query)
        return result or 0

    def create_question(self, question: RFPQuestion) -> RFPQuestion:
        """Add new question to an RFP."""
        self.db.add(question)
        self.db.commit()
        self.db.refresh(question)
        return question

    def create_questions_batch(self, questions: List[RFPQuestion]) -> List[RFPQuestion]:
        """Add multiple questions in batch."""
        self.db.add_all(questions)
        self.db.commit()
        for q in questions:
            self.db.refresh(q)
        return questions

    def update_question(self, question: RFPQuestion) -> RFPQuestion:
        """Update an existing question."""
        self.db.commit()
        self.db.refresh(question)
        return question

    def delete_question(self, question: RFPQuestion) -> None:
        """Delete question."""
        self.db.delete(question)
        self.db.commit()

    # User lookup for assignment validation
    def get_user_by_id(self, user_id: int) -> Optional[ApplicationUser]:
        return self.db.get(ApplicationUser, user_id)
