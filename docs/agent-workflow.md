# Agent workflow

Start with the task, existing conversation and changed paths. This document is
for setup or validation decisions that need more detail than `AGENTS.md`; it is
not a mandatory pre-read for every task.

## Local validation

In an existing working environment, do not reinstall dependencies. On a fresh
checkout use `python -m pip install -e ".[dev]"`; install optional extras only
for the workflow being exercised. Python 3.10+ is supported.

Plan from a validated base and the current worktree, including untracked files:

```powershell
$checks = python scripts/select_checks.py --base origin/main | ConvertFrom-Json
if ($LASTEXITCODE -ne 0) { throw "Check selection failed" }
if ($checks.tests.Count) {
    python -m pytest -q @($checks.tests)
    if ($LASTEXITCODE -ne 0) { throw "Tests failed" }
}
if ($checks.lint.Count) {
    python -m ruff check @($checks.lint)
    if ($LASTEXITCODE -ne 0) { throw "Lint failed" }
}
git diff --check
```

`--base` should identify the revision whose behavior has already been validated.
If there is no usable baseline, use `--full`. Explicit paths are useful for a
single known task, for example `python scripts/select_checks.py src/saxsabs/cli.py`;
the complete diff remains authoritative before delivery. `--head REF` compares
committed revisions and intentionally excludes local untracked files.

The selector reads path names from one Git diff and, locally, one untracked-file
query. It does not parse source, collect all tests or create a repository index.
Its small route table lists isolated entry points and consumer tests. Unknown
files, deleted code, shared scientific calculations, parsers/exporters, build
configuration, CI and shared test fixtures select `tests` and the full lint
scope. Update a route only when its consumer coverage is understood.

For documentation changes, check the actual diff and changed links/content;
there is no unconditional pytest or artifact build. README changes retain their
homepage/metadata tests and distribution check. Deleted documentation/assets
also run the README local-link tests. GUI behavior changes require the relevant
manual check and synthetic example from `examples/manual-verification.md`.

Record a passing command and its covered files/inputs in the current task.
Reuse that result while those contents and dependencies are unchanged. A commit
or merge that preserves the validated contents does not itself require another
identical local run. New changes, failed checks, unexplained differences or an
uncovered consumer justify focused follow-up; expand to the full suite when the
local evidence cannot resolve the risk. Release validation retains the complete
test suite, clean-installed artifacts and metadata gates.

## Context and skills

Search the known module before widening to its callers or package. Read the
smallest section that answers the current question. Batch independent reads
and retain conclusions in the conversation instead of rebuilding a project
map. Use Git diff and changed-file metadata to decide whether a previous read
needs refreshing. Do not recursively search `.git`, environments, old audit
deliveries or generated outputs for ordinary source tasks.

Load a skill only for its applicable operation. Treat overlapping checklists as
one verification requirement: cite the existing passing check rather than
repeating it for each skill or PR checklist. JOSS submission uses its checklist
when submission is actually requested; it is not a development preflight.
This repository adds no model-specific prompt pack or persistent agent cache.

## Reuse of scientific inputs

The text profile reader captures one UTF-8 snapshot for grammar detection,
header/width checks, provenance and pandas trials. It retains the selected table
for CLI column overrides and reuses numeric conversions within each candidate.
All format trials and their ranking remain active; the optimization does not
accept the first plausible table or suppress malformed-unit checks.

No text or parsed result survives a call. The next call reads the current file,
including a same-size edit whose modification time is unchanged. This avoids
persistent cache invalidation rules and large detector-array retention. XML and
HDF5 retain their specialized readers. Scientific SHA-256, calibration context,
missing-data and resume-integrity checks remain required at reuse boundaries.

The submission checker reads each metadata document once per invocation. It
reports generated directory roots and stops descending into them; detecting a
root is already sufficient to fail that gate. Git internals are excluded from
that source-tree check. Full submission checks remain an explicit deep path.

## Continuous integration

CI uses the same selector. It first checks for a successful `ci.yml` run on the
exact base revision and branch. A missing, failed, pending or inaccessible
baseline selects full validation; manual dispatch also selects the full path.
This prevents a small follow-up commit from concealing an earlier failed change.
The lookup uses the documented [GitHub CLI run filters](https://cli.github.com/manual/gh_run_list).

Focused tests cover Ubuntu/Python 3.10, Windows/3.13 and macOS/3.12. Shared
boundaries keep the original 12 OS/Python combinations. Ruff runs once, outside
the matrix. Paper and distribution jobs run only when their inputs change or
full validation is explicitly required. The release workflow keeps its full
validation and installation checks. Conditional jobs follow
[GitHub's job-condition behavior](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-jobs-with-conditions).

See [measured efficiency evidence](agent-efficiency-evidence.md) for replay
counts, numerical equivalence and the limits of the measurements.
