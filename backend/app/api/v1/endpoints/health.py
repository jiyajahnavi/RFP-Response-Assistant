from datetime import datetime, timezone
import logging
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.database import get_db
from app.core.config import settings
from app.schemas.rfp import HealthResponse

router = APIRouter()
logger = logging.getLogger("rfp_assistant.api.health")


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check endpoint",
    description="Returns the health status of the API and validates SQL database connectivity.",
)
def check_health(db: Session = Depends(get_db)):
    db_connected = False
    try:
        # Validate database connectivity
        db.execute(text("SELECT 1"))
        db_connected = True
    except Exception as exc:
        logger.error("Health check database connectivity failure: %s", str(exc))
        db_connected = False

    return HealthResponse(
        status="healthy" if db_connected else "degraded",
        environment=settings.ENVIRONMENT,
        database_connected=db_connected,
        timestamp=datetime.now(timezone.utc),
        version="v1",
    )
