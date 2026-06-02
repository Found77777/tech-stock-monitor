"""FastAPI application entrypoint."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.api.agent_routes import router as agent_router
from app.config import get_settings
from app.scheduler.jobs import build_scheduler
from app.review.routes import router as review_router

settings = get_settings()
app = FastAPI(title=settings.app_name)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "http://127.0.0.1:3000", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)
app.include_router(agent_router, prefix="/agent", tags=["agent"])
app.include_router(review_router)

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
