# JobKit documentation

Docs for prompting and planning. Use these when asking for features, refactors, or migration plans.

| Doc | Use when |
|-----|----------|
| **[FEATURES.md](FEATURES.md)** | Scoping features, UX, or “what does the app do?” |
| **[ARCHITECTURE.md](ARCHITECTURE.md)** | Refactors, new services, deployment, or “how is it built?” |
| **[DATA_AND_STORAGE.md](DATA_AND_STORAGE.md)** | Backups, where data lives, migration scope |
| **[DATABASE_UPGRADE_SUPABASE.md](DATABASE_UPGRADE_SUPABASE.md)** | Planning a move from SQLite to Supabase (cloud DB, optional Storage) |
| **[GOOGLE_SETUP.md](GOOGLE_SETUP.md)** | Configuring Google OAuth, Drive, and Sheets |

---

## Quick reference for prompts

- **“Use the JobKit docs”** — point the model at this folder or at specific files above.
- **“Plan the Supabase migration”** — use FEATURES + ARCHITECTURE + DATA_AND_STORAGE + DATABASE_UPGRADE_SUPABASE.
- **“Add a new API/feature”** — use FEATURES + ARCHITECTURE.
