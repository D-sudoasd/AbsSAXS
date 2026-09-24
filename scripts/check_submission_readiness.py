#!/usr/bin/env python3
"""Fail closed on mechanical JOSS pre-submission requirements.

The script checks only facts that can be established from a local checkout.
Author-controlled declarations, demonstrated research use, repository age, and
remote CI are reported as manual gates rather than guessed from local files.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "paper" / "paper.md"
EARLIEST_SUBMISSION_DATE = date(2026, 8, 26)
CANONICAL_REPOSITORY = "https://github.com/D-sudoasd/AbsSAXS"

REQUIRED_SECTIONS = (
    "Summary",
    "Statement of need",
    "State of the field",
    "Software design",
    "Software availability",
    "Research impact statement",
    "AI usage disclosure",
    "Author contributions",
    "Acknowledgements",
    "References",
)

MANUAL_GATES = (
    "Public history and iterative development still satisfy JOSS on the submission date.",
    "The public repository identity and submitted branch match the confirmed candidate.",
    "A verifiable research-use case is included in the impact statement.",
    "Author list, order, corresponding author, affiliations, ORCIDs, and roles are confirmed.",
    "AI tools/models/versions, scope, and final human review are confirmed.",
    "Funding, sponsor role, acknowledgements, and competing interests are confirmed.",
    "The public candidate revision has a green CI run.",
)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def current_date() -> date:
    """Return the runtime date; isolated for deterministic strict-gate tests."""
    return date.today()


def project_version() -> str:
    match = re.search(
        r'(?ms)^\[project\]\s*$.*?^version\s*=\s*"([^"]+)"\s*$',
        read(ROOT / "pyproject.toml"),
    )
    if not match:
        raise ValueError("pyproject.toml has no [project] version")
    return match.group(1)


def citation_keys(markdown: str) -> set[str]:
    # Exclude e-mail addresses while retaining Pandoc bracketed and narrative
    # citations such as [@key] and "@key showed ...".
    return set(re.findall(r"(?<![A-Za-z0-9._%+-])@([A-Za-z0-9_:.+-]+)", markdown))


def bibliography_keys(bibtex: str) -> set[str]:
    return set(re.findall(r"(?m)^@\w+\{([^,]+),", bibtex))


def local_readme_targets(markdown: str) -> set[str]:
    targets = set(
        re.findall(r"(?<!!)\[[^\]]+\]\(([^)]+)\)", markdown)
        + re.findall(r"!\[[^\]]*\]\(([^)]+)\)", markdown)
        + re.findall(r'<(?:a\s+href|img\s+src)="([^"]+)"', markdown)
    )
    return {
        target.split("#", 1)[0]
        for target in targets
        if target
        and not target.startswith(("http://", "https://", "mailto:", "#"))
    }


def markdown_heading_anchors(markdown: str) -> set[str]:
    anchors: set[str] = set()
    counts: dict[str, int] = {}
    for heading in re.findall(r"(?m)^#{1,6}\s+(.+?)\s*$", markdown):
        slug = heading.strip().lower()
        slug = re.sub(r"<[^>]+>", "", slug)
        slug = re.sub(r"[^\w\- ]", "", slug, flags=re.UNICODE)
        slug = re.sub(r"[\s-]+", "-", slug).strip("-")
        if not slug:
            continue
        occurrence = counts.get(slug, 0)
        counts[slug] = occurrence + 1
        anchors.add(slug if occurrence == 0 else f"{slug}-{occurrence}")
    return anchors


def local_readme_anchors(markdown: str) -> set[str]:
    targets = set(
        re.findall(r"(?<!!)\[[^\]]+\]\((#[^)]+)\)", markdown)
        + re.findall(r'<a\s+href="(#[^"]+)"', markdown)
    )
    return {target[1:] for target in targets}


def git_output(*arguments: str) -> str | None:
    try:
        completed = subprocess.run(
            ["git", "-c", f"safe.directory={ROOT.as_posix()}", *arguments],
            cwd=ROOT,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None
    return completed.stdout.strip()


def paper_word_count() -> int:
    pandoc = os.environ.get("PANDOC") or shutil.which("pandoc")
    if pandoc is None:
        raise RuntimeError(
            "pandoc is required for the paper word-count gate; install it or set PANDOC"
        )
    command = [
        pandoc,
        str(PAPER),
        "--from=markdown",
        "--to=plain",
        f"--resource-path={PAPER.parent}",
    ]
    try:
        completed = subprocess.run(
            command,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
        )
    except FileNotFoundError as exc:
        raise RuntimeError(f"configured Pandoc executable was not found: {pandoc}") from exc
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"pandoc failed: {exc.stderr.strip()}") from exc

    body = completed.stdout.split("References", 1)[0]
    body = re.sub(r"\[Author input required.*?\]", "", body, flags=re.DOTALL)
    return len(re.findall(r"[A-Za-z0-9][A-Za-z0-9'./+^-]*", body))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--allow-author-placeholders",
        action="store_true",
        help="report author-controlled placeholders without failing the local gate",
    )
    parser.add_argument(
        "--as-of",
        type=date.fromisoformat,
        default=date.today(),
        metavar="YYYY-MM-DD",
        help="date used for deterministic eligibility checks; defaults to today",
    )
    parser.add_argument(
        "--manual-confirmations",
        type=Path,
        help="author-approved JSON record required by strict submission mode",
    )
    args = parser.parse_args()
    runtime_date = current_date()

    failures: list[str] = []
    paper = read(PAPER)
    version = project_version()
    front_matter_match = re.match(r"\A---\s*\n(.*?)\n---\s*\n", paper, re.DOTALL)
    if front_matter_match is None:
        failures.append("paper has no parseable YAML front matter")
        front_matter = ""
    else:
        front_matter = front_matter_match.group(1)

    if args.as_of < EARLIEST_SUBMISSION_DATE:
        failures.append(
            f"submission date {args.as_of.isoformat()} is before the conservative "
            f"eligibility date {EARLIEST_SUBMISSION_DATE.isoformat()}"
        )
    if not args.allow_author_placeholders and args.as_of > runtime_date:
        failures.append(
            f"strict mode cannot use future submission date {args.as_of.isoformat()}; "
            f"runtime date is {runtime_date.isoformat()}"
        )

    paper_title_match = re.search(r"(?m)^title:\s*(.+?)\s*$", front_matter)
    if paper_title_match is None:
        failures.append("paper front matter has no title")
        paper_title = ""
    else:
        paper_title = paper_title_match.group(1).strip()
        if (
            len(paper_title) >= 2
            and paper_title[0] == paper_title[-1]
            and paper_title[0] in {"'", '"'}
        ):
            paper_title = paper_title[1:-1]

    paper_date_match = re.search(r"(?m)^date:\s*(.+?)\s*$", front_matter)
    if paper_date_match is None:
        failures.append("paper front matter has no date")
        paper_date = None
    else:
        try:
            paper_date = datetime.strptime(paper_date_match.group(1), "%d %B %Y").date()
        except ValueError:
            failures.append("paper date must use the JOSS format 'D Month YYYY'")
            paper_date = None
    if paper_date is not None and paper_date != args.as_of:
        failures.append(
            f"paper date {paper_date.isoformat()} does not match submission date "
            f"{args.as_of.isoformat()}"
        )

    corresponding_count = len(
        re.findall(r"(?m)^\s+corresponding:\s*true\s*$", front_matter)
    )
    if corresponding_count != 1 and not args.allow_author_placeholders:
        failures.append(
            f"paper must identify exactly one corresponding author; found {corresponding_count}"
        )
    author_email_present = bool(
        re.search(r"(?m)^\s+email:\s*\S+@\S+\s*$", front_matter)
    )
    if not author_email_present and not args.allow_author_placeholders:
        failures.append("paper front matter has no author email")

    for section in REQUIRED_SECTIONS:
        if not re.search(rf"(?m)^# {re.escape(section)}\s*$", paper):
            failures.append(f"missing paper section: {section}")

    placeholder_count = paper.count("[Author input required before submission:")
    if placeholder_count and not args.allow_author_placeholders:
        failures.append(f"paper contains {placeholder_count} author-input placeholders")

    confirmations: dict[str, object] = {}
    confirmed_branch = ""
    if not args.allow_author_placeholders:
        if args.manual_confirmations is None:
            failures.append("strict mode requires --manual-confirmations JSON")
        else:
            try:
                confirmations = json.loads(args.manual_confirmations.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                failures.append(f"cannot read manual confirmations: {exc}")
            else:
                boolean_fields = (
                    "public_history_confirmed",
                    "repository_identity_confirmed",
                    "research_use_confirmed",
                    "authorship_confirmed",
                    "ai_disclosure_confirmed",
                    "funding_and_coi_confirmed",
                )
                for field in boolean_fields:
                    if confirmations.get(field) is not True:
                        failures.append(f"manual confirmation is not true: {field}")
                ci_run_url = str(confirmations.get("ci_run_url", ""))
                if not re.fullmatch(
                    re.escape(CANONICAL_REPOSITORY) + r"/actions/runs/\d+", ci_run_url
                ):
                    failures.append(
                        "manual confirmations contain no valid Actions run URL for the "
                        "canonical repository"
                    )
                confirmed_branch = str(confirmations.get("submitted_branch", "")).strip()
                if confirmed_branch not in {"main", "joss-submission"}:
                    failures.append(
                        "manual confirmations contain no valid submitted branch"
                    )
                submitted_commit = str(confirmations.get("submitted_commit", ""))
                if not re.fullmatch(r"[0-9a-fA-F]{40}", submitted_commit):
                    failures.append("manual confirmations contain no 40-character commit SHA")
                if confirmations.get("confirmed_on") != args.as_of.isoformat():
                    failures.append("manual confirmations date does not match --as-of")
                evidence_reference = str(
                    confirmations.get("research_evidence_reference", "")
                ).strip()
                if not evidence_reference or evidence_reference.lower() in {
                    "todo",
                    "tbd",
                    "none",
                    "n/a",
                }:
                    failures.append(
                        "manual confirmations contain no research-evidence reference"
                    )

    if re.search(r"(?i)\b(TODO|TBD|FIXME)\b", paper):
        failures.append("paper contains TODO/TBD/FIXME text")

    cited = citation_keys(paper)
    bibliography = bibliography_keys(read(ROOT / "paper" / "paper.bib"))
    if cited - bibliography:
        failures.append(f"paper has missing bibliography keys: {sorted(cited - bibliography)}")
    if bibliography - cited:
        failures.append(f"paper has unused bibliography keys: {sorted(bibliography - cited)}")

    readme = read(ROOT / "README.md")
    for target in sorted(local_readme_targets(readme)):
        if not (ROOT / target).exists():
            failures.append(f"README local target does not exist: {target}")
    missing_anchors = local_readme_anchors(readme) - markdown_heading_anchors(readme)
    if missing_anchors:
        failures.append(f"README has missing local anchors: {sorted(missing_anchors)}")

    versions = {
        "pyproject": version,
        "citation": re.search(r'(?m)^version: "([^"]+)"$', read(ROOT / "CITATION.cff")),
        "codemeta": json.loads(read(ROOT / "codemeta.json"))["version"],
        "zenodo": json.loads(read(ROOT / ".zenodo.json"))["version"],
    }
    citation_match = versions["citation"]
    if citation_match is None:
        failures.append("CITATION.cff has no version")
    else:
        versions["citation"] = citation_match.group(1)
    if any(value != version for value in versions.values()):
        failures.append(f"version metadata disagree: {versions}")

    canonical = CANONICAL_REPOSITORY
    citation_text = read(ROOT / "CITATION.cff")
    codemeta = json.loads(read(ROOT / "codemeta.json"))
    zenodo = json.loads(read(ROOT / ".zenodo.json"))
    if f'repository-code: "{canonical}"' not in citation_text:
        failures.append("CITATION.cff does not use the canonical repository")
    if f'url: "{canonical}"' not in citation_text:
        failures.append("CITATION.cff URL does not identify the candidate repository")
    if "10.5281/zenodo.19687103" in citation_text:
        failures.append("CITATION.cff presents the concept DOI as an unreleased version DOI")
    if codemeta.get("identifier") != canonical or codemeta.get("url") != canonical:
        failures.append("CodeMeta candidate identity does not use the canonical repository")
    if codemeta.get("codeRepository") != canonical:
        failures.append("CodeMeta codeRepository is not canonical")
    related = zenodo.get("related_identifiers", [])
    expected_relations = {
        ("isSupplementTo", canonical, ""),
        ("isVersionOf", "10.5281/zenodo.19687103", "doi"),
    }
    actual_relations = {
        (
            str(item.get("relation", "")),
            str(item.get("identifier", "")),
            str(item.get("scheme", "")),
        )
        for item in related
        if isinstance(item, dict)
    }
    if actual_relations != expected_relations:
        failures.append("Zenodo related identifiers do not match repository/concept DOI roles")
    if paper_title and zenodo.get("title") != paper_title:
        failures.append("Zenodo title does not match the JOSS paper title")

    changelog = read(ROOT / "CHANGELOG.md")
    if f"## [{version}] - Unreleased" not in changelog:
        failures.append(f"CHANGELOG does not mark {version} as Unreleased")

    required_files = (
        ROOT / "LICENSE",
        ROOT / "CITATION.cff",
        ROOT / "CONTRIBUTING.md",
        ROOT / "CODE_OF_CONDUCT.md",
        ROOT / "docs" / "api.md",
        ROOT / "paper" / "paper.bib",
        ROOT / "paper" / "fig_workflow.png",
        ROOT / "paper" / "fig_gui.png",
    )
    for path in required_files:
        if not path.is_file() or path.stat().st_size == 0:
            failures.append(f"missing or empty required file: {path.relative_to(ROOT)}")

    generated_names = {"__pycache__", ".pytest_cache", ".ruff_cache", "build", "dist"}
    generated = [
        path.relative_to(ROOT)
        for path in ROOT.rglob("*")
        if path.is_dir() and (path.name in generated_names or path.name.endswith(".egg-info"))
    ]
    if generated:
        failures.append(f"generated cache/build directories remain: {generated}")

    branch_value = git_output("branch", "--show-current")
    branch = "unknown" if branch_value is None else (branch_value or "detached")
    allowed_submission_branches = {"main", "joss-submission"}
    if args.allow_author_placeholders:
        if branch not in allowed_submission_branches | {"unknown"}:
            failures.append(f"unexpected submission branch: {branch}")
    else:
        if branch == "unknown":
            failures.append("strict mode cannot verify the current Git branch")
        elif branch not in allowed_submission_branches:
            failures.append(f"unexpected submission branch: {branch}")
        elif confirmed_branch in allowed_submission_branches and branch != confirmed_branch:
            failures.append(
                f"current branch {branch!r} does not match confirmed submitted branch "
                f"{confirmed_branch!r}"
            )

    current_head = git_output("rev-parse", "HEAD")
    status_porcelain = git_output("status", "--porcelain=v1", "--untracked-files=all")
    worktree_clean = status_porcelain == "" if status_porcelain is not None else None
    if not args.allow_author_placeholders:
        if current_head is None or status_porcelain is None:
            failures.append("strict mode cannot verify Git HEAD and worktree state")
        else:
            submitted_commit = str(confirmations.get("submitted_commit", ""))
            if re.fullmatch(r"[0-9a-fA-F]{40}", submitted_commit) and (
                submitted_commit.lower() != current_head.lower()
            ):
                failures.append("manual confirmation commit does not match current HEAD")
            if not worktree_clean:
                failures.append("strict mode requires a clean Git worktree")

    try:
        words = paper_word_count()
    except RuntimeError as exc:
        failures.append(str(exc))
        words = -1
    else:
        if not 750 <= words <= 1750:
            failures.append(f"paper body is {words} words; required range is 750-1750")

    status = "PASS" if not failures else "FAIL"
    print(f"mechanical_readiness={status}")
    print(f"version={version}")
    print(f"as_of={args.as_of.isoformat()}")
    print(f"earliest_submission_date={EARLIEST_SUBMISSION_DATE.isoformat()}")
    print(f"paper_body_words={words}")
    print(f"author_placeholders={placeholder_count}")
    print(f"citations={len(cited)}")
    print(f"bibliography_entries={len(bibliography)}")
    print(f"branch={branch}")
    print(f"submitted_branch_confirmed={confirmed_branch or 'none'}")
    print(f"current_head={current_head or 'unknown'}")
    print(
        "worktree_clean="
        + ("unknown" if worktree_clean is None else str(worktree_clean).lower())
    )
    print(f"corresponding_authors={corresponding_count}")
    print(f"author_email_present={author_email_present}")
    print(f"manual_confirmations_loaded={bool(confirmations)}")
    for failure in failures:
        print(f"FAIL: {failure}")
    for gate in MANUAL_GATES:
        print(f"MANUAL: {gate}")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
