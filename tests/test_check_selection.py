"""Validation routing should cost one diff, not a source/test inventory."""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "select_checks.py"
SPEC = importlib.util.spec_from_file_location("select_checks", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise ImportError(f"cannot load check selector from {SCRIPT}")
checks = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(checks)


@pytest.mark.parametrize(
    ("path", "full", "test_count", "paper", "package"),
    [
        ("AGENTS.md", False, 0, False, False),
        ("docs/agent-workflow.md", False, 0, False, False),
        ("README.md", False, 2, False, True),
        ("src/saxsabs/cli.py", False, 3, False, True),
        ("src/saxsabs/workbench_launcher.py", False, 1, False, True),
        ("scripts/check_submission_readiness.py", False, 2, False, False),
        ("paper/fig_workflow.svg", False, 0, True, False),
        ("tests/test_parsers.py", False, 1, False, False),
        ("src/saxsabs/io/parsers.py", True, 1, False, True),
        ("src/saxsabs/core/calibration.py", True, 1, False, True),
        ("tests/conftest.py", True, 1, False, True),
        ("pyproject.toml", True, 1, False, True),
        (".github/workflows/ci.yml", True, 1, True, True),
        ("new_unmapped_config.json", True, 1, False, True),
    ],
)
def test_common_task_routes(path, full, test_count, paper, package, monkeypatch):
    def no_content_reads(*args, **kwargs):
        pytest.fail("check selection must not parse repository contents")

    monkeypatch.setattr(Path, "read_text", no_content_reads)
    plan = checks.select_checks([path])
    assert plan["full"] == full
    assert len(plan["tests"]) == test_count
    assert plan["paper"] == paper
    assert plan["package"] == package
    assert len(plan["matrix"]["include"]) == (12 if full else 3)
    if full:
        assert plan["tests"] == ["tests"]


def test_plan_unions_related_tests_and_normalizes_paths():
    assert checks.select_checks(["docs/new_config.json"])["full"]
    assert checks.select_checks(["assets/new_generator.py"])["full"]
    plan = checks.select_checks(
        [
            r"src\saxsabs\cli.py",
            "./src/saxsabs/cli.py",
            "tests/test_cli.py",
            ".github/PULL_REQUEST_TEMPLATE.md",
        ]
    )
    assert plan["tests"] == [
        "tests/test_cli.py",
        "tests/test_minimal_2d_example.py",
        "tests/test_profile_read_reuse.py",
    ]
    assert plan["lint"] == ["src/saxsabs/cli.py", "tests/test_cli.py"]


def test_git_diff_is_batched_and_includes_untracked(monkeypatch):
    calls = []

    def git(command, **kwargs):
        calls.append(command)
        if "diff" in command:
            return b"src/saxsabs/cli.py\0"
        return b"tests/test_cli.py\0"

    monkeypatch.setattr(checks.subprocess, "check_output", git)
    assert checks.changed_paths("baseline") == ["src/saxsabs/cli.py", "tests/test_cli.py"]
    assert len(calls) == 2
    calls.clear()
    assert checks.changed_paths("baseline", "head") == ["src/saxsabs/cli.py"]
    assert len(calls) == 1


def test_missing_diff_does_not_become_an_empty_plan(monkeypatch, capsys):
    def failed(*args):
        raise subprocess.CalledProcessError(128, "git diff")

    monkeypatch.setattr(checks, "changed_paths", failed)
    monkeypatch.setattr(sys, "argv", ["select_checks.py"])
    assert checks.main() == 2
    assert "Cannot determine changes" in capsys.readouterr().err


def test_deleted_code_expands_and_ci_outputs_are_json(tmp_path, monkeypatch, capsys):
    output = tmp_path / "job-output"
    monkeypatch.setattr(checks, "ROOT", tmp_path)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "select_checks.py",
            "tests/test_deleted.py",
            "--github-output",
            str(output),
        ],
    )
    assert checks.main() == 0
    plan = json.loads(capsys.readouterr().out)
    assert plan["full"]
    assert plan["tests"] == ["tests"]
    fields = dict(line.split("=", 1) for line in output.read_text().splitlines())
    assert json.loads(fields["tests"]) == ["tests"]
    assert len(json.loads(fields["matrix"])["include"]) == 12


def test_deleted_document_checks_readme_links(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(checks, "ROOT", tmp_path)
    monkeypatch.setattr(sys, "argv", ["select_checks.py", "docs/deleted.md"])
    assert checks.main() == 0
    plan = json.loads(capsys.readouterr().out)
    assert plan["tests"] == ["tests/test_readme_homepage.py"]


def test_explicit_full_does_not_need_git(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["select_checks.py", "--full"])
    monkeypatch.setattr(checks, "changed_paths", lambda *args: pytest.fail("unexpected Git read"))
    assert checks.main() == 0
    plan = json.loads(capsys.readouterr().out)
    assert plan["full"] and plan["paper"] and plan["package"]


def test_ci_routes_jobs_and_lints_once():
    root = Path(__file__).resolve().parents[1]
    workflow = yaml.safe_load((root / ".github/workflows/ci.yml").read_text(encoding="utf-8"))
    jobs = workflow["jobs"]
    assert jobs["test"]["needs"] == "changes"
    assert "fromJSON" in jobs["test"]["strategy"]["matrix"]
    assert not any(step.get("name") == "Ruff" for step in jobs["test"]["steps"])
    assert jobs["lint"]["if"] == "needs.changes.outputs.lint != '[]'"
    assert jobs["paper"]["if"] == "needs.changes.outputs.paper == 'true'"
    assert jobs["package"]["if"] == "needs.changes.outputs.package == 'true'"
    planning = jobs["changes"]["steps"][-1]["run"]
    assert '--commit "$BASE" --status success' in planning
    assert "--full" in planning
