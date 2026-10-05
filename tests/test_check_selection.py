"""Validation routing should cost one diff, not a source/test inventory."""

import importlib.util
import json
import os
import shutil
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


def _git(root, *args):
    return subprocess.check_output(
        ["git", "-c", "core.autocrlf=false", *args], cwd=root, text=True, encoding="utf-8"
    ).strip()


@pytest.fixture(scope="module")
def ci_jobs():
    root = SCRIPT.parents[1]
    return yaml.safe_load((root / ".github/workflows/ci.yml").read_text(encoding="utf-8"))["jobs"]


@pytest.fixture(scope="module")
def selector_text():
    return SCRIPT.read_text(encoding="utf-8")


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
    assert "--no-renames" in calls[0]
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


@pytest.mark.parametrize(
    ("old_path", "new_path", "full", "selected_tests"),
    [
        ("src/saxsabs/core/calibration.py", "docs/calibration.md", True, ["tests"]),
        ("docs/old.md", "docs/new.md", False, ["tests/test_readme_homepage.py"]),
    ],
)
def test_git_renames_keep_removed_inputs(
    tmp_path, monkeypatch, capsys, old_path, new_path, full, selected_tests
):
    _git(tmp_path, "init", "-q")
    old = tmp_path / old_path
    old.parent.mkdir(parents=True)
    old.write_text("unchanged contents\n", encoding="utf-8")
    _git(tmp_path, "add", ".")
    _git(
        tmp_path, "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
        "commit", "-qm", "baseline",
    )
    base = _git(tmp_path, "rev-parse", "HEAD")
    new = tmp_path / new_path
    new.parent.mkdir(parents=True, exist_ok=True)
    old.rename(new)
    _git(tmp_path, "add", "-A")
    monkeypatch.setattr(checks, "ROOT", tmp_path)
    monkeypatch.setattr(sys, "argv", ["select_checks.py", "--base", base])
    assert checks.main() == 0
    plan = json.loads(capsys.readouterr().out)
    assert plan["changed"] == sorted([old_path, new_path])
    assert plan["full"] == full
    assert plan["tests"] == selected_tests


def test_explicit_full_does_not_need_git(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["select_checks.py", "--full"])
    monkeypatch.setattr(checks, "changed_paths", lambda *args: pytest.fail("unexpected Git read"))
    assert checks.main() == 0
    plan = json.loads(capsys.readouterr().out)
    assert plan["full"] and plan["paper"] and plan["package"]


def test_ci_routes_jobs_and_lints_once(ci_jobs):
    jobs = ci_jobs
    assert jobs["test"]["needs"] == "changes"
    assert "fromJSON" in jobs["test"]["strategy"]["matrix"]
    assert not any(step.get("name") == "Ruff" for step in jobs["test"]["steps"])
    assert jobs["lint"]["if"] == "needs.changes.outputs.lint != '[]'"
    assert jobs["paper"]["if"] == "needs.changes.outputs.paper == 'true'"
    assert jobs["package"]["if"] == "needs.changes.outputs.package == 'true'"


@pytest.mark.parametrize(
    ("path", "event", "baseline", "fetch_status", "base_kind", "full", "commands"),
    [
        ("AGENTS.md", "push", "1", "0", "sha", False, ["gh", "git", "python"]),
        ("src/saxsabs/cli.py", "push", "1", "0", "sha", False, ["gh", "git", "python"]),
        ("src/saxsabs/io/parsers.py", "push", "1", "0", "sha", True, ["gh", "git", "python"]),
        ("AGENTS.md", "push", "0", "0", "sha", True, ["gh", "python"]),
        ("AGENTS.md", "push", "error", "0", "sha", True, ["gh", "python"]),
        ("AGENTS.md", "push", "1", "1", "sha", True, ["gh", "git", "python"]),
        ("AGENTS.md", "workflow_dispatch", "1", "0", "sha", True, ["python"]),
        ("AGENTS.md", "push", "1", "0", "empty", True, ["python"]),
        ("AGENTS.md", "push", "1", "0", "zero", True, ["python"]),
    ],
)
def test_ci_planner_replay(
    tmp_path, ci_jobs, selector_text, path, event, baseline, fetch_status, base_kind, full, commands
):
    # Execute the actual planner and selector with controlled remote GH/fetch
    # calls. Only diff-based routes need a real two-commit repository.
    bash = shutil.which("bash")
    if os.name == "nt":
        git = shutil.which("git")
        bash_path = Path(git).parents[1] / "bin/bash.exe" if git else None
        bash = str(bash_path) if bash_path and bash_path.is_file() else None
    if bash is None:
        pytest.skip("CI planner replay requires Bash (Git for Windows includes it)")
    script = tmp_path / "scripts/select_checks.py"
    script.parent.mkdir()
    script.write_text(selector_text, encoding="utf-8")
    source = tmp_path / path
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text("before\n", encoding="utf-8")
    base = "a" * 40
    explicit_full = len(commands) == 1 or baseline != "1" or fetch_status != "0"
    if not explicit_full:
        _git(tmp_path, "init", "-q")
        _git(tmp_path, "add", ".")
        commit = ("-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-qm")
        _git(tmp_path, *commit, "baseline")
        base = _git(tmp_path, "rev-parse", "HEAD")
        source.write_text("after\n", encoding="utf-8")
        _git(tmp_path, "add", ".")
        _git(tmp_path, *commit, "head")
    log = tmp_path / "commands"
    output = tmp_path / "outputs"
    git_trace = tmp_path / "git-trace"
    env = {
        **os.environ,
        "BASE": base if base_kind == "sha" else "0" * 40 if base_kind == "zero" else "",
        "BASE_BRANCH": "main",
        "GITHUB_EVENT_NAME": event,
        "GITHUB_REPOSITORY": "D-sudoasd/AbsSAXS",
        "GITHUB_OUTPUT": output.as_posix(),
        "COMMAND_LOG": log.as_posix(),
        "BASELINE_RESULT": baseline,
        "FETCH_STATUS": fetch_status,
        "REPLAY_PYTHON": Path(sys.executable).as_posix(),
        "GIT_TRACE": git_trace.as_posix(),
    }
    controlled_remote = r'''
    record() { printf '%s\0' "$@" >> "$COMMAND_LOG"; printf '\0' >> "$COMMAND_LOG"; }
    gh() {
      record gh "$@"
      if [ "$BASELINE_RESULT" = error ]; then return 1; fi
      printf '%s\n' "$BASELINE_RESULT"
    }
    git() { record git "$@"; return "$FETCH_STATUS"; }
    python() { record python "$@"; "$REPLAY_PYTHON" "$@"; }
    '''
    completed = subprocess.run(
        [bash, "--noprofile", "--norc", "-e", "-o", "pipefail", "-c",
         controlled_remote + ci_jobs["changes"]["steps"][-1]["run"]],
        cwd=tmp_path, env=env, check=True, capture_output=True, text=True, encoding="utf-8",
    )
    plan = json.loads(completed.stdout)
    fields = {
        key: json.loads(value)
        for key, value in (line.split("=", 1) for line in output.read_text().splitlines())
    }
    calls = [part.split("\0") for part in log.read_text().rstrip("\0").split("\0\0")]
    assert [call[0] for call in calls] == commands
    assert plan["full"] == full
    assert fields == {key: plan[key] for key in fields}
    selector = calls[-1]
    assert ("--full" in selector) == explicit_full
    diff_calls = sum(
        "built-in: git diff " in line for line in git_trace.read_text().splitlines()
    ) if git_trace.exists() else 0
    assert diff_calls == int(not explicit_full)
    if calls[0][0] == "gh":
        assert "--branch" in calls[0] and calls[0][calls[0].index("--branch") + 1] == "main"
        assert calls[0][calls[0].index("--commit") + 1] == base
        assert calls[0][calls[0].index("--status") + 1] == "success"
    if not full:
        expected = checks.select_checks([path])
        assert plan["tests"] == expected["tests"]
        assert plan["package"] == expected["package"]
    else:
        assert plan["tests"] == ["tests"]
    if explicit_full:
        assert plan["paper"] and plan["package"]
    assert len(plan["matrix"]["include"]) == (12 if full else 3)
    print(json.dumps({
        "path": path, "baseline": baseline, "event": event, "base_kind": base_kind,
        "fetch_status": fetch_status, "commands": commands, "diff_calls": diff_calls, "full": full,
        "tests": plan["tests"], "paper": plan["paper"], "package": plan["package"],
    }))
