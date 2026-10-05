#!/usr/bin/env python3
"""Select validation from changed paths, without reading source or test contents.

This is a read-only plan, shared by local agents and CI. Unknown paths and
shared scientific/build boundaries expand to the full suite. No result cache
or repository index is created.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# These isolated entry points have explicit consumer tests. Shared scientific
# calculations, parsers and exporters deliberately use the full-suite fallback.
FOCUSED = {
    "src/saxsabs/cli.py": [
        "test_cli",
        "test_profile_read_reuse",
        "test_minimal_2d_example",
    ],
    "src/saxsabs/workbench_launcher.py": ["test_workbench_launcher"],
    "saxsabs_workbench.py": ["test_workbench_launcher"],
    "saxsabs_workbench.pyw": ["test_workbench_launcher"],
    "Start_SAXSAbs_Workbench.bat": ["test_workbench_launcher"],
    "src/saxsabs/core/session_grouper.py": ["test_session_grouper", "test_workbench_scientific"],
    "scripts/check_submission_readiness.py": ["test_submission_readiness", "test_version_metadata"],
    "scripts/check_public_candidate.py": ["test_public_candidate"],
    "scripts/validate_release_metadata.py": ["test_release_metadata"],
    "scripts/build_release_notes.py": ["test_release_notes"],
    "README.md": ["test_readme_homepage", "test_version_metadata"],
    "docs/api.md": ["test_public_exports", "test_readme_homepage"],
}
METADATA = {"CITATION.cff", "codemeta.json", ".zenodo.json", "CHANGELOG.md"}
INSTRUCTIONS = {"AGENTS.md", "CONTRIBUTING.md", "CODE_OF_CONDUCT.md", ".gitignore"}
FULL_LINT = ["SASAbs.py", "saxs_mpl_style.py", "src", "tests", "paper", "scripts"]


def select_checks(paths: list[str], *, full: bool = False) -> dict:
    changed = sorted({path.replace("\\", "/").removeprefix("./") for path in paths})
    tests: set[str] = set()
    reasons = ["explicit full validation"] if full else []
    paper = full
    package = full
    for path in changed:
        package |= path.startswith("src/") or path in {
            "pyproject.toml",
            "MANIFEST.in",
            "LICENSE",
            "README.md",
            "SASAbs.py",
            "saxs_mpl_style.py",
            "saxsabs_workbench.py",
            "saxsabs_workbench.pyw",
            "Start_SAXSAbs_Workbench.bat",
        }
        paper |= path.startswith("paper/")
        if path in FOCUSED:
            tests.update(f"tests/{name}.py" for name in FOCUSED[path])
        elif path in METADATA or path in {"paper/paper.md", "paper/paper.bib"}:
            tests.update(
                f"tests/{name}.py"
                for name in (
                    "test_version_metadata",
                    "test_submission_readiness",
                    "test_release_metadata",
                    "test_release_notes",
                )
            )
        elif path.startswith("tests/test_") and path.endswith(".py"):
            tests.add(path)
        elif path.startswith("paper/") and not path.endswith(".py"):
            pass  # the paper build validates these assets
        elif (
            path in INSTRUCTIONS
            or (path.startswith("docs/") and path.endswith(".md"))
            or (
                path.startswith("assets/")
                and Path(path).suffix in {".md", ".png", ".svg", ".jpg", ".jpeg", ".webp"}
            )
            or path.startswith(".github/ISSUE_TEMPLATE/")
        ):
            pass
        elif path == ".github/PULL_REQUEST_TEMPLATE.md":
            pass
        else:
            full = True
            reasons.append(f"shared boundary or unmapped path: {path}")
            package = True
            if path.startswith(".github/workflows/"):
                paper = True

    if full:
        matrix = {
            "include": [
                {"os": os_name, "python": version}
                for os_name in ("ubuntu-latest", "windows-latest", "macos-latest")
                for version in ("3.10", "3.11", "3.12", "3.13")
            ]
        }
    else:
        matrix = {
            "include": [
                {"os": "ubuntu-latest", "python": "3.10"},
                {"os": "windows-latest", "python": "3.13"},
                {"os": "macos-latest", "python": "3.12"},
            ]
        }
    return {
        "changed": changed,
        "full": full,
        "tests": ["tests"] if full else sorted(tests),
        "lint": FULL_LINT if full else [p for p in changed if p.endswith((".py", ".pyw"))],
        "paper": paper,
        "package": package,
        "matrix": matrix,
        "reasons": reasons,
    }


def changed_paths(base: str, head: str | None = None) -> list[str]:
    def git(*args: str) -> list[str]:
        output = subprocess.check_output(["git", *args], cwd=ROOT)
        return [part.decode("utf-8") for part in output.split(b"\0") if part]

    # Keep both sides of a move: rename folding can hide deleted code or links.
    paths = git("diff", "--no-renames", "--name-only", "-z", base, *([head] if head else []), "--")
    if head is None:
        paths.extend(git("ls-files", "--others", "--exclude-standard", "-z"))
    return paths


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", help="explicit changed paths; otherwise read Git diff")
    parser.add_argument("--base", default="origin/main")
    parser.add_argument("--head", help="committed head for CI; omitted means current worktree")
    parser.add_argument("--full", action="store_true", help="explicit deep validation path")
    parser.add_argument("--github-output", type=Path, help="append CI job outputs to this file")
    args = parser.parse_args()
    try:
        paths = args.paths or ([] if args.full else changed_paths(args.base, args.head))
    except (OSError, subprocess.CalledProcessError) as exc:
        print(f"Cannot determine changes: {exc}", file=sys.stderr)
        return 2
    # Deleted source/tests cannot be validated by naming the removed test file.
    deleted_code = any(p.endswith((".py", ".pyw")) and not (ROOT / p).is_file() for p in paths)
    plan = select_checks(paths, full=args.full or deleted_code)
    if not plan["full"] and any(
        (p.endswith(".md") or p.startswith("assets/")) and not (ROOT / p).exists() for p in paths
    ):
        plan["tests"] = sorted(set(plan["tests"]) | {"tests/test_readme_homepage.py"})
    plan["lint"] = [p for p in plan["lint"] if (ROOT / p).exists()]
    print(json.dumps(plan, indent=2))
    if args.github_output is not None:
        with args.github_output.open("a", encoding="utf-8") as output:
            for key in ("full", "tests", "lint", "paper", "package", "matrix"):
                output.write(f"{key}={json.dumps(plan[key], separators=(',', ':'))}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
