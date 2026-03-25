# JobKit — Database Upgrade: Supabase (Considerations)

Use this doc when planning a move from SQLite to a cloud database (e.g. Supabase) so you can run Docker without worrying about losing data. This is a **planning and scoping** doc; implement a full migration plan after locking scope.

---

## Goals (assumed)

- **Durability**: Job and artifact metadata (and Google token) live in a managed cloud DB, not only on the host/volume.
- **Containers**: Keep running API + frontend in Docker; DB is external so container restarts or volume loss don’t lose application data.
- **Optional**: Move generated files (PDFs, markdown) to cloud object storage so `jobs/` and `outputs/` are not single points of failure.

---

## What Supabase would replace today

| Current (SQLite)   | Supabase equivalent |
|--------------------|----------------------|
| `jobs` table       | PostgreSQL table `jobs` (same or similar schema). |
| `artifacts` table  | PostgreSQL table `artifacts` (path could become object URL or key). |
| `google_tokens`    | PostgreSQL table `google_tokens` (encrypted_refresh_token remains encrypted at rest; consider Supabase Vault or app-level encryption). |
| `jobkit.db` file   | No local DB file; connection string to Supabase (Postgres). |

- **Schema**: Supabase is Postgres; SQLite-specific types (e.g. `INTEGER` primary key, `JSON`) map to `BIGSERIAL`/`SERIAL` and `JSONB`. Dialect differences in SQLAlchemy are manageable (use `postgresql` driver and adjust types if needed).

---

## What stays file-based (unless you change it)

- **Truth store**: `data/resume_base.yml`, `data/skills.yml`, `data/projects/*.yml` — currently read from disk. Options: (1) keep as files and mount `data/` in Docker, (2) move to DB (new tables or JSON columns), (3) move to Supabase Storage and read at startup.
- **Profile**: `data/profile.yml` — same options as truth store.
- **Job content**: `jobs/<slug>/job.json`, `description.md`, `generated/*.md`, PDFs — today on disk. Options: (1) keep on volume, (2) move to Supabase Storage (or S3-compatible) and store object keys/URLs in `artifacts` and possibly extend `jobs` or a new table for “job body” location.

---

## Supabase pieces to use

1. **Database (Postgres)**  
   - Hosted Postgres; connection via connection string (direct or pooler).  
   - Use for: `jobs`, `artifacts`, `google_tokens`.  
   - **RLS**: Enabled on all public tables (migration `012_rls`). See [Row Level Security (RLS)](#row-level-security-rls) below.

2. **Auth (optional)**  
   - Supabase Auth can replace or sit alongside current session (username/password from env).  
   - If you keep single-admin, you might keep current cookie auth and only use Supabase for DB + Storage.

3. **Storage (optional)**  
   - Buckets for: (a) generated files (PDFs, markdown) per job, (b) optionally truth store YAML and profile.  
   - Replace `path` in `artifacts` with a storage path or public/signed URL; same for any “job body” storage.

4. **Secrets**  
   - Keep `SESSION_SECRET`, `GOOGLE_*`, `LLM_*` in `.env` (or inject from a secrets manager). Supabase project secrets are for Supabase-managed code (e.g. Edge Functions), not required for the FastAPI app.

---

## Code and config changes (high level)

- **Backend**  
  - **DB driver**: Switch from `sqlite` to `postgresql` (e.g. `asyncpg` or `psycopg2`); connection string from env (e.g. `DATABASE_URL` or `SUPABASE_DB_URL`).  
  - **SQLAlchemy**: Same models; use Postgres dialect (e.g. `JSONB` instead of SQLite `JSON`; `DateTime(timezone=True)` is fine).  
  - **Session**: If you stay sync, use same pattern with Postgres engine; no need to go async unless you want to.

- **Env**  
  - Add e.g. `DATABASE_URL=postgresql://...` (from Supabase project settings).  
  - Remove or ignore “create SQLite file” in config; keep `JOBKIT_DATA_DIR` if you still read YAML from disk.

- **Migrations**  
  - Introduce Alembic (or similar) so schema changes are repeatable on Postgres; initial migration can mirror current `create_all` schema.

- **File storage (if using Supabase Storage)**  
  - Replace direct filesystem writes under `jobs/` and `outputs/` with uploads to a bucket (e.g. `jobkit-artifacts`); path convention e.g. `jobs/<slug>/generated/resume.pdf`.  
  - Artifact `path` then stores object path or key; download URL from Supabase Storage (signed or public).  
  - Ingest and tailor services: write `job.json` and generated markdown to Storage instead of local disk, or keep a hybrid (e.g. local cache + Storage backup).

---

## Risks and decisions

- **Encrypted Google token**: Storing in Postgres is fine; keep encrypting with `GOOGLE_TOKEN_ENCRYPTION_KEY` before save. Consider Supabase Vault for the encryption key if you want it out of `.env`.
- **Truth store and profile**: If they stay on disk, ensure `data/` is backed up or replicated; if moved to DB or Storage, add a reload/refresh path so the app sees updates.
- **Cost and limits**: Supabase free tier has DB size and Storage limits; check current and projected usage.
- **Local dev**: Use a second Supabase project or local Postgres so dev doesn’t touch production data.

---

## Row Level Security (RLS)

**Roles (what Supabase means):**

| Role / connection | What it is |
|-------------------|------------|
| **`postgres`** (direct DB URL) | Superuser connection used by FastAPI + Alembic. **Bypasses RLS** — your app keeps working as before. |
| **`anon`** | PostgREST / Data API with the **anon** API key (no JWT). |
| **`authenticated`** | PostgREST with a logged-in user’s **JWT** (Supabase Auth). Your frontend only uses this for **Auth**, not for querying tables. |
| **Service role key** | Bypasses RLS for Supabase client APIs (Storage, etc.). Never expose in the browser. |

There is **no separate “admin” Postgres role** in JobKit. `ADMIN_USERNAME` / `ADMIN_PASSWORD` / `ADMIN_USER_ID` in `.env` are **application** admin (cookie + optional JWT check on the API), not a database role.

**What we did:** Migration `012_enable_row_level_security.py` turns on RLS for every JobKit table in `public`. We **do not** add policies for `anon` / `authenticated`, so the Supabase **Data API** cannot read or write those rows with the anon key or user JWTs. That clears Advisor “RLS disabled” warnings and matches the architecture (all data goes through FastAPI).

**If you later query tables from the client** (e.g. realtime or direct Supabase JS), add policies such as `user_id = auth.uid()::text` per table.

**Apply the migration** (against Supabase):

```bash
cd backend && alembic upgrade head
```

If Advisor still lists a table JobKit doesn’t own, enable RLS manually in the SQL Editor:  
`ALTER TABLE public.<table_name> ENABLE ROW LEVEL SECURITY;`

---

## Suggested order for a full plan

1. **Phase 1 — DB only**: Replace SQLite with Supabase Postgres; keep all file storage on current volumes. No Supabase Auth or Storage yet.  
2. **Phase 2 (optional)**: Move generated artifacts (and optionally job bodies) to Supabase Storage; update artifact paths and download logic.  
3. **Phase 3 (optional)**: Move truth store and profile into DB or Storage; adjust load/save and reload behavior.

Once this scope is fixed, you can create a detailed implementation plan (tasks, env matrix, migration steps, rollback).
