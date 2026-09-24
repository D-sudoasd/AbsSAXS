"""JOSS homepage checks against the shipped README.md."""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
README_PATH = REPO_ROOT / "README.md"


def _load_readiness_checker():
    script = REPO_ROOT / "scripts" / "check_submission_readiness.py"
    spec = importlib.util.spec_from_file_location("check_submission_readiness", script)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load submission readiness checker from {script}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


readiness = _load_readiness_checker()


def _readme_text() -> str:
    return README_PATH.read_text(encoding="utf-8")


def test_shipped_readme_covers_joss_documentation_outcomes():
    readme = _readme_text()
    lowered = readme.lower()

    assert "absolute intensity" in lowered or "absolute-intensity" in lowered
    assert "beamline" in lowered
    assert "pyfai" in lowered
    assert "fabio" in lowered
    assert "sasview" in lowered
    assert "irena" in lowered
    assert "bioxtas" in lowered
    assert "python -m pip install -e ." in readme
    assert "numpy" in lowered
    assert "pandas" in lowered
    assert "xraydb" in lowered
    assert "saxsabs norm-factor" in readme
    assert "docs/api.md" in readme
    assert (REPO_ROOT / "docs" / "api.md").is_file()
    assert "CONTRIBUTING.md" in readme
    assert "https://github.com/D-sudoasd/AbsSAXS/issues" in readme
    assert "CODE_OF_CONDUCT.md" in readme
    assert "CITATION.cff" in readme


def test_shipped_readme_keeps_scientific_limits_without_submission_ritual():
    readme = _readme_text()
    lowered = re.sub(r"\s+", " ", readme.lower())

    assert "2.0.0" in readme
    assert "unreleased" in lowered
    assert "concept doi" in lowered
    assert "9×9" in readme or "9x9" in lowered
    assert "synthetic" in lowered
    assert "not pyfai" in lowered
    assert "workbench" in lowered
    assert "bl19b2" in lowered

    assert "editorialbot" not in lowered
    assert "--allow-author-placeholders" not in readme
    assert "--manual-confirmations" not in readme
    assert "check_public_candidate.py" not in readme
    assert "check_submission_readiness.py" not in readme
    assert "author-confirmation-form.md" not in readme


def test_shipped_readme_local_targets_and_heading_anchors_exist():
    readme = _readme_text()
    missing_targets = []
    empty_targets = []
    for target in sorted(readiness.local_readme_targets(readme)):
        path = REPO_ROOT / target
        if not path.is_file():
            missing_targets.append(target)
            continue
        if path.stat().st_size == 0:
            empty_targets.append(target)
    assert missing_targets == []
    assert empty_targets == []

    heading_anchors = readiness.markdown_heading_anchors(readme)
    missing_anchors = sorted(readiness.local_readme_anchors(readme) - heading_anchors)
    assert missing_anchors == []
    for required in (
        "installation",
        "example-usage",
        "workflows",
        "workbench",
        "citation",
    ):
        assert required in heading_anchors
