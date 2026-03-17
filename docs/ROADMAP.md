# JobKit — Roadmap and deployment

Use this doc when planning releases, hosting, or self-hosted vs managed backend.

---

## Deployment modes

### Current: Supabase (recommended for personal → small group)

- **Database**: Postgres on Supabase (e.g. Canada region for data residency).
- **Storage**: Supabase Storage bucket `jobkit-artifacts` for job JSON, markdown, and PDFs. When `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` are set, the app reads and writes job/generated content **only from Storage** (no disk fallback). Fast and consistent.
- **Auth**: Supabase Auth (or legacy session); invite codes for friends.
- **Hosting**: You run `jobkit-api` and `jobkit-frontend` (Docker or direct); they talk to Supabase. Good for: you, friends, Discord group; Canada-hosted DB and storage.

### Future: Self-hosted (optional for Reddit/public)

- **Database**: Local Postgres container (or external Postgres). Same schema (Alembic migrations).
- **Storage**: Either local dirs (`JOBKIT_JOBS_DIR`, `JOBKIT_OUTPUTS_DIR`) with disk-only reads, or an S3-compatible backend (e.g. MinIO) if you add an adapter. No Supabase Storage in this mode.
- **Auth**: Session or JWT; invite codes or open signup depending on goal.
- Use case: “run JobKit yourself” for Reddit/public; single `docker compose` with API + frontend + Postgres (and optionally local or S3 storage).

---

## Release stages

| Stage        | Audience   | Hosting / data                         |
|--------------|------------|----------------------------------------|
| Personal     | You        | Supabase (Canada) + your Docker/host  |
| Friends      | Invitees   | Same project; invite codes             |
| Discord      | Small group| Same; optional Discord OAuth later    |
| Reddit       | Wider      | Same or add self-hosted option        |
| Public       | Open       | Hosted app and/or self-hosted image   |

Recommendation: **Keep Supabase as the primary backend** for personal → Discord (one project, good data rights, local region). Add a **self-hosted variant** when you target Reddit/public (compose with Postgres + optional local/S3 storage).

---

## Data flow (Supabase mode)

1. **Job creation**: Ingest → Job row in Postgres; job JSON/md written to Supabase Storage at `{user_id}/jobs/{slug}/`.
2. **Generate**: Tailor reads job from Storage; writes resume/cover/notes to Storage at `{user_id}/jobs/{slug}/generated/`.
3. **Render**: PDFs uploaded to same `generated/` prefix; Artifact rows store storage key path.
4. **List/detail**: API loads job.json and “has generated” from Storage only (no disk). Fast and predictable.

When Storage is not configured (e.g. future self-hosted), the app uses `JOBKIT_JOBS_DIR` and `JOBKIT_OUTPUTS_DIR` for reads/writes instead.
