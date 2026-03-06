"""JobKit FastAPI application."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.logging import setup_logging
from app.db.session import get_engine, get_session_factory, init_db
from app.api.routes_auth import router as auth_router
from app.api.routes_status import router as status_router
from app.api.routes_jobs import router as jobs_router
from app.api.routes_truth_store import router as truth_store_router
from app.api.routes_generate import router as generate_router
from app.api.routes_google import router as google_router
from app.api.routes_profile import router as profile_router
from app.services.truth_store import load_truth_store

setup_logging("INFO")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    settings.ensure_dirs()
    engine = get_engine()
    init_db(engine)
    get_session_factory(engine)
    load_truth_store()
    logger.info("JobKit backend started")
    yield
    engine.dispose()


app = FastAPI(title="JobKit", lifespan=lifespan)

settings = get_settings()
# CORS: app_url (Caddy), local/Tailscale direct ports, localhost dev
_cors_origins = [
    settings.app_url.rstrip("/"),
    "http://localhost:3000",
    "http://localhost:8123",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:8123",
    "http://192.168.50.128:8123",
    "http://daedalus.sunfish-prometheus.ts.net:8123",
]
if settings.cors_extra_origins:
    _cors_origins.extend(o.strip() for o in settings.cors_extra_origins.split(",") if o.strip())
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(status_router)
app.include_router(auth_router)
app.include_router(jobs_router)
app.include_router(truth_store_router)
app.include_router(generate_router)
app.include_router(google_router)
app.include_router(profile_router)
