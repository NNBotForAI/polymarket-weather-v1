"""FastAPI application entry-point."""

import logging

from fastapi import FastAPI

from app.api.health import router as health_router
from app.core.config import settings

logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))
log = logging.getLogger(__name__)

app = FastAPI(title=settings.app_name, version="0.1.0")

app.include_router(health_router, tags=["health"])


@app.on_event("startup")
async def startup():
    log.info("%s starting — env=%s", settings.app_name, settings.app_env)


@app.on_event("shutdown")
async def shutdown():
    log.info("%s shutting down", settings.app_name)
