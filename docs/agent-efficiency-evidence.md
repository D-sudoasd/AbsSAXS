# Agent workflow efficiency evidence

Measured on 5 October 2026. Baseline: commit `2439fa3`; optimized behavior:
the profile reader, CLI, readiness checker and check selector introduced with
this document. These are engineering measurements, not measured-beamline
validation or a GPT-6 Astra model A/B experiment.

## Observed sources of repeated work

- A local 27 September JOSS-review trace requested `CITATION.cff` twice,
  `docs/author-confirmation-form.md` three times and readiness-checker sections
  four times. Some sections and environments were different: the trace supports
  retaining task context, not removing the necessary full submission review.
  The trace itself is private and is not copied into this repository.
- `read_external_1d_profile` reopened one text file for decimal-comma detection,
  comment/plain headers, physical width, each pandas trial and provenance.
  CLI column overrides then performed another table read/parse.
- The readiness checker parsed `codemeta.json` and `.zenodo.json` twice and
  read `CITATION.cff` twice. Its recursive generated-directory check descended
  into a directory even after that directory had already failed the gate.
- CI unconditionally ran the full suite and identical Ruff scope in all 12
  OS/Python combinations, plus paper and package jobs. The PR template also
  requested the full suite for every change.

## Profile and CLI replay

Each fixture has 1,500 rows: `Q = 0.01*n`, `I = 100/n`, another intensity column
`alternate = 50/n`, and `sigma = 0.1`, for `n = 1..1500`. Formats were named CSV,
a whitespace table with a comment header and relative-intensity provenance,
and semicolon/decimal-comma data with six decimal places. Column-override tasks
select `alternate` through the actual CLI helper. Both implementations used the
same fixtures and runtime: Windows, Python 3.13.0, pandas 2.3.0, NumPy 2.4.1.

Counts instrumented file opens, `pandas.read_csv` and `pandas.to_numeric`.
Timings are medians of seven instrumented calls after a warm-up, with the old
and new implementations run sequentially. Imports and environment setup are
excluded. OS caching and instrumentation affect elapsed times; operation counts
are the principal result.

| Task | File reads, before → after | Pandas parses | Numeric conversions | Median ms |
| --- | ---: | ---: | ---: | ---: |
| Named CSV | 8 → 1 | 3 → 3 | 15 → 9 | 38.498 → 31.632 |
| Named CSV, CLI override | 12 → 1 | 4 → 3 | 18 → 12 | 43.813 → 27.218 |
| Comment header | 8 → 1 | 4 → 4 | 15 → 12 | 104.160 → 103.290 |
| Comment header, CLI override | 9 → 1 | 5 → 4 | 22 → 15 | 155.548 → 114.445 |
| Decimal comma | 2 → 1 | 0 → 0 | 7 → 4 | 23.310 → 21.052 |

The decimal-comma route uses its special row parser once in both versions; zero
pandas parses does not mean zero parsing. The other grammar trials remain
because their interpretation/ranking and malformed-unit rejection are required.
For all five replays, hashes of the returned arrays and metadata were identical.
The CSV override reduced file opens by 91.7%, pandas parses by 25% and observed
median time by 37.9%; the comment-header override reduced time by 26.4%.
The plain comment-header task had little timing change despite fewer reads.

`tests/test_profile_read_reuse.py` reproduces the operation limits for three
formats, BOM handling, unknown uncertainty and column selection. It also replaces
the source during parsing, then restores the old size/mtime: the first result
uses the original coherent snapshot and the next call observes the new values
and provenance. XML/HDF5 paths remain specialized; unsupported non-text column
overrides fail explicitly. No persistent file/result cache was introduced.

## Readiness-check replay

A synthetic tree contained `build/<n>/__pycache__/large.pyc` for `n = 0..199`,
an empty `src/`, and `.git/objects/`. The old loop examined 604 entries and
reported 201 generated directories. The new scan examined three child names in
two visited directories and reported `build` once. Both checks failed the gate;
the generated payload was not re-inspected after its root established failure.
The source metadata read counts fell from 2 to 1 for each of the three documents.
The strict-gate tests still check dates, branch/commit identity and clean state.

## Validation-route replay

The existing CI had 14 jobs for each change and 12 identical Ruff executions.
The new selector was exercised with common source/document tasks and failure
cases. It performs no source/test-content reads; an ordinary worktree plan uses
one Git diff and one untracked-path query. Missing Git evidence returns an error,
and unknown/shared boundaries and deleted code expand to full validation.

The table uses the 1,216 cases from one actual full pytest run, including the 27
new regression cases. Focused counts were derived from that run's test report;
the passing suite was not repeated separately for each hypothetical change.

| Changed path | Selected test cases | CI test jobs | Ruff executions | Paper / package |
| --- | ---: | ---: | ---: | --- |
| `AGENTS.md` or ordinary workflow prose | 0 | 0 | 0 | neither |
| `README.md` | 8 | 3 | 0 | package |
| CLI entry point | 88 | 3 | 1 | package |
| Workbench launcher | 16 | 3 | 1 | package |
| Readiness checker | 12 | 3 | 1 | neither |
| Shared profile parser | 1,216 | 12 | 1 | package |

The conditional routes require a previously successful CI run at the exact base
SHA/branch. Without that evidence, CI runs the full path. Manual dispatch, CI
changes, shared fixtures and unknown inputs also expand validation. The planner
adds one small job; a separate Ruff job replaces the 12 repeated executions.
Full dispatch retains all 12 test combinations, paper and package validation.
The release workflow remains complete. These job/count comparisons describe
the implemented routes; they do not claim a measured remote wall-time reduction
or a model-level reduction in agent tool calls.

## Executable workflow replay

The final review added `test_ci_planner_replay`. It executes the current CI
planning step and selector, using real two-commit Git repositories for diff-based
routes. GitHub responses and remote fetch success/failure are controlled; Git
traces count actual diff calls. Full-fallback cases do not create or parse a
repository because `--full` does not need a diff. The workflow and selector
source are each read once by module-scoped test fixtures.

Baseline counts come from `2439fa3:.github/workflows/ci.yml`; current routes come
from the replay's emitted JSON and conditional jobs. These are reproducible
workflow command/job counts, not observed GPT-6 Astra outer tool calls or remote
wall time. Runner actions, dependency installation, Python command wrappers and
fixture setup commits are excluded. Pytest and Ruff counts mean invocations of
those verification tools; the replay does not rerun their selected suites.

| Task / baseline evidence | Planner calls: GH / fetch / selector / diff | Pytest jobs, before → after | Ruff runs | Paper / package jobs, after |
| --- | ---: | ---: | ---: | --- |
| Workflow prose, successful base | 1 / 1 / 1 / 1 | 12 → 0 | 12 → 0 | 0 / 0 |
| CLI, successful base | 1 / 1 / 1 / 1 | 12 → 3 | 12 → 1 | 0 / 1 |
| Shared parser, successful base | 1 / 1 / 1 / 1 | 12 → 12 | 12 → 1 | 0 / 1 |
| Missing/unsuccessful base run or GH lookup error | 1 / 0 / 1 / 0 | 12 → 12 | 12 → 1 | 1 / 1 |
| Successful run but base fetch fails | 1 / 1 / 1 / 0 | 12 → 12 | 12 → 1 | 1 / 1 |
| Manual dispatch or empty/zero base SHA | 0 / 0 / 1 / 0 | 12 → 12 | 12 → 1 | 1 / 1 |

The old workflow had no planning subprocesses and built paper/package artifacts
for every task. The planner therefore adds a bounded decision step; it saves
validation work on local changes while retaining the deep path when evidence is
insufficient. A failed fetch now takes that deep path instead of stopping before
validation. No remote lookup or Git diff is repeated within one plan.

Real-Git regression tests also cover code/document moves. Rename detection must
not hide a removed source or README link: both old and new paths are classified
using `--no-renames`, without another Git query. The selected session-grouper
tests cover both branches of its public metadata helper as well as clustering.

Reproduce the routing trace in a configured environment with Git and Bash
(Git for Windows includes Bash):

```powershell
python -m pytest -q -s tests/test_check_selection.py -k ci_planner_replay
```

## Verification and reproduction

The initial complete local suite passed: **1,216 tests**. The final review added
13 regression cases; **1,229 tests passed in 38.35 seconds**, with full project
Ruff also passing. `actionlint` 1.7.12 accepted the initial CI workflow; the final
planner shell is exercised by the executable replay above. Wheel and sdist builds
succeeded during the initial validation; committed artifacts are checked by CI. The installed-wheel
smoke uses the existing dependency environment and is not a fresh-dependency
installation claim.

The final selection guards and standalone `pytest` collection path were checked
with the focused selector/readiness tests after the full run. The selector test
loads the project script by its explicit path, so it works with both `pytest`
and `python -m pytest` and does not depend on an ambient `scripts` package.

To reproduce the relevant regression checks in a configured environment:

```powershell
python -m pytest -q tests/test_profile_read_reuse.py tests/test_check_selection.py tests/test_submission_readiness.py
python scripts/select_checks.py AGENTS.md
python scripts/select_checks.py src/saxsabs/cli.py
python scripts/select_checks.py src/saxsabs/io/parsers.py
```

Temporary benchmark fixtures, extracted baseline modules, timing drivers,
workflow-lint binaries and build/smoke outputs are removed during closeout.
Only the implementation, regression tests and this evidence record are retained.
