from fastapi import APIRouter
from app.api.v1.endpoints import health, rfps, questions, responses, library, export_analytics

api_router = APIRouter()

api_router.include_router(health.router, tags=["Health"])
api_router.include_router(rfps.router, prefix="/rfps", tags=["RFPs"])
api_router.include_router(questions.router, prefix="/questions", tags=["Questions"])
api_router.include_router(responses.router, tags=["Responses & Workflow"])
api_router.include_router(library.router, prefix="/library", tags=["Response Library"])
api_router.include_router(export_analytics.router, tags=["Export & Analytics"])
