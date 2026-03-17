# JobKit

Self-hosted web app for scraping job descriptions, tailoring resumes with an LLM, rendering PDFs, uploading to Google Drive, and logging to Google Sheets. Private (single-user), runs at `jobs.chrislawrence.ca`.

## Features

- **Job ingestion**: Paste a job URL or raw description; store as markdown + JSON.
- **Truth store**: Master resume, skills, and projects in `data/resume_base.yml`, `data/skills.yml`, and `data/projects/*.yml`.
- **Tailoring**: Heuristic match + LLM refinement to generate resume, cover letter, and notes (no hallucinated facts).
- **PDF**: WeasyPrint renders Markdown → PDF with a clean template.
- **Google**: OAuth for Drive + Sheets; upload artifacts and append/update a tracker row.

## Tech stack

- **Backend**: FastAPI, SQLAlchemy (SQLite), Pydantic.
- **Frontend**: React, Vite, TypeScript, Mantine.
- **Deploy**: Docker Compose; Caddy reverse proxy.

## Local development

1. Copy `.env.example` to `.env` and set at least `ADMIN_USERNAME`, `ADMIN_PASSWORD`, `SESSION_SECRET`. For LLM generation set `LLM_API_KEY` (and optionally `LLM_BASE_URL` for a different endpoint).
2. Backend (from repo root):
   ```bash
   cd backend
   python3 -m venv .venv
   .venv/bin/pip install -r requirements.txt
   JOBKIT_DATA_DIR=./data JOBKIT_JOBS_DIR=./jobs JOBKIT_OUTPUTS_DIR=./outputs .venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```
3. Frontend (from repo root):
   ```bash
   cd frontend
   npm install
   npm run dev
   ```
   Vite proxies `/api` to the backend (see `vite.config.ts`).
4. Open http://localhost:3000 and log in with your admin credentials.

## Production deploy

1. In the repo root, create `.env` from `.env.example` and set all secrets (including `GOOGLE_*` if using Drive/Sheets).
2. Ensure `data/`, `jobs/`, and `outputs/` exist (or will be created by compose).
3. From the homelab infra repo, Caddy is already configured for `jobs.chrislawrence.ca` (see `proxy/Caddyfile`). Ensure the JobKit Caddy block is present.
4. Run (from `~/apps/jobkit`):
   ```bash
   docker compose -f compose.yaml up -d --build
   ```
5. Add Cloudflare Tunnel route for `jobs.chrislawrence.ca` → `http://caddy:80` and an Access application with your desired policy (e.g. Admin).

## Google OAuth and Drive/Sheets setup

**Quick steps:** Create an OAuth 2.0 Web client in [Google Cloud Console](https://console.cloud.google.com/), set redirect URI to `https://jobs.chrislawrence.ca/api/google/oauth/callback`, put Client ID and Secret in `.env`, generate and set `GOOGLE_TOKEN_ENCRYPTION_KEY`, then in the app click **Connect Google** in the header to authorize.

For full instructions (OAuth consent screen, APIs, Drive folder ID, Sheets spreadsheet/tab/column), see **[docs/GOOGLE_SETUP.md](docs/GOOGLE_SETUP.md)**.

## Environment variables

See `.env.example` for the full list. Required for basic run: `SESSION_SECRET`, `ADMIN_USERNAME`, `ADMIN_PASSWORD`. For generation: `LLM_API_KEY`. For Drive/Sheets: all `GOOGLE_*` variables.

## Supabase / database migrations

Use the **backend venv** and **requirements.txt** for Alembic and the data migration script. Do not use system-installed `alembic` or `python3-alembic` (they pull in old SQLAlchemy 1.x and break the app).

From repo root (`.env` can live in repo root or in `backend/`):

```bash
cd backend
python3 -m venv .venv   # if you don't have it yet
source .venv/bin/activate
pip install -r requirements.txt
```

Then create tables on Supabase and optionally copy data from SQLite:

```bash
# 1. Create tables (DATABASE_URL in .env must point at Supabase)
alembic upgrade head

# 2. One-time: copy existing SQLite data into Supabase (default: data/jobkit.db)
python scripts/migrate_sqlite_to_postgres.py
# Or: python scripts/migrate_sqlite_to_postgres.py /path/to/jobkit.db
```

## Data and reference material

JobKit uses **YAML** for tailoring so it can do heuristic project matching and pass structured data to the LLM. The app loads:

| File / folder | Purpose |
|---------------|--------|
| `data/profile.yml` | Name, email, phone, LinkedIn, default tone/length/focus, **pitch** (used in cover letters). |
| `data/resume_base.yml` | Contact, summary, highlights, technical snapshot, experience, education, certifications. |
| `data/skills.yml` | Categorized or flat skills; used for keyword matching and to align resume/cover letter wording with the job. |
| `data/projects/*.yml` | One project per file (or one file with a list). Each: `name`, `description`, `tags`, `tech_stack`, `bullets`, optional `dates`/`link`/`status`. |

The markdown files in `data/projects/` (`resume.md`, `skills.md`, `coursework.md`, `homelab.md`, `portfolio.md`) are **reference sources**. Edit them for narrative and detail; then update the corresponding YAML so JobKit stays in sync. Optional: add a small script or manual step to re-export from markdown → YAML when you change the reference docs.

**Customization tips:**

- **Resume/cover letter tone**: Set `default_tone` and `default_focus` in `profile.yml`; override per job in the UI if needed.
- **Cover letter**: The **pitch** in `profile.yml` is injected where appropriate; keep it to one or two sentences.
- **ATS**: If ingest extracts action verbs and key phrases into the job's `ats` field, the tailor uses them to phrase bullets (without inventing facts).
- **Projects**: More projects in `data/projects/*.yml` give the tailor more to choose from; scoring picks the most relevant by tags/tech_stack vs job keywords.
- **Coursework**: Use a project like `coursework.yml` for roles that value C/C++, data structures, or academic foundations so it can be selected when relevant.

## Demo mode

Without Google connected, you can still add jobs, run tailoring (if LLM is configured), and render PDFs; artifacts stay local. The “Upload + Log” action will prompt to connect Google first.
