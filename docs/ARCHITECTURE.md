# JobKit — Architecture

Use this doc when prompting for refactors, new services, deployment, or integration work.

---

## High-level diagram

```
[Browser] ←→ [Caddy] ←→ [jobkit-frontend :3000]  (React/Vite)
                  ↓
            [jobkit-api :8000]  (FastAPI)
                  ↓
    ┌─────────────┼─────────────┐
    ↓             ↓             ↓
 SQLite      data/ (YAML)   jobs/ + outputs/ (files)
 jobkit.db   truth store    job content + PDFs
```

- **Production**: Caddy reverse-proxies `jobs.chrislawrence.ca` to frontend; frontend calls backend at `/api` (same origin via proxy).
- **Docker**: Two services — `jobkit-api`, `jobkit-frontend`; shared network `homelab-web`. With Supabase: Postgres and Storage are remote; job/generated content is read from Storage only (no disk fallback). Without Supabase: SQLite + dirs are host/volume-mounted (see ROADMAP.md for deployment modes).

---

## Backend (FastAPI)

- **Entry**: `backend/app/main.py` — lifespan creates dirs, inits DB engine, runs migrations (create_all), loads truth store.
- **Config**: `app/core/config.py` — Pydantic Settings from `.env`; paths, Google, LLM, session.
- **Auth**: `app/core/auth.py` — session cookie, CSRF; single admin (username/password from env).
- **DB**: SQLAlchemy 2.x; engine from `sqlite:///{jobkit_data_dir}/jobkit.db`; sync session factory; `get_db()` dependency.
- **Models**: `app/db/models.py` — `Job`, `Artifact`, `GoogleToken` (see DATA_AND_STORAGE.md).

### API routers (prefix / tags)

| Prefix            | Tag          | Purpose |
|-------------------|--------------|---------|
| `/api` (status)   | -            | Health, etc. |
| `/api/auth`       | auth         | Login, me, logout, CSRF token |
| `/api/jobs`       | jobs         | CRUD jobs, description, delete |
| `/api/jobs`       | generate     | Generate, tailor-preview, render PDFs, list/download artifacts, upload-and-log |
| `/api/truth-store`| truth-store  | Status, reload YAML |
| `/api/profile`    | profile      | Get/put profile (profile.yml) |
| `/api/google`     | google       | OAuth start/callback, connection status |

### Key services

- **ingest** — URL fetch or paste → job JSON + slug; writes `job.json` and `description.md` under `jobs/<slug>/`.
- **extract** — Keywords and ATS signals from job text.
- **truth_store** — Load/resume_base/projects/skills from YAML; in-memory cache.
- **profile_store** — Read/write `data/profile.yml`.
- **tailor** — Project selection + LLM generation; writes `jobs/<slug>/generated/*.md`.
- **render** — WeasyPrint Markdown → PDF; writes to job generated dir or outputs dir.
- **google_auth** — OAuth flow; encrypt/decrypt refresh token; get credentials for Drive/Sheets.
- **google_drive** — Upload file, ensure folder.
- **google_sheets** — Column map, find/append/update row by Job URL.

---

## Frontend (React + Vite + TypeScript)

- **Stack**: React, React Router, Vite, Mantine UI.
- **API**: `src/api/client.ts` — fetch to same origin with credentials; `src/api/types.ts` for types.
- **Routes**: See FEATURES.md (Login, Dashboard, New Job, Job Detail, Profile, Tracker).
- **Proxy**: In dev, Vite proxies `/api` to backend (e.g. port 8000); see `vite.config.ts`.

---

## Docker (compose)

- **File**: `compose.yaml` at repo root.
- **Services**:
  - `jobkit-api`: build `./backend`, port 8122→8000, env_file `.env`, volumes `./data`, `./jobs`, `./outputs`.
  - `jobkit-frontend`: build `./frontend`, port 8123→3000.
- **Network**: `homelab-web` (external). Caddy (not in this compose) fronts both; JobKit blocks live in homelab proxy config.
- **Persistence**: All persistent state is in mounted dirs and SQLite inside `./data`; no database container.

---

## Data flow (summary)

1. **Job creation**: Request → ingest service → Job row + `jobs/<slug>/` files.
2. **Tailoring**: Job + truth store + profile → tailor → `jobs/<slug>/generated/*.md`.
3. **PDF**: Generated markdown → render → PDFs on disk; Artifact rows with `path`.
4. **Upload + Log**: Render if needed → Drive upload (update Artifact with drive_file_id/drive_link) → Sheets sync by Job URL.

---

## Dependencies for prompting

- **Backend**: FastAPI, SQLAlchemy, Pydantic, httpx, WeasyPrint, PyYAML, etc. (see `backend/requirements.txt`).
- **Frontend**: React, Mantine, React Router (see `frontend/package.json`).
- **Deploy**: Docker Compose; Caddy and Cloudflare Tunnel are in homelab infra, not in this repo.
