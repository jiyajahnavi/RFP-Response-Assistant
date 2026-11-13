import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy import text

from app.core.config import settings
from app.core.logging import setup_logging
from app.core.database import engine
from app.core.exceptions import AppException
from app.api.v1.router import api_router

logger = setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: log configuration and verify database accessibility
    logger.info("Initializing %s in %s mode...", settings.PROJECT_NAME, settings.ENVIRONMENT)
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Database connection validated on startup.")
    except Exception as exc:
        logger.warning("Database connection test during startup: %s", str(exc))
    yield
    # Shutdown
    logger.info("Shutting down %s...", settings.PROJECT_NAME)
    engine.dispose()


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Backend API for the RFP Response Assistant application.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# CORS middleware for Angular frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Centralized exception handlers
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    logger.warning("Application error: status_code=%s, message=%s", exc.status_code, exc.message)
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": exc.message, "details": exc.details},
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled server exception on %s %s: %s", request.method, request.url.path, str(exc), exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"message": "Internal server error occurred.", "details": {}},
    )


# Include API v1 endpoints
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/api/v1/docs", include_in_schema=False)
def redirect_v1_docs():
    return RedirectResponse(url="/docs")


@app.get("/api/v1/redoc", include_in_schema=False)
def redirect_v1_redoc():
    return RedirectResponse(url="/redoc")


@app.get("/api/v1/openapi.json", include_in_schema=False)
def redirect_v1_openapi():
    return RedirectResponse(url="/openapi.json")


@app.get("/", include_in_schema=False)
def root_redirect():
    return {
        "message": f"Welcome to {settings.PROJECT_NAME}",
        "documentation": "/docs",
        "health": f"{settings.API_V1_PREFIX}/health",
    }
