import logging
from typing import List, Optional
from sqlalchemy.orm import Session
from app.repositories.rfp_repository import RFPRepository
from app.models.entities import RFP
from app.schemas.rfp import RFPCreate
from app.core.exceptions import EntityNotFoundException

logger = logging.getLogger("rfp_assistant.services.rfp")


class RFPService:
    """Service layer handling RFP business logic."""

    def __init__(self, db: Session):
        self.repository = RFPRepository(db)

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
        rfp = RFP(
            Title=rfp_in.Title,
            CustomerName=rfp_in.CustomerName,
            Description=rfp_in.Description,
            DueDate=rfp_in.DueDate,
            Status=rfp_in.Status,
            CreatedBy=rfp_in.CreatedBy,
        )
        return self.repository.create(rfp)
