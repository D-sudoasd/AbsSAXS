from __future__ import annotations

import importlib.util
import json
from datetime import date
from pathlib import Path
import re
import sys

from saxsabs import __version__


ROOT = Path(__file__).resolve().parents[1]


def test_release_version_metadata_is_consistent(monkeypatch):
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    citation = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
    codemeta = json.loads((ROOT / "codemeta.json").read_text(encoding="utf-8"))
    zenodo = json.loads((ROOT / ".zenodo.json").read_text(encoding="utf-8"))
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    paper = (ROOT / "paper" / "paper.md").read_text(encoding="utf-8")

    project_version = re.search(
        r'(?ms)^\[project\]\s*$.*?^version\s*=\s*"([^\"]+)"\s*$', pyproject
    )
    assert project_version is not None
    assert project_version.group(1) == __version__
    assert re.search(rf'^version: "{re.escape(__version__)}"$', citation, re.MULTILINE)
    assert codemeta["version"] == __version__
    assert zenodo["version"] == __version__
    spec = importlib.util.spec_from_file_location(
        "saxsabs_workbench_version_metadata_test",
        ROOT / "SASAbs.py",
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    assert module.APP_VERSION == __version__

    class MissingSourceVersionPath:
        def __init__(self, *_parts):
            pass

        def resolve(self):
            return self

        @property
        def parent(self):
            return self

        def __truediv__(self, _part):
            return self

        def read_text(self, **_kwargs):
            raise OSError("source tree unavailable")

    monkeypatch.setattr(module, "Path", MissingSourceVersionPath)
    monkeypatch.setattr(
        module.importlib_metadata,
        "version",
        lambda distribution: __version__ if distribution == "saxsabs" else "",
    )
    assert module._read_package_version() == __version__
    changelog_heading = re.search(
        rf"(?m)^## \[{re.escape(__version__)}\] - (?:Unreleased|\d{{4}}-\d{{2}}-\d{{2}})$",
        changelog,
    )
    assert changelog_heading is not None
    heading_value = changelog_heading.group(0).rsplit(" - ", 1)[1]
    if heading_value != "Unreleased":
        assert date.fromisoformat(heading_value).isoformat() == heading_value
    assert '"Development Status :: 4 - Beta"' in pyproject
    assert '"Development Status :: 5 - Production/Stable"' not in pyproject
    assert '"Concept DOI" = "https://doi.org/10.5281/zenodo.19687103"' in pyproject
    assert "\nDOI = " not in pyproject
    canonical = "https://github.com/D-sudoasd/AbsSAXS"
    concept_doi = "10.5281/zenodo.19687103"
    assert f'repository-code: "{canonical}"' in citation
    assert f'url: "{canonical}"' in citation
    assert concept_doi not in citation
    assert codemeta["identifier"] == canonical
    assert codemeta["url"] == canonical
    assert codemeta["codeRepository"] == canonical
    assert zenodo["related_identifiers"] == [
        {
            "relation": "isSupplementTo",
            "identifier": canonical,
        },
        {
            "relation": "isVersionOf",
            "identifier": concept_doi,
            "scheme": "doi",
        },
    ]
    paper_title = re.search(r"(?m)^title:\s*'([^']+)'\s*$", paper)
    assert paper_title is not None
    assert zenodo["title"] == paper_title.group(1)


def test_source_distribution_manifest_includes_release_metadata():
    manifest = (ROOT / "MANIFEST.in").read_text(encoding="utf-8").splitlines()
    included = {
        line.removeprefix("include ").strip()
        for line in manifest
        if line.startswith("include ")
    }
    assert {
        "CHANGELOG.md",
        "CITATION.cff",
        "codemeta.json",
        ".zenodo.json",
        "CODE_OF_CONDUCT.md",
        "CONTRIBUTING.md",
        "LICENSE",
        "SASAbs.py",
        "saxs_mpl_style.py",
        ".github/workflows/ci.yml",
        ".github/workflows/release.yml",
    } <= included


def test_release_smoke_isolated_from_checkout_source():
    workflow = (ROOT / ".github" / "workflows" / "release.yml").read_text(
        encoding="utf-8"
    )
    example = (
        ROOT / "examples" / "minimal_2d" / "run_minimal_2d_pipeline.py"
    ).read_text(encoding="utf-8")

    assert 'smoke_dir="$(mktemp -d)"' in workflow
    assert 'cd "$smoke_dir"' in workflow
    assert '"site-packages" not in module_path.parts' in workflow
    assert 'python scripts/validate_release_metadata.py --tag "$GITHUB_REF_NAME"' in workflow
    assert "sys.path.insert" not in example


def test_ci_runs_for_submission_branch_and_manual_dispatch():
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

    assert "branches: [main, joss-submission]" in workflow
    assert "workflow_dispatch:" in workflow


def test_submission_readiness_gate_is_packaged_and_fail_closed():
    script = (ROOT / "scripts" / "check_submission_readiness.py").read_text(
        encoding="utf-8"
    )
    manifest = (ROOT / "MANIFEST.in").read_text(encoding="utf-8")

    assert 'paper.count("[Author input required before submission:")' in script
    assert "750 <= words <= 1750" in script
    assert "EARLIEST_SUBMISSION_DATE = date(2026, 8, 26)" in script
    assert "corresponding_count != 1 and not args.allow_author_placeholders" in script
    assert "author_email_present = bool(" in script
    assert "paper has missing bibliography keys" in script
    assert "README local target does not exist" in script
    assert "generated cache/build directories remain" in script
    assert "strict mode requires --manual-confirmations JSON" in script
    assert '"repository_identity_confirmed"' in script
    assert "no valid Actions run URL for the " in script
    assert "manual confirmation commit does not match current HEAD" in script
    assert "strict mode requires a clean Git worktree" in script
    workbench = (ROOT / "SASAbs.py").read_text(encoding="utf-8")
    assert "K-only scaling requires positive thickness_cm provenance" in workbench
    assert "K-only scaling requires thickness_source provenance" in workbench
    assert '"thicknesscm": "thickness_cm"' in workbench
    assert '"thicknesssource": "thickness_source"' in workbench
    assert "recursive-include scripts *.py" in manifest
