# JobKit — Exemplar Library: implementation handoff

**Status:** approved plan, not yet implemented. Selection/injection/promote pipeline
still needs to be built. Two seed exemplars are already converted and in place.

**How to use this file:** open a Claude Code CLI session in `/mnt/storage/apps/jobkit`
and implement the plan below. Everything needed is self-contained here. Read
`CLAUDE.md` first for repo conventions (no em dashes, venv rules, migration naming,
storage modes).

---

## Current state (verified 2026-05-22)

- `archive/data/exemplars/` exists and is mounted into the API container at
  `/app/data/exemplars` via the existing `./archive/data:/app/data` volume in
  `compose.yaml` (line 22). **No compose change is required.**
- **Nothing in the codebase references "exemplar" yet.** Full-repo grep returns zero hits.
  The folder was a stub created earlier; the feature was never written.
- Seed content **already converted to the loader format** and present:
  - `archive/data/exemplars/brentwood-senior-data-strategist-resume.yml`
  - `archive/data/exemplars/brentwood-senior-data-strategist-cover-letter.yml`
- Original Word uploads remain alongside them and are harmless (the loader globs
  `*.yml` only): `Chris_Lawrence_Resume_DataStrategist.docx`,
  `Chris_Lawrence_CoverLetter_DataStrategist.docx`. Delete once the YAML seeds are
  confirmed good.
- `archive/data/exemplars.md` is an empty 0-byte leftover stub; safe to delete.

## Decisions already locked (do not re-litigate)

1. **Storage = disk-backed, global, startup-loaded** — mirror `truth_store.py` exactly.
   Read `JOBKIT_DATA_DIR/exemplars/*.yml` into an in-memory cache at lifespan startup
   with a reload path. This is a curated *config* library like `resume_base.yml` /
   `skills.yml`, which are disk-only **even in Supabase mode**, so it is consistent in
   both modes. It is a single shared library across users (acceptable: form only, never
   content). If per-user scoping is wanted later, nest files under
   `exemplars/{user_id}/` — not in scope now.
2. **Selection metadata via LLM, with a heuristic fallback.** NOTE: `extract.py` is
   regex/heuristic only — there is **no** existing LLM extraction step to "reuse." So:
   add a small LLM classification call inside the generate (LLM) path that returns
   `{role_family, seniority, tags}` for the JD; when no API key is set (heuristic path),
   fall back to keyword-derived `role_family` + `tags = job keywords` so selection still
   works and degrades gracefully.
3. **Promote path = API endpoint + frontend button** (not CLI-only).

## Acceptance criteria (from the original spec)

- Output contains zero facts absent from the truth stores or JD (existing no-fabrication
  rule still holds; exemplars must never become a fabrication path).
- Output visibly matches exemplar conventions: no em dashes, consistent section order,
  comparable bullet density/length.
- A "promote to approved output -> exemplar" path exists (endpoint + button) that writes
  a YAML file with full frontmatter and reloads the library.
- Tests/checks: selection returns the right exemplar for a known JD; injection respects
  the max-2 cap; a no-fabrication spot-check passes on a sample run. (Repo has no test
  suite; add a `scripts/check_exemplars.py` smoke check matching the existing
  `scripts/*.py` convention, OR a small `backend/tests/` pytest suite — pick one and
  state it.)
- Empty / no-match library degrades to exactly current behaviour.

---

## Exemplar YAML schema (the seed files already follow this)

```yaml
id: <kebab-id>
doc_type: resume            # resume | cover_letter
role_family: data_ml        # devops_sre | platform | data_ml | ai_llm | backend | infra | other
seniority: senior           # mid | senior
target_role: "Senior Data Strategist"
jd_summary: |
  3-6 line distilled summary of the JD this doc was tailored to.
tags: [ai-governance, full-stack, training, purview-gap]
quality_notes: |
  What about this doc to imitate (form only).
body: |
  <final approved document text, exactly as sent>
```

`role_family` for the two seeds is `data_ml` (a judgment call: title is "Data Strategist"
but AI governance is heavy; retune to `ai_llm` if selection accuracy suggests it).

---

## Implementation plan (file by file)

### A. `backend/app/services/exemplar_store.py` (new)
Copy the structure of `backend/app/services/truth_store.py`:
- Module-level cache + `_loaded_at`; `load_exemplars()` parses every
  `JOBKIT_DATA_DIR/exemplars/*.yml` (frontmatter keys + `body`) into records.
- `get_exemplars() -> list[dict]`, `get_loaded_at()`.
- `score_exemplar(record, role_family, seniority, tags) -> int`: tag overlap x2,
  role_family exact +3 (same "family group" +1), seniority match +1.
- `select_exemplars(role_family, seniority, tags, doc_type, k=1, max_k=2) -> list[dict]`:
  filter by `doc_type`, sort by score desc, take top-K, hard cap 2, fall back to nearest
  role_family when no positive-score match, return `[]` when library is empty / no match.
- `write_exemplar(record: dict) -> Path`: write `exemplars/{id}.yml` then call
  `load_exemplars()` to refresh. Build `id` from slugified `target_role` + `doc_type`
  (+ short hash to avoid collisions).

### B. `backend/app/services/tailor.py` (edit)
- `classify_job_for_exemplars(job_json, _chat=None) -> dict`:
  - LLM available: one cheap JSON-only completion -> `{role_family, seniority, tags}`.
  - Fallback: map `job_json["keywords"]` + `role` text to a `role_family` via a small
    keyword->family table; `tags = keywords[:N]`; seniority from a regex on role/JD text.
- `_build_exemplar_block(exemplars) -> str`: emit the VERBATIM instruction block below,
  wrapping each selected doc in `<exemplar doc_type="..." target_role="...">` with its
  `jd_summary` and `body`. Return `""` when the list is empty.
- In `generate_artifacts` (the LLM branch only): classify -> select resume exemplars for
  the resume prompt and cover_letter exemplars for the cover prompt -> append the block
  AFTER the JSON `context_str`, clearly delimited. **Notes doc gets no exemplars.** Cap 2
  per doc. The heuristic path (`generate_artifacts_heuristic`) is unchanged.

### C. `backend/app/api/routes_jobs.py` (edit) — promote endpoint
- `POST /api/jobs/{job_id}/promote-exemplar`, CSRF-verified, owner-checked via
  `_get_user_job`. Body: `{doc_type, role_family, seniority, target_role, tags,
  quality_notes, jd_summary?}`. Read the approved `resume.md` / `cover_letter.md` via the
  existing storage-or-disk helpers (`storage_svc.download_generated_md` / disk fallback),
  build the record (default `jd_summary`/`tags` from the job + classification when
  omitted, `target_role` default from `job.role`), call `exemplar_store.write_exemplar`,
  return the saved record. Demo user is already 403'd by the middleware in `main.py`.

### D. `backend/app/main.py` (edit)
- Call `load_exemplars()` at lifespan startup next to `load_truth_store()`.
- Add a reload route (`POST /api/exemplars/reload`) or fold into the existing
  truth-store reload route. `write_exemplar` already reloads, so this is for manual edits.

### E. Frontend
- `frontend/src/components/ApplicationFlow.tsx`: add a "Promote to exemplar" button in the
  Resume and Cover-letter tab panels (next to the existing Save buttons), opening a small
  Mantine modal to confirm/edit frontmatter (doc_type prefilled, role_family/seniority
  selects, target_role/tags/quality_notes/jd_summary fields), then
  `api.post('/api/jobs/{id}/promote-exemplar', body)`.
- `frontend/src/api/types.ts`: add the request/response type. Type-check with
  `npm run build` (runs `tsc -b`).

### F. Docs (per CLAUDE.md "sync docs" guidance)
- `docs/DATA_AND_STORAGE.md`: add the `data/exemplars/` location and that it is disk-only
  in both modes.
- `docs/FEATURES.md`: add an "Exemplar library" feature note.

### G. Tests / checks
- `backend/scripts/check_exemplars.py` (matches existing `scripts/*.py` convention):
  load the seeds, assert selection returns the Brentwood resume for a data/AI-governance
  JD, assert `select_exemplars(..., max_k=2)` never returns >2, and run a sample generate
  (or a stubbed prompt assembly) asserting the injected block is present and separated
  from the truth JSON. Document how to run it in the script docstring.

---

## VERBATIM injection block (drop into the tailoring prompt exactly)

```
REFERENCE EXEMPLARS
The documents below are human-approved, high-quality tailored applications for
OTHER roles. Use them ONLY as demonstrations of form: section order and
headings, bullet structure and density, sentence voice and tone, length,
formatting conventions (no em dashes; plain hyphens for ranges), and how to
acknowledge skill gaps honestly and confidently.

Do NOT copy any content from the exemplars: no employers, project names,
metrics, phrasing, or skill claims. Every fact in the output must come solely
from the candidate's truth stores and the target job description. If an
exemplar references a tool or experience the truth stores do not contain, do
not carry it over.

Match the exemplars' voice and structure; source all substance from the
truth stores.

<exemplar doc_type="..." target_role="...">
JD it was tailored to: {{jd_summary}}
---
{{exemplar_body}}
</exemplar>
```

---

## Original task spec (for reference)

Add an "Exemplar Library" to JobKit's tailoring pipeline. Curated, human-approved tailored
documents act as FEW-SHOT EXEMPLARS that teach the model the target *form* (section order,
bullet density, voice/tone, length, formatting conventions, honest gap acknowledgement)
WITHOUT ever copying their content. On each new JD, automatically select the most relevant
exemplar(s) and inject them into the tailoring prompt as reference demonstrations.
Empty/no-match must degrade gracefully to current behaviour.

1. **Storage** — `data/exemplars/`, one file per approved doc (frontmatter + body) with
   `id, doc_type, role_family, seniority, target_role, jd_summary, tags, quality_notes` and
   the final approved `body`. `jd_summary` is included because a few-shot example is
   strongest when it shows the input->output mapping (this JD -> this doc).
2. **Selection** — score exemplars by tag/role overlap against the new JD's parsed metadata;
   top-K per doc_type (default K=1, hard max 2). Fall back to nearest role_family.
3. **Injection** — insert selected exemplars in a clearly delimited block, kept SEPARATE
   from the YAML truth stores so the model never confuses exemplar content with the
   candidate's real facts.
4. **Instruction block** — the verbatim block above.
5. **Guardrails** — no-fabrication rule still holds; visible convention match; promote path;
   tests for selection, the max-2 cap, and fabrication.
6. **Seed** — the two Brentwood docs (Senior Data Strategist resume + cover letter), already
   converted to YAML in `archive/data/exemplars/`.
