"""Pytest fixtures for the exemplar-library tests.

These tests are hermetic: each points JOBKIT_DATA_DIR at a temp dir with its own exemplars/
subdir, so they never touch the real seed library (one optional test does, guarded by a skip).
"""
import sys
from pathlib import Path

import pytest

# Make the `app` package importable no matter where pytest is invoked from.
BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

REPO_ROOT = BACKEND_DIR.parent
SEED_EXEMPLAR_DIR = REPO_ROOT / "archive" / "data" / "exemplars"


@pytest.fixture
def exemplar_dir(tmp_path, monkeypatch):
    """Create an empty temp exemplars/ dir and point JOBKIT_* env at the temp tree.

    Returns the exemplars dir so a test can drop fixture YAML files in before reloading.
    """
    data_dir = tmp_path / "data"
    ex_dir = data_dir / "exemplars"
    ex_dir.mkdir(parents=True)
    monkeypatch.setenv("JOBKIT_DATA_DIR", str(data_dir))
    monkeypatch.setenv("JOBKIT_JOBS_DIR", str(tmp_path / "jobs"))
    monkeypatch.setenv("JOBKIT_OUTPUTS_DIR", str(tmp_path / "outputs"))
    return ex_dir
