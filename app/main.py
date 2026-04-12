"""FastAPI application entry-point."""

import logging
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI

from app.api.health import router as health_router
from app.api.routes import router as api_router
from app.core.config import settings

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def _scheduled_scan():
    logger.info("Scheduled scan job triggered")
    try:
        from app.jobs import run_scan
        await run_scan()
    except Exception:
        logger.exception("Scheduled scan failed")


async def _scheduled_resolve():
    logger.info("Scheduled resolve job triggered")
    try:
        from app.jobs.resolve_job import run_resolve
        await run_resolve()
    except Exception:
        logger.exception("Scheduled resolve failed")


async def _scheduled_evaluate():
    logger.info("Scheduled evaluate job triggered")
    try:
        from app.jobs.evaluate_job import run_evaluate
        await run_evaluate()
    except Exception:
        logger.exception("Scheduled evaluate failed")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start scheduler
    scheduler.add_job(_scheduled_scan, "interval", hours=6, id="scan", replace_existing=True)
    scheduler.add_job(_scheduled_resolve, "interval", hours=12, id="resolve", replace_existing=True)
    scheduler.add_job(_scheduled_evaluate, "interval", hours=24, id="evaluate", replace_existing=True)
    scheduler.start()
    logger.info("Scheduler started")
    yield
    scheduler.shutdown()
    logger.info("Scheduler stopped")


app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    lifespan=lifespan,
)

app.include_router(health_router, tags=["health"])
app.include_router(api_router, prefix="/api/v1", tags=["api"])
