"""Scheduled jobs registration."""
from apscheduler.schedulers.background import BackgroundScheduler

from app.config import get_settings


def pull_market_data_job() -> None:
    """Placeholder scheduled job for pulling market data.

    TODO: wire real data ingestion pipeline and persistence.
    """
    print("[scheduler] pull_market_data_job executed")


def build_scheduler() -> BackgroundScheduler:
    """Create scheduler with placeholder jobs."""
    settings = get_settings()
    scheduler = BackgroundScheduler(timezone=settings.scheduler_timezone)
    scheduler.add_job(pull_market_data_job, "interval", minutes=30, id="pull_market_data_job", replace_existing=True)
    return scheduler
