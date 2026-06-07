from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.router import router as core_router
from app.modules.calendar.router import router as calendar_router
from app.modules.calendar.admin_router import router as admin_router
from app.core.scheduler import setup_scheduler

logger = logging.getLogger(__name__)


async def run_calendar_sync():
    """Kører daglig sync af alle aktive kalender-kilder."""
    from app.core.database import AsyncSessionLocal
    from app.modules.calendar.service import sync_all_sources
    async with AsyncSessionLocal() as db:
        try:
            count = await sync_all_sources(db)
            logger.info(f"Daglig sync: {count} events total")
        except Exception as e:
            logger.error(f"Daglig sync fejlede: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = setup_scheduler(run_calendar_sync)
    scheduler.start()
    logger.info("Scheduler started")
    yield
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
app.include_router(admin_router, prefix="/api/admin")
