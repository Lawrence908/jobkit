# JobKit

Self-hosted web app for scraping job descriptions, tailoring resumes with an LLM, rendering PDFs, uploading to Google Drive, and logging to Google Sheets. Private (single-user), runs at `jobs.chrislawrence.ca`.

## Features

- **Job ingestion**: Paste a job URL or raw description; store as markdown + JSON.
- **Truth store**: Master resume and projects in `data/resume_base.yml` and `data/projects/*.yml`.
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

## Demo mode

Without Google connected, you can still add jobs, run tailoring (if LLM is configured), and render PDFs; artifacts stay local. The “Upload + Log” action will prompt to connect Google first.
