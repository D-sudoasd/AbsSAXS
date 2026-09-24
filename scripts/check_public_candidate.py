#!/usr/bin/env python3
"""Verify that the public GitHub candidate matches the local submitted checkout."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


CANONICAL_SLUG = "D-sudoasd/AbsSAXS"
CANONICAL_REPOSITORY = f"https://github.com/{CANONICAL_SLUG}"
API_REPOSITORY = f"https://api.github.com/repos/{CANONICAL_SLUG}"
EXPECTED_HOMEPAGE = "https://doi.org/10.5281/zenodo.19687103"
EXPECTED_LICENSE = "BSD-3-Clause"
ALLOWED_SUBMISSION_BRANCHES = {"main", "joss-submission"}
ALLOWED_CI_EVENTS = {"push", "pull_request", "workflow_dispatch"}


class PublicCandidateError(ValueError):
    """Raised when local evidence and public GitHub state do not identify one candidate."""


def git_output(root: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ["git", "-c", f"safe.directory={root.as_posix()}", *arguments],
        cwd=root,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
    )
    return completed.stdout.strip()


def fetch_json(url: str, *, token: str | None, timeout: float) -> dict[str, Any]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "saxsabs-joss-public-candidate-check",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(url, headers=headers)
    try:
        with urlopen(request, timeout=timeout) as response:  # noqa: S310 - fixed GitHub API
            payload = json.load(response)
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise PublicCandidateError(f"cannot read public GitHub evidence from {url}: {exc}") from exc
    if not isinstance(payload, dict):
        raise PublicCandidateError(f"GitHub API returned a non-object payload for {url}")
    return payload


def confirmed_identity(confirmations: dict[str, Any]) -> tuple[str, str, str, int]:
    branch = str(confirmations.get("submitted_branch", "")).strip()
    if branch not in ALLOWED_SUBMISSION_BRANCHES:
        raise PublicCandidateError("confirmation JSON has no valid submitted_branch")
    commit = str(confirmations.get("submitted_commit", "")).strip().lower()
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise PublicCandidateError("confirmation JSON has no 40-character submitted_commit")
    ci_run_url = str(confirmations.get("ci_run_url", "")).strip()
    run_match = re.fullmatch(
        re.escape(CANONICAL_REPOSITORY) + r"/actions/runs/(\d+)",
        ci_run_url,
    )
    if run_match is None:
        raise PublicCandidateError("confirmation JSON has no canonical GitHub Actions run URL")
    return branch, commit, ci_run_url, int(run_match.group(1))


def validate_public_candidate(
    confirmations: dict[str, Any],
    repository: dict[str, Any],
    branch_payload: dict[str, Any],
    run_payload: dict[str, Any],
    readme_payload: dict[str, Any],
    paper_payload: dict[str, Any],
    *,
    local_branch: str,
    local_head: str,
    local_status: str,
    local_readme_blob: str,
    local_paper_blob: str,
) -> dict[str, str]:
    """Validate local Git state, public branch identity, visible files, and CI evidence."""
    branch, commit, ci_run_url, run_id = confirmed_identity(confirmations)

    if local_branch != branch:
        raise PublicCandidateError(
            f"local branch {local_branch!r} does not match submitted branch {branch!r}"
        )
    if local_head.lower() != commit:
        raise PublicCandidateError("local HEAD does not match submitted_commit")
    if local_status:
        raise PublicCandidateError("local submitted worktree is not clean")

    if repository.get("full_name") != CANONICAL_SLUG:
        raise PublicCandidateError("GitHub repository identity is not canonical")
    if repository.get("private") is not False:
        raise PublicCandidateError("GitHub repository is not public")
    if repository.get("archived") is not False or repository.get("disabled") is not False:
        raise PublicCandidateError("GitHub repository is archived or disabled")
    if repository.get("has_issues") is not True:
        raise PublicCandidateError("GitHub issue tracker is not enabled")
    if repository.get("default_branch") != "main":
        raise PublicCandidateError("GitHub default branch is not main")
    if repository.get("homepage") != EXPECTED_HOMEPAGE:
        raise PublicCandidateError("GitHub homepage does not use the project concept DOI")
    license_payload = repository.get("license")
    if not isinstance(license_payload, dict) or license_payload.get("spdx_id") != EXPECTED_LICENSE:
        raise PublicCandidateError("GitHub does not detect the expected BSD-3-Clause license")

    if branch_payload.get("name") != branch:
        raise PublicCandidateError("GitHub branch response does not match submitted_branch")
    branch_commit = branch_payload.get("commit")
    if not isinstance(branch_commit, dict) or str(branch_commit.get("sha", "")).lower() != commit:
        raise PublicCandidateError("public submitted branch does not point to submitted_commit")

    for label, payload, path, local_blob in (
        ("README", readme_payload, "README.md", local_readme_blob),
        ("paper", paper_payload, "paper/paper.md", local_paper_blob),
    ):
        if payload.get("type") != "file" or payload.get("path") != path:
            raise PublicCandidateError(f"public {label} is not a visible file at {path}")
        if not isinstance(payload.get("size"), int) or payload["size"] <= 0:
            raise PublicCandidateError(f"public {label} is empty")
        if str(payload.get("sha", "")).lower() != local_blob.lower():
            raise PublicCandidateError(f"public {label} does not match the local submitted file")

    if run_payload.get("id") != run_id or run_payload.get("html_url") != ci_run_url:
        raise PublicCandidateError("GitHub Actions response does not match ci_run_url")
    if str(run_payload.get("head_sha", "")).lower() != commit:
        raise PublicCandidateError("GitHub Actions run does not test submitted_commit")
    if run_payload.get("head_branch") != branch:
        raise PublicCandidateError("GitHub Actions run does not test submitted_branch")
    if run_payload.get("status") != "completed" or run_payload.get("conclusion") != "success":
        raise PublicCandidateError("GitHub Actions run is not completed successfully")
    if run_payload.get("event") not in ALLOWED_CI_EVENTS:
        raise PublicCandidateError("GitHub Actions run has an unexpected event type")
    run_repository = run_payload.get("repository")
    if not isinstance(run_repository, dict) or run_repository.get("full_name") != CANONICAL_SLUG:
        raise PublicCandidateError("GitHub Actions run belongs to another repository")

    default_branch = str(repository["default_branch"])
    editorialbot_command = "none"
    if branch != default_branch:
        editorialbot_command = f"@editorialbot set branch-where-paper-is as {branch}"
    return {
        "repository": CANONICAL_REPOSITORY,
        "submitted_branch": branch,
        "submitted_commit": commit,
        "ci_run_url": ci_run_url,
        "editorialbot_branch_command": editorialbot_command,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--confirmations", type=Path, required=True)
    parser.add_argument("--timeout", type=float, default=20.0)
    args = parser.parse_args()
    root = args.root.resolve()
    try:
        confirmations = json.loads(args.confirmations.read_text(encoding="utf-8"))
        if not isinstance(confirmations, dict):
            raise PublicCandidateError("confirmation JSON must contain an object")
        branch, _commit, _ci_run_url, run_id = confirmed_identity(confirmations)
        token = os.environ.get("GITHUB_TOKEN") or None
        branch_encoded = quote(branch, safe="")
        ref_encoded = quote(branch, safe="")
        repository = fetch_json(API_REPOSITORY, token=token, timeout=args.timeout)
        branch_payload = fetch_json(
            f"{API_REPOSITORY}/branches/{branch_encoded}",
            token=token,
            timeout=args.timeout,
        )
        run_payload = fetch_json(
            f"{API_REPOSITORY}/actions/runs/{run_id}",
            token=token,
            timeout=args.timeout,
        )
        readme_payload = fetch_json(
            f"{API_REPOSITORY}/contents/README.md?ref={ref_encoded}",
            token=token,
            timeout=args.timeout,
        )
        paper_payload = fetch_json(
            f"{API_REPOSITORY}/contents/paper/paper.md?ref={ref_encoded}",
            token=token,
            timeout=args.timeout,
        )
        result = validate_public_candidate(
            confirmations,
            repository,
            branch_payload,
            run_payload,
            readme_payload,
            paper_payload,
            local_branch=git_output(root, "branch", "--show-current"),
            local_head=git_output(root, "rev-parse", "HEAD"),
            local_status=git_output(root, "status", "--porcelain=v1", "--untracked-files=all"),
            local_readme_blob=git_output(root, "hash-object", "README.md"),
            local_paper_blob=git_output(root, "hash-object", "paper/paper.md"),
        )
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        parser.exit(1, f"public candidate invalid: {exc}\n")

    print("public_candidate=PASS")
    for key, value in result.items():
        print(f"{key}={value}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
