# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

JobKit is a self-hosted (now multi-user via Supabase Auth) web app for ingesting job postings, tailoring a resume + cover letter via an LLM, rendering PDFs, and optionally syncing to Google Drive/Sheets. Two services: FastAPI backend (`backend/`) and React/Vite/Mantine frontend (`frontend/`).

For the canonical architecture, feature scope, and storage model, read these first when scope warrants:
- `docs/ARCHITECTURE.md` — services, routers, request flow.
- `docs/FEATURES.md` — feature inventory and UI routes.
- `docs/DATA_AND_STORAGE.md` — what lives in DB vs disk vs Supabase Storage vs Google.
- `docs/DATABASE_UPGRADE_SUPABASE.md` — Postgres/Supabase migration notes and RLS posture.
- `docs/ROADMAP.md` — Supabase-mode vs self-hosted deployment modes.
- `docs/GOOGLE_SETUP.md` — OAuth client + Drive/Sheets configuration.

The README is the user-facing quickstart; the docs above are the source of truth for design decisions.

## Commands

### Backend (from `backend/`)
- `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt` — set up venv. **Always use this venv for `alembic` and `python` invocations**; system `alembic` / `python3-alembic` pull SQLAlchemy 1.x and break the app.
- `JOBKIT_DATA_DIR=./data JOBKIT_JOBS_DIR=./jobs JOBKIT_OUTPUTS_DIR=./outputs .venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000` — run dev server. The repo-root `.env` is auto-loaded (config looks at `.env` and `../.env`).
- `alembic upgrade head` — apply migrations. Required when `DATABASE_URL` is set (Postgres/Supabase). On SQLite, the app uses `Base.metadata.create_all` at startup and migrations are not strictly required, but Alembic is the source of truth for schema.
- `alembic revision -m "msg" --autogenerate` — new migration after model changes.
- `python scripts/migrate_sqlite_to_postgres.py [path/to/jobkit.db]` — one-shot SQLite → Postgres copy.
- Other `scripts/*.py` are operational backfills (artifact paths, user_id, storage uploads, demo user setup) — read the script before running; many require Supabase env vars.
- No formal test suite or linter is configured; do not invent commands for them.

### Frontend (from `frontend/`)
- `npm install`
- `npm run dev` — Vite on port 3000; `/api` is proxied to `http://localhost:8000` (see `vite.config.ts`).
- `npm run build` — runs `tsc -b` then `vite build`. Use this to type-check.
- `npm run preview` — serve the built `dist/`.

### Docker
- `docker compose up -d --build` from repo root. `jobkit-api` exposes 8122→8000, `jobkit-frontend` exposes 8123→3000, both on the external `homelab-web` network (Caddy in the homelab proxy fronts both — not in this repo).
- Volumes are only mounted on `jobkit-api`: `./data`, `./jobs`, `./outputs`. Frontend is stateless. The entrypoint `chown`s these dirs to `appuser` on each start.

## Architecture notes that are not obvious from the tree

### Storage backend is mode-dependent
- **Supabase mode** (`SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY` set): job content and generated artifacts are read/written **only** from Supabase Storage bucket `jobkit-artifacts` at `{user_id}/jobs/{slug}/...`. There is no disk fallback in this mode. `services/storage.py` is the abstraction.
- **Local mode** (Supabase env unset): same code falls back to `JOBKIT_JOBS_DIR` / `JOBKIT_OUTPUTS_DIR` on disk.
- The DB follows a separate switch: `DATABASE_URL` (or the `DATABASE_HOST/USER/PASSWORD/...` components, which `config.py` assembles with `quote_plus` on the password) → Postgres; otherwise SQLite at `{JOBKIT_DATA_DIR}/jobkit.db`.

### Auth is layered, not single-mode
- Primary auth is **Supabase Auth** (JWT in `Authorization: Bearer ...`); the frontend uses `@supabase/supabase-js` directly for login/signup and attaches the JWT to API calls.
- Legacy single-admin cookie+CSRF session auth (`ADMIN_USERNAME`/`ADMIN_PASSWORD`/`SESSION_SECRET`) still exists in `core/auth.py` and is referenced as backward compat — slated for removal per `.env.example`. Don't add new dependencies on it.
- `ADMIN_USER_ID` is the Supabase user UUID granted application-admin powers (invite codes, admin routes). It is **not** a Postgres role. RLS is enabled on all `public` tables (migration `012`) but **no policies are defined**, intentionally — all data access flows through FastAPI using the `postgres` superuser connection (which bypasses RLS). Don't query tables from the frontend with the anon key expecting them to work.
- Demo account: `DEMO_USER_ID` is enforced read-only by a middleware in `main.py` that 403s any non-`/api/auth/*` mutating request from that user.

### Truth store is YAML loaded at startup
`services/truth_store.py` loads `data/resume_base.yml`, `data/skills.yml`, `data/projects/*.yml` into an in-memory cache at lifespan startup. Changes to these files are not picked up until reload via `/api/truth-store/reload` or process restart. `data/profile.yml` is a separate store edited via `/api/profile`. The markdown files under `data/projects/` are human reference, not loaded by the app.

### LLM is OpenAI-compatible
`services/llm_provider.py` talks to whatever `LLM_BASE_URL` points at. `.env.example` defaults to OpenRouter (`anthropic/claude-sonnet-4.7`); `config.py` defaults to OpenAI. There's no separate Anthropic SDK path.

### Routers
Routers live in `app/api/routes_*.py` (note: `docs/ARCHITECTURE.md` describes them as `app/routers/` — the actual location is `app/api/`). All are registered in `main.py`. The set has grown beyond what `ARCHITECTURE.md` lists: `routes_admin`, `routes_register`, `routes_resume`, `routes_skills`, `routes_projects`, `routes_stats`, `routes_interview_prep` are also active. If you're updating architecture docs, sync them.

### CORS allow-list is hardcoded for the homelab
`main.py` hardcodes localhost, daedalus LAN/Tailscale, and the Caddy `APP_URL` as allowed origins. Use `CORS_EXTRA_ORIGINS` (comma-separated) instead of editing the list when adding a new dev host.

## Conventions

- **No emdashes** in generated text or code comments (per repo-level instruction in `/mnt/CLAUDE.md`). Use commas, semicolons, colons, or restructure.
- **Python**: 3.12, SQLAlchemy 2.x sync sessions via `get_db()`, Pydantic v2 settings. `from __future__ import annotations` is not used uniformly — match the surrounding file.
- **Frontend**: TypeScript strict via `tsc -b`. Mantine v7 components + `@tabler/icons-react`. API calls go through `src/api/client.ts` which attaches the Supabase JWT and uses same-origin `/api`.
- **Migrations**: Numbered prefix (`NNN_short_name.py`) under `backend/alembic/versions/`; keep the existing convention.
