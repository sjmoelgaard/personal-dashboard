from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.router import router as core_router
from app.modules.calendar.router import router as calendar_router
from app.core.scheduler import setup_scheduler

logger = logging.getLogger(__name__)


async def run_calendar_sync():
    """Wrapper that fetches DB session and runs sync."""
    from app.core.database import AsyncSessionLocal
    from app.modules.calendar.service import sync_calendar
    from app.core.config import settings
    if not settings.ical_url:
        return
    async with AsyncSessionLocal() as db:
        try:
            count = await sync_calendar(db, settings.ical_url)
            logger.info(f"Calendar sync: {count} events")
        except Exception as e:
            logger.error(f"Calendar sync failed: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    scheduler = setup_scheduler(run_calendar_sync)
    scheduler.start()
    logger.info("Scheduler started")
    yield
    # Shutdown
    scheduler.shutdown(wait=False)
    logger.info("Scheduler stopped")


app = FastAPI(title="Personal Dashboard", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(core_router, prefix="/api")
app.include_router(calendar_router, prefix="/api/calendar")
