"""FastAPI application entry-point."""

from fastapi import FastAPI

from app.api.health import router as health_router
from app.core.config import settings

app = FastAPI(title=settings.app_name, debug=settings.debug)

app.include_router(health_router, tags=["health"])
