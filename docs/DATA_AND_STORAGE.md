# JobKit — Data and Storage

Use this doc when prompting for backups, migration, or moving to cloud DB/storage (e.g. Supabase).

---

## What lives where

### SQLite database

- **Path**: `{JOBKIT_DATA_DIR}/jobkit.db` (default in Docker: `/app/data/jobkit.db`; on host: `./data/jobkit.db`).
- **Created**: On first run via `Base.metadata.create_all(bind=engine)`; no separate migrations yet.

**Tables:**

| Table          | Purpose |
|----------------|---------|
| `jobs`         | One row per job: id, url, company, role, location, status, slug, keywords_json, source, created_at, updated_at. |
| `artifacts`    | One row per generated file: id, job_id, type (e.g. resume_pdf, cover_letter_pdf), path (relative or absolute), drive_file_id, drive_link, created_at. |
| `google_tokens`| Single row (provider='google'): encrypted_refresh_token, scopes, created_at, updated_at. |

- **Concurrency**: SQLite with `check_same_thread=False`; single process. No WAL or connection pooling in current setup.

---

### File system (directories)

| Directory / path        | Env / default     | Purpose |
|-------------------------|-------------------|---------|
| `data/`                 | `JOBKIT_DATA_DIR` | `jobkit.db`, `profile.yml`, `resume_base.yml`, `skills.yml`, `projects/*.yml`, **`avatars/<user-id>.jpg`** (optional profile photos for the dashboard only). |
| `jobs/`                 | `JOBKIT_JOBS_DIR` | Per-job folders `jobs/<slug>/`: `job.json`, `description.md`, `generated/resume.md`, `cover_letter.md`, `notes.md`, and rendered PDFs. |
| `outputs/`              | `JOBKIT_OUTPUTS_DIR` | Optional alternate root for rendered PDFs (configurable in render path logic). |

- **Truth store**: All under `data/` — YAML only; loaded at startup and on explicit reload; not in SQLite.
- **Job content**: Metadata in DB; body and generated content on disk under `jobs/<slug>/`.
- **Artifacts**: DB row points to file via `path`; file lives under `jobs/<slug>/generated/` or `outputs/`.

---

### Google (external)

- **Drive**: Uploaded PDFs (and optionally other files); folder per job; IDs and links stored in `artifacts.drive_file_id` and `artifacts.drive_link`.
- **Sheets**: Tracker spreadsheet; row keyed by Job URL; deletes remove that row from the sheet; no copy of sheet data in JobKit DB.

---

## Volume layout in Docker

```yaml
volumes:
  - ./data:/app/data
  - ./jobs:/app/jobs
  - ./outputs:/app/outputs
```

- Only `jobkit-api` mounts these; frontend is stateless.
- If you lose `./data`, you lose: DB (jobs, artifacts, Google token), profile, resume_base, skills, projects YAML, and uploaded profile avatars under `data/avatars/`.
- If you lose `./jobs`, you lose: job descriptions and all generated markdown/PDFs (metadata remains in DB but paths may point to missing files).
- `./outputs` is optional and may duplicate or supplement PDFs under `jobs/<slug>/`.

---

## Backup implications

- **Critical**: `data/` (DB + YAML) and `jobs/` (job content + generated docs).
- **Recoverable from Google**: Drive has uploaded PDFs; Sheets has application log; reconnecting OAuth restores “Connect Google” but not the encrypted token (user re-authorizes).
- **Not stored in JobKit**: LLM API keys, Google OAuth client secret; those are in `.env` only.

---

## Reference for “database upgrade” planning

- **In DB**: Jobs (metadata), Artifacts (paths + Drive refs), Google token (encrypted).
- **On disk only**: Job bodies and generated markdown/PDFs; truth store YAML; profile YAML.
- Moving to a cloud DB (e.g. Supabase) would replace SQLite for those three tables; file storage could stay local, move to Supabase Storage, or another object store — see DATABASE_UPGRADE_SUPABASE.md.
