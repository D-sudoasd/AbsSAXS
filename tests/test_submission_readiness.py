from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def _load_readiness_checker():
    script = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "check_submission_readiness.py"
    )
    spec = importlib.util.spec_from_file_location("check_submission_readiness", script)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load submission readiness checker from {script}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


readiness = _load_readiness_checker()


def _write(path: Path, text: str = "present") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _minimal_ready_repository(root: Path) -> Path:
    sections = "\n\n".join(
        f"# {section}\n\nSection text [@reference]."
        if section == "Summary"
        else f"# {section}\n\nSection text."
        for section in readiness.REQUIRED_SECTIONS
    )
    paper = f"""---
title: Test paper
authors:
  - name: Test Author
    email: author@example.org
    corresponding: true
    affiliation: '1'
affiliations:
  - index: 1
    name: Test Institute
date: 26 August 2026
bibliography: paper.bib
---

{sections}
"""
    _write(root / "paper" / "paper.md", paper)
    _write(
        root / "paper" / "paper.bib",
        "@misc{reference,\n  title = {Reference}\n}\n",
    )
    _write(root / "pyproject.toml", '[project]\nversion = "2.0.0"\n')
    canonical = readiness.CANONICAL_REPOSITORY
    concept_doi = "10.5281/zenodo.19687103"
    _write(
        root / "CITATION.cff",
        'version: "2.0.0"\n'
        f'repository-code: "{canonical}"\n'
        f'url: "{canonical}"\n',
    )
    _write(
        root / "codemeta.json",
        json.dumps(
            {
                "version": "2.0.0",
                "identifier": canonical,
                "url": canonical,
                "codeRepository": canonical,
            }
        ),
    )
    _write(
        root / ".zenodo.json",
        json.dumps(
            {
                "title": "Test paper",
                "version": "2.0.0",
                "related_identifiers": [
                    {"relation": "isSupplementTo", "identifier": canonical},
                    {
                        "relation": "isVersionOf",
                        "identifier": concept_doi,
                        "scheme": "doi",
                    },
                ],
            }
        ),
    )
    _write(root / "CHANGELOG.md", "## [2.0.0] - Unreleased\n")
    _write(root / "README.md", "[License](LICENSE)\n")
    for relative in (
        "LICENSE",
        "CONTRIBUTING.md",
        "CODE_OF_CONDUCT.md",
        "docs/api.md",
        "paper/fig_workflow.png",
        "paper/fig_gui.png",
    ):
        _write(root / relative)

    confirmations = root / "confirmations.json"
    _write(
        confirmations,
        json.dumps(
            {
                "public_history_confirmed": True,
                "repository_identity_confirmed": True,
                "research_use_confirmed": True,
                "authorship_confirmed": True,
                "ai_disclosure_confirmed": True,
                "funding_and_coi_confirmed": True,
                "ci_run_url": "https://github.com/D-sudoasd/AbsSAXS/actions/runs/12345",
                "submitted_branch": "joss-submission",
                "submitted_commit": "a" * 40,
                "confirmed_on": "2026-08-26",
                "research_evidence_reference": "editor-visible workflow record 2026-08-20",
            }
        ),
    )
    return confirmations


def test_reference_and_readme_target_parsers():
    assert readiness.citation_keys(
        "Text [@alpha; @beta]. Contact author@example.org. @gamma agrees."
    ) == {"alpha", "beta", "gamma"}
    assert readiness.bibliography_keys("@misc{alpha,\n}\n@article{beta,\n}\n") == {
        "alpha",
        "beta",
    }
    assert readiness.local_readme_targets(
        "[Docs](docs/api.md) ![Hero](assets/hero.svg) "
        '<a href="https://example.org">external</a>'
    ) == {"docs/api.md", "assets/hero.svg"}
    assert readiness.markdown_heading_anchors("# Quick start\n\n## Quick start\n") == {
        "quick-start",
        "quick-start-1",
    }
    assert readiness.local_readme_anchors(
        '<a href="#quick-start">Start</a> [Docs](#documentation)'
    ) == {"quick-start", "documentation"}


def _mock_clean_git(monkeypatch):
    def fake_git_output(*arguments: str) -> str | None:
        values = {
            ("branch", "--show-current"): "joss-submission",
            ("rev-parse", "HEAD"): "a" * 40,
            ("status", "--porcelain=v1", "--untracked-files=all"): "",
        }
        return values.get(arguments)

    monkeypatch.setattr(readiness, "git_output", fake_git_output)


def test_strict_gate_passes_with_complete_evidence_record(tmp_path, monkeypatch, capsys):
    confirmations = _minimal_ready_repository(tmp_path)
    monkeypatch.setattr(readiness, "ROOT", tmp_path)
    monkeypatch.setattr(readiness, "PAPER", tmp_path / "paper" / "paper.md")
    monkeypatch.setattr(readiness, "paper_word_count", lambda: 900)
    _mock_clean_git(monkeypatch)
    monkeypatch.setattr(
        readiness.sys,
        "argv",
        [
            "check_submission_readiness.py",
            "--as-of",
            "2026-08-26",
            "--manual-confirmations",
            str(confirmations),
        ],
    )

    monkeypatch.setattr(readiness, "current_date", lambda: readiness.date(2026, 8, 25))
    assert readiness.main() == 1
    assert "strict mode cannot use future submission date" in capsys.readouterr().out

    monkeypatch.setattr(readiness, "current_date", lambda: readiness.date(2026, 8, 26))
    assert readiness.main() == 0


def test_strict_gate_accepts_confirmed_main_after_merge(tmp_path, monkeypatch):
    confirmations = _minimal_ready_repository(tmp_path)
    payload = json.loads(confirmations.read_text(encoding="utf-8"))
    payload["submitted_branch"] = "main"
    payload["submitted_commit"] = "c" * 40
    confirmations.write_text(json.dumps(payload), encoding="utf-8")

    monkeypatch.setattr(readiness, "ROOT", tmp_path)
    monkeypatch.setattr(readiness, "PAPER", tmp_path / "paper" / "paper.md")
    monkeypatch.setattr(readiness, "paper_word_count", lambda: 900)
    monkeypatch.setattr(readiness, "current_date", lambda: readiness.date(2026, 8, 26))

    def main_git_output(*arguments: str) -> str | None:
        values = {
            ("branch", "--show-current"): "main",
            ("rev-parse", "HEAD"): "c" * 40,
            ("status", "--porcelain=v1", "--untracked-files=all"): "",
        }
        return values.get(arguments)

    monkeypatch.setattr(readiness, "git_output", main_git_output)
    monkeypatch.setattr(
        readiness.sys,
        "argv",
        [
            "check_submission_readiness.py",
            "--as-of",
            "2026-08-26",
            "--manual-confirmations",
            str(confirmations),
        ],
    )

    assert readiness.main() == 0


def test_strict_gate_rejects_branch_not_confirmed(tmp_path, monkeypatch, capsys):
    confirmations = _minimal_ready_repository(tmp_path)
    payload = json.loads(confirmations.read_text(encoding="utf-8"))
    payload["submitted_branch"] = "main"
    confirmations.write_text(json.dumps(payload), encoding="utf-8")

    monkeypatch.setattr(readiness, "ROOT", tmp_path)
    monkeypatch.setattr(readiness, "PAPER", tmp_path / "paper" / "paper.md")
    monkeypatch.setattr(readiness, "paper_word_count", lambda: 900)
    monkeypatch.setattr(readiness, "current_date", lambda: readiness.date(2026, 8, 26))
    _mock_clean_git(monkeypatch)
    monkeypatch.setattr(
        readiness.sys,
        "argv",
        [
            "check_submission_readiness.py",
            "--as-of",
            "2026-08-26",
            "--manual-confirmations",
            str(confirmations),
        ],
    )

    assert readiness.main() == 1
    assert (
        "current branch 'joss-submission' does not match confirmed submitted branch 'main'"
        in capsys.readouterr().out
    )


def test_strict_gate_rejects_missing_evidence_record(tmp_path, monkeypatch, capsys):
    _minimal_ready_repository(tmp_path)
    monkeypatch.setattr(readiness, "ROOT", tmp_path)
    monkeypatch.setattr(readiness, "PAPER", tmp_path / "paper" / "paper.md")
    monkeypatch.setattr(readiness, "paper_word_count", lambda: 900)
    _mock_clean_git(monkeypatch)
    monkeypatch.setattr(readiness, "current_date", lambda: readiness.date(2026, 8, 26))
    monkeypatch.setattr(
        readiness.sys,
        "argv",
        ["check_submission_readiness.py", "--as-of", "2026-08-26"],
    )

    assert readiness.main() == 1
    assert "strict mode requires --manual-confirmations JSON" in capsys.readouterr().out


def test_strict_gate_rejects_dirty_or_mismatched_checkout(tmp_path, monkeypatch, capsys):
    confirmations = _minimal_ready_repository(tmp_path)
    monkeypatch.setattr(readiness, "ROOT", tmp_path)
    monkeypatch.setattr(readiness, "PAPER", tmp_path / "paper" / "paper.md")
    monkeypatch.setattr(readiness, "paper_word_count", lambda: 900)

    def dirty_git_output(*arguments: str) -> str | None:
        values = {
            ("branch", "--show-current"): "joss-submission",
            ("rev-parse", "HEAD"): "b" * 40,
            ("status", "--porcelain=v1", "--untracked-files=all"): " M paper/paper.md",
        }
        return values.get(arguments)

    monkeypatch.setattr(readiness, "git_output", dirty_git_output)
    monkeypatch.setattr(readiness, "current_date", lambda: readiness.date(2026, 8, 26))
    monkeypatch.setattr(
        readiness.sys,
        "argv",
        [
            "check_submission_readiness.py",
            "--as-of",
            "2026-08-26",
            "--manual-confirmations",
            str(confirmations),
        ],
    )

    assert readiness.main() == 1
    output = capsys.readouterr().out
    assert "commit does not match current HEAD" in output
    assert "requires a clean Git worktree" in output
