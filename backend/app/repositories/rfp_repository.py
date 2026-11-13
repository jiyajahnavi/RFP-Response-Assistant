import logging
from typing import List, Optional
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select
from app.models.entities import RFP

logger = logging.getLogger("rfp_assistant.repositories.rfp")


class RFPRepository:
    """Repository class encapsulating database operations for RFPs."""

    def __init__(self, db: Session):
        self.db = db

    def get_all(self, skip: int = 0, limit: int = 100) -> List[RFP]:
        """Fetch list of RFPs with pagination."""
        query = select(RFP).offset(skip).limit(limit).order_by(RFP.CreatedDate.desc())
        return list(self.db.scalars(query).all())

    def get_by_id(self, rfp_id: int) -> Optional[RFP]:
        """Fetch a single RFP by primary key including questions."""
        query = (
            select(RFP)
            .options(selectinload(RFP.questions))
            .where(RFP.RfpId == rfp_id)
        )
        return self.db.scalars(query).first()

    def create(self, rfp: RFP) -> RFP:
        """Add new RFP to database."""
        self.db.add(rfp)
        self.db.commit()
        self.db.refresh(rfp)
        return rfp
