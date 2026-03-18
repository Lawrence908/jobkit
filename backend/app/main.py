"""JobKit FastAPI application."""
import logging
from contextlib import asynccontextmanager

import jwt
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.auth import _decode_supabase_jwt
from app.core.config import get_settings
from app.core.logging import setup_logging
from app.db.session import get_engine, get_session_factory, init_db
from app.api.routes_auth import router as auth_router
from app.api.routes_register import router as register_router
from app.api.routes_admin import router as admin_router
from app.api.routes_status import router as status_router
from app.api.routes_jobs import router as jobs_router
from app.api.routes_interview_prep import router as interview_prep_router
from app.api.routes_truth_store import router as truth_store_router
from app.api.routes_generate import router as generate_router
from app.api.routes_stats import router as stats_router
from app.api.routes_google import router as google_router
from app.api.routes_profile import router as profile_router
from app.api.routes_resume import router as resume_router
from app.api.routes_skills import router as skills_router
from app.api.routes_projects import router as projects_router
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

@app.middleware("http")
async def demo_write_guard(request: Request, call_next):
    """Block mutating requests from the demo user (read-only account)."""
    s = get_settings()
    if (
        s.demo_user_id
        and request.method in ("POST", "PUT", "PATCH", "DELETE")
        and not request.url.path.startswith("/api/auth/")
    ):
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            try:
                payload = _decode_supabase_jwt(auth_header[7:], s)
                if payload.get("sub") == s.demo_user_id:
                    return JSONResponse(
                        status_code=403,
                        content={"detail": "Demo account is read-only"},
                    )
            except (jwt.InvalidTokenError, Exception):
                pass
    return await call_next(request)


app.include_router(status_router)
app.include_router(auth_router)
app.include_router(register_router)
app.include_router(admin_router)
app.include_router(jobs_router)
app.include_router(interview_prep_router)
app.include_router(truth_store_router)
app.include_router(generate_router)
app.include_router(stats_router)
app.include_router(google_router)
app.include_router(profile_router)
app.include_router(resume_router)
app.include_router(skills_router)
app.include_router(projects_router)
