"""FastAPI application entrypoint."""
from fastapi import FastAPI

from app.api.routes import router
from app.config import get_settings
from app.scheduler.jobs import build_scheduler

settings = get_settings()
app = FastAPI(title=settings.app_name)
app.include_router(router)

scheduler = build_scheduler()


@app.on_event("startup")
def on_startup() -> None:
    """Start background scheduler when API starts."""
    if not scheduler.running:
        scheduler.start()


@app.on_event("shutdown")
def on_shutdown() -> None:
    """Stop background scheduler when API shuts down."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
