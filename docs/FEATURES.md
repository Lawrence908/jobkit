# JobKit — Feature Overview

Use this doc when prompting for feature work, UX changes, or scope decisions.

---

## Core Features

### Job ingestion
- **Input**: Paste a job URL or raw description text.
- **URL path**: Fetches the page, extracts title/company/body; stores as structured JSON + markdown.
- **Paste path**: Parses raw text into company, role, body; no fetch.
- **Storage**: Job record in SQLite (metadata); `jobs/<slug>/job.json` and `jobs/<slug>/description.md` on disk.
- **Output**: Job record with slug, company, role, location, status, keywords (extracted), source.

### Truth store (tailoring source of truth)
- **Location**: `data/` — YAML files loaded at startup and cached in memory.
- **Files**:
  - `data/profile.yml` — Name, email, phone, LinkedIn, default tone/length/focus, **pitch** (used in cover letters).
  - `data/resume_base.yml` — Contact, summary, highlights, technical snapshot, experience, education, certifications.
  - `data/skills.yml` — Categorized or flat skills; used for keyword matching and wording alignment.
  - `data/projects/*.yml` — One project per file (or list in one file). Fields: name, description, tags, tech_stack, bullets, optional dates/link/status.
- **API**: Read/update via `/api/truth-store/*` and `/api/profile`; profile can be edited in UI (Profile page); truth store is reloaded on demand or restart.
- **Reference docs**: Markdown in `data/projects/` (e.g. `resume.md`, `skills.md`, `portfolio.md`) are for human editing; YAML is the source for the app (optional sync step from markdown → YAML).

### Tailoring (LLM-assisted)
- **Input**: Job (from DB + `job.json` on disk), truth store (resume_base, projects, skills), profile (pitch, tone, focus).
- **Flow**: Heuristic project selection (score projects by tags/tech_stack vs job keywords) → LLM generates resume, cover letter, notes from structured context (no hallucinated facts).
- **Output**: Markdown files in `jobs/<slug>/generated/` (resume.md, cover_letter.md, notes.md); optionally ATS-oriented phrasing if job has extracted ATS signals.
- **Config**: Tone, focus, length overridable per job in UI; `LLM_*` env for model/temperature.

### PDF rendering
- **Engine**: WeasyPrint (Markdown → HTML → PDF).
- **Input**: Generated markdown (resume, cover letter) from `jobs/<slug>/generated/`.
- **Output**: PDFs written to `jobs/<slug>/generated/` or `outputs/`; Artifact records in DB with `path`; optional Drive upload stores `drive_file_id` and `drive_link`.

### Google integration
- **OAuth**: Connect Google once; refresh token stored encrypted in DB (`google_tokens` table).
- **Drive**: Upload resume/cover/notes PDFs (and markdown if desired) to a folder per job; root folder configurable via `GOOGLE_DRIVE_ROOT_FOLDER_ID` or auto-created “JobKit” folder.
- **Sheets**: Append or update a row keyed by Job URL; column mapping via env (company, role, status, date submitted, resume/cover/notes links, etc.). See `docs/GOOGLE_SETUP.md`.
- **Upload + Log**: Single action to render PDFs, upload to Drive, and sync row to Sheets.

### Authentication
- **Model**: Single-admin session auth (username/password from env); no multi-user.
- **Session**: Cookie-based; `SESSION_SECRET` for signing.
- **CSRF**: Verified on state-changing requests (e.g. create job, generate, update).

### Profile (UI)
- **Page**: `/profile` — edit profile (name, email, pitch, default tone/focus, etc.); persisted to `data/profile.yml`.

### Tracker / Spreadsheet view
- **Page**: `/tracker` — read-only view of the configured Google Sheet (job applications table).

---

## UI Structure

- **Login** — `/login`
- **Dashboard** — `/` — list jobs (cards), link to new job and job detail.
- **New job** — `/jobs/new` — paste URL or raw text, submit to ingest.
- **Job detail** — `/jobs/:jobId` — description, generated docs, tailor/generate, PDF download, Upload + Log.
- **Profile** — `/profile` — edit profile YAML-backed fields.
- **Spreadsheet** — `/tracker` — sheet data (when Google connected).

---

## Demo / limited mode

- Without Google: add jobs, run tailoring (if LLM configured), render PDFs; artifacts stay local.
- “Upload + Log” prompts to connect Google if not connected.

---

## Feature boundaries (for prompting)

- **Single user**: No multi-tenant or per-user data isolation.
- **No email/response tracking**: Sheet columns like “Rejection reason” or “Salary” are manual; no email parsing or auto-update (possible future).
- **Truth store**: File-based YAML; not in SQLite. Profile is editable in UI; resume_base/skills/projects are editable via API or file.
- **Artifacts**: Metadata in DB (Artifact table); file content on disk. Download and Drive links derived from `path` and `drive_file_id`/`drive_link`.
