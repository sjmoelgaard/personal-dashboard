import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler()


def setup_scheduler(sync_fn) -> AsyncIOScheduler:
    """Register scheduled jobs. sync_fn is an async callable."""
    scheduler.add_job(
        sync_fn,
        trigger=CronTrigger(hour=6, minute=0),
        id="daily_calendar_sync",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    return scheduler
