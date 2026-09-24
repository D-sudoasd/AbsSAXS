from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


def _load_checker():
    script = Path(__file__).resolve().parents[1] / "scripts" / "check_public_candidate.py"
    spec = importlib.util.spec_from_file_location("check_public_candidate", script)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load public candidate checker from {script}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


checker = _load_checker()
COMMIT = "a" * 40
RUN_URL = "https://github.com/D-sudoasd/AbsSAXS/actions/runs/12345"


def _payloads(branch: str = "joss-submission"):
    confirmations = {
        "submitted_branch": branch,
        "submitted_commit": COMMIT,
        "ci_run_url": RUN_URL,
    }
    repository = {
        "full_name": "D-sudoasd/AbsSAXS",
        "private": False,
        "archived": False,
        "disabled": False,
        "has_issues": True,
        "default_branch": "main",
        "homepage": "https://doi.org/10.5281/zenodo.19687103",
        "license": {"spdx_id": "BSD-3-Clause"},
    }
    branch_payload = {"name": branch, "commit": {"sha": COMMIT}}
    run_payload = {
        "id": 12345,
        "html_url": RUN_URL,
        "head_sha": COMMIT,
        "head_branch": branch,
        "status": "completed",
        "conclusion": "success",
        "event": "push",
        "repository": {"full_name": "D-sudoasd/AbsSAXS"},
    }
    readme_payload = {"type": "file", "path": "README.md", "size": 100, "sha": "b" * 40}
    paper_payload = {
        "type": "file",
        "path": "paper/paper.md",
        "size": 100,
        "sha": "c" * 40,
    }
    return confirmations, repository, branch_payload, run_payload, readme_payload, paper_payload


def _validate(branch: str = "joss-submission", **overrides):
    payloads = _payloads(branch)
    arguments = {
        "confirmations": payloads[0],
        "repository": payloads[1],
        "branch_payload": payloads[2],
        "run_payload": payloads[3],
        "readme_payload": payloads[4],
        "paper_payload": payloads[5],
        "local_branch": branch,
        "local_head": COMMIT,
        "local_status": "",
        "local_readme_blob": "b" * 40,
        "local_paper_blob": "c" * 40,
    }
    arguments.update(overrides)
    return checker.validate_public_candidate(**arguments)


def test_submission_branch_passes_and_reports_editorialbot_command():
    result = _validate()
    assert result["submitted_commit"] == COMMIT
    assert result["editorialbot_branch_command"] == (
        "@editorialbot set branch-where-paper-is as joss-submission"
    )


def test_main_passes_without_branch_command():
    result = _validate("main")
    assert result["submitted_branch"] == "main"
    assert result["editorialbot_branch_command"] == "none"


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda p: p[1].update(homepage="https://doi.org/10.5281/zenodo.19687104"),
         "concept DOI"),
        (lambda p: p[2]["commit"].update(sha="d" * 40), "public submitted branch"),
        (lambda p: p[3].update(head_sha="d" * 40), "does not test submitted_commit"),
        (lambda p: p[3].update(conclusion="failure"), "not completed successfully"),
        (lambda p: p[4].update(sha="d" * 40), "public README does not match"),
    ],
)
def test_remote_mismatch_fails_closed(mutation, message):
    payloads = _payloads()
    mutation(payloads)
    with pytest.raises(checker.PublicCandidateError, match=message):
        checker.validate_public_candidate(
            *payloads,
            local_branch="joss-submission",
            local_head=COMMIT,
            local_status="",
            local_readme_blob="b" * 40,
            local_paper_blob="c" * 40,
        )


def test_dirty_or_wrong_local_checkout_fails_closed():
    with pytest.raises(checker.PublicCandidateError, match="not clean"):
        _validate(local_status=" M README.md")
    with pytest.raises(checker.PublicCandidateError, match="local HEAD"):
        _validate(local_head="d" * 40)
    with pytest.raises(checker.PublicCandidateError, match="local branch"):
        _validate(local_branch="main")


def test_confirmation_identity_rejects_noncanonical_run_url():
    confirmations = {
        "submitted_branch": "joss-submission",
        "submitted_commit": COMMIT,
        "ci_run_url": "https://example.org/actions/runs/12345",
    }
    with pytest.raises(checker.PublicCandidateError, match="canonical GitHub Actions"):
        checker.confirmed_identity(confirmations)
