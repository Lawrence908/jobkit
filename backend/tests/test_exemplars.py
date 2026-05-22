"""Tests for the exemplar library: selection, the max-2 cap, graceful degradation, and the
no-fabrication-shaped injection block.

Run from backend/:
    .venv/bin/pip install -r requirements-dev.txt
    .venv/bin/python -m pytest tests/ -q

The selection/cap/empty-library tests are hermetic (temp dir + fixture YAML). One test exercises
the real seed library under archive/data/exemplars/ and is skipped if those files are absent.
A true end-to-end no-fabrication check needs a live LLM run; here we assert the structural
guardrail instead: the injected block keeps exemplars separate from the truth data and carries
the explicit "do not copy content" instruction.
"""
import textwrap

import pytest

from app.services import exemplar_store as es
from app.services import tailor
from tests.conftest import SEED_EXEMPLAR_DIR


def _write(ex_dir, name, content):
    (ex_dir / name).write_text(textwrap.dedent(content), encoding="utf-8")


_DATA_ML_RESUME = """\
    id: data-ml-resume
    doc_type: resume
    role_family: data_ml
    seniority: senior
    target_role: "Senior Data Strategist"
    jd_summary: |
      A data and AI governance role.
    tags: [ai-governance, data-strategy, full-stack, dashboards]
    quality_notes: |
      Imitate section order and two bullets per role.
    body: |
      Chris Lawrence
      PROFILE
      Data and AI resume body.
"""

_DATA_ML_COVER = """\
    id: data-ml-cover
    doc_type: cover_letter
    role_family: data_ml
    seniority: senior
    target_role: "Senior Data Strategist"
    jd_summary: |
      A data and AI governance role.
    tags: [ai-governance, data-strategy, honest-gap-handling]
    quality_notes: |
      Five-paragraph arc; honest gap handling.
    body: |
      Dear Hiring Committee,
      Cover letter body for data role.
"""

_AI_LLM_RESUME = """\
    id: ai-llm-resume
    doc_type: resume
    role_family: ai_llm
    seniority: senior
    target_role: "LLM Engineer"
    jd_summary: |
      An LLM/RAG engineering role.
    tags: [llm-orchestration, rag, prompt-engineering]
    quality_notes: |
      Dense projects section.
    body: |
      LLM engineer resume body.
"""

_BACKEND_RESUME = """\
    id: backend-resume
    doc_type: resume
    role_family: backend
    seniority: mid
    target_role: "Backend Engineer"
    jd_summary: |
      A backend API role.
    tags: [api-design, fastapi]
    quality_notes: |
      Concise one-pager.
    body: |
      Backend engineer resume body.
"""


def test_select_returns_best_resume_for_data_ai_jd(exemplar_dir):
    _write(exemplar_dir, "data_ml_resume.yml", _DATA_ML_RESUME)
    _write(exemplar_dir, "data_ml_cover.yml", _DATA_ML_COVER)
    _write(exemplar_dir, "ai_llm_resume.yml", _AI_LLM_RESUME)
    _write(exemplar_dir, "backend_resume.yml", _BACKEND_RESUME)
    es.load_exemplars()

    selected = es.select_exemplars(
        role_family="data_ml",
        seniority="senior",
        tags=["ai-governance", "data-strategy"],
        doc_type="resume",
    )
    assert selected, "expected a resume exemplar for a data/AI JD"
    assert selected[0]["id"] == "data-ml-resume"
    # doc_type filter holds: cover-letter exemplar must not appear in a resume selection.
    assert all(e["doc_type"] == "resume" for e in selected)


def test_doc_type_filter_selects_cover_letter(exemplar_dir):
    _write(exemplar_dir, "data_ml_resume.yml", _DATA_ML_RESUME)
    _write(exemplar_dir, "data_ml_cover.yml", _DATA_ML_COVER)
    es.load_exemplars()

    selected = es.select_exemplars("data_ml", "senior", ["ai-governance"], "cover_letter")
    assert [e["id"] for e in selected] == ["data-ml-cover"]


def test_max_two_cap_is_enforced(exemplar_dir):
    # Three positively-scoring resume exemplars; selection must never return more than 2.
    _write(exemplar_dir, "a.yml", _DATA_ML_RESUME.replace("data-ml-resume", "a-resume"))
    _write(exemplar_dir, "b.yml", _DATA_ML_RESUME.replace("data-ml-resume", "b-resume"))
    _write(exemplar_dir, "c.yml", _DATA_ML_RESUME.replace("data-ml-resume", "c-resume"))
    es.load_exemplars()

    selected = es.select_exemplars(
        "data_ml", "senior", ["ai-governance", "data-strategy"], "resume", k=5, max_k=5
    )
    assert len(selected) <= 2
    # Default k=1 returns a single exemplar.
    assert len(es.select_exemplars("data_ml", "senior", ["ai-governance"], "resume")) == 1


def test_empty_library_degrades(exemplar_dir):
    es.load_exemplars()  # dir exists but is empty
    assert es.get_exemplars() == []
    assert es.select_exemplars("data_ml", "senior", ["x"], "resume") == []
    assert tailor._build_exemplar_block([]) == ""


def test_no_match_returns_empty(exemplar_dir):
    # Only a data_ml resume exists; a backend JD with no tag overlap and a different family group
    # must select nothing rather than carry over an unrelated example.
    _write(exemplar_dir, "data_ml_resume.yml", _DATA_ML_RESUME)
    es.load_exemplars()
    assert es.select_exemplars("backend", "mid", ["nonexistent-tag"], "resume") == []


def test_nearest_family_fallback(exemplar_dir):
    # No positive score (tags don't overlap, role_family ai_llm vs data_ml) but same "data_ai"
    # family group, so the data_ml resume is a valid nearest-family fallback.
    _write(exemplar_dir, "data_ml_resume.yml", _DATA_ML_RESUME)
    es.load_exemplars()
    selected = es.select_exemplars("ai_llm", "mid", ["unrelated"], "resume")
    assert [e["id"] for e in selected] == ["data-ml-resume"]


def test_build_block_is_separated_and_no_copy(exemplar_dir):
    _write(exemplar_dir, "data_ml_resume.yml", _DATA_ML_RESUME)
    es.load_exemplars()
    selected = es.select_exemplars("data_ml", "senior", ["ai-governance"], "resume")
    block = tailor._build_exemplar_block(selected)

    # Verbatim header present, exemplar wrapped in tags, body carried.
    assert block.startswith("REFERENCE EXEMPLARS")
    assert '<exemplar doc_type="resume"' in block
    assert "</exemplar>" in block
    assert "Data and AI resume body." in block
    # No-fabrication guardrail text is present (the testable proxy for "exemplars never fabricate").
    assert "Do NOT copy any content from the exemplars" in block
    assert "Every fact in the output must come solely" in block
    # The block is example-form only: it must not contain the truth-store JSON wrapper.
    assert '"resume_base"' not in block


def test_classify_heuristic_no_llm():
    meta = tailor.classify_job_for_exemplars(
        {
            "role": "Senior Data Strategist",
            "keywords": ["analytics", "dashboard", "data-governance"],
            "raw_body": "AI governance, data strategy, and analytics dashboards.",
        }
    )
    assert meta["role_family"] in es.ROLE_FAMILIES
    assert meta["seniority"] == "senior"
    assert isinstance(meta["tags"], list) and meta["tags"]


def test_classify_llm_path_parses_json():
    def fake_chat(_msgs, **_kwargs):
        return '```json\n{"role_family": "backend", "seniority": "mid", "tags": ["api-design", "fastapi"]}\n```'

    meta = tailor.classify_job_for_exemplars(
        {"role": "Engineer", "keywords": [], "raw_body": "build APIs"}, _chat=fake_chat
    )
    assert meta == {"role_family": "backend", "seniority": "mid", "tags": ["api-design", "fastapi"]}


def test_classify_llm_garbage_falls_back():
    def bad_chat(_msgs, **_kwargs):
        return "not json at all"

    meta = tailor.classify_job_for_exemplars(
        {"role": "Senior Backend Engineer", "keywords": ["fastapi"], "raw_body": "microservices"},
        _chat=bad_chat,
    )
    assert meta["role_family"] in es.ROLE_FAMILIES
    assert meta["seniority"] in ("mid", "senior")


def test_write_exemplar_roundtrip(exemplar_dir):
    es.load_exemplars()
    assert es.get_exemplars() == []
    record = {
        "doc_type": "resume",
        "role_family": "ai_llm",
        "seniority": "senior",
        "target_role": "Staff AI Engineer",
        "jd_summary": "An AI platform role.",
        "tags": ["llm", "platform"],
        "quality_notes": "Imitate the projects section.",
        "body": "Resume body line one\nResume body line two",
    }
    path = es.write_exemplar(record)
    assert path.exists()
    assert path.name.startswith("staff-ai-engineer-resume-")

    # write_exemplar reloads the cache; the new record is present with all 9 keys.
    saved = next((e for e in es.get_exemplars() if e["id"] == path.stem), None)
    assert saved is not None
    for key in ("id", "doc_type", "role_family", "seniority", "target_role", "jd_summary",
                "tags", "quality_notes", "body"):
        assert key in saved
    assert saved["role_family"] == "ai_llm"
    assert saved["body"].splitlines()[0] == "Resume body line one"


@pytest.mark.skipif(
    not (SEED_EXEMPLAR_DIR.is_dir() and any(SEED_EXEMPLAR_DIR.glob("*.yml"))),
    reason="seed exemplars not present",
)
def test_real_seeds_select_brentwood(monkeypatch):
    monkeypatch.setenv("JOBKIT_DATA_DIR", str(SEED_EXEMPLAR_DIR.parent))
    es.load_exemplars()
    ids = {e["id"] for e in es.get_exemplars()}
    assert "brentwood-senior-data-strategist-resume" in ids

    resume = es.select_exemplars("data_ml", "senior", ["ai-governance", "full-stack"], "resume")
    assert resume and resume[0]["id"] == "brentwood-senior-data-strategist-resume"
    cover = es.select_exemplars("data_ml", "senior", ["ai-governance"], "cover_letter")
    assert cover and cover[0]["id"] == "brentwood-senior-data-strategist-cover-letter"
