# AbsSAXS agent instructions

Complete authorized work and appropriate verification; preserve unrelated changes.
Use established SAXS terminology. Keep measured values, units, missingness and
provenance explicit; synthetic fixtures establish engineering behavior only.
Do not commit private beamline data, credentials or large generated outputs.

## Start from the task and current changes

- Reuse context already available in this conversation. Inspect Git status/diff
  and the relevant entry point; search its callers/tests only as needed.
- Read bounded sections of relevant files. Do not pre-read a fixed document set,
  build a repository map, scan generated outputs, or load every available skill.
- Batch independent reads in one tool call. Use parallel work only when it saves
  elapsed time without shared mutations or repeated investigation.

## Select and reuse evidence

`python scripts/select_checks.py --base origin/main` returns a read-only check
plan from changed paths, including untracked files. Use a validated base; use
`--full` for an explicit deep check. Run the selected tests and lint once for
the current contents. Reuse passing results until relevant code, inputs or
configuration change; investigate failures locally before expanding scope.
Shared scientific calculations, I/O contracts, dependencies, CI configuration,
shared test fixtures and unknown paths require the full suite. Release validation
also retains installation/artifact checks. Never skip numerical, unit,
missingness, provenance or resume-integrity checks for speed.

## Route only when relevant

- Package: `src/saxsabs/`; calculations: `core/`; I/O: `io/`; CLI: `cli.py`.
  Tests mirror these concerns under `tests/`. Root launchers and `SASAbs.py`
  contain the desktop/legacy workbench; keep reusable logic in the package.
- Check selection, setup and workflow details: [agent workflow](docs/agent-workflow.md).
- GUI or detector workflow changes: relevant sections of
  [manual verification](examples/manual-verification.md) and `examples/minimal_2d/`.
- BL19B2 batch semantics: [batch runbook](docs/bl19b2_abs2d_batch_runbook.md).
- JOSS submission or release: [contributing](CONTRIBUTING.md) and
  [submission checklist](docs/joss-submission-checklist.md).

Use Python 3.10+, four-space indentation, explicit imports and the existing
100-character Ruff configuration. Keep optional dependencies optional. Describe
behavior changes and actual verification in commits/PRs; use `type: imperative summary`.
