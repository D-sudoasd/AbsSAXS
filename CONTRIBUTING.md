# Contributing

Thanks for considering a contribution to AbsSAXS. The canonical repository is
<https://github.com/D-sudoasd/AbsSAXS>.

## Questions and issue reports

Report reproducible bugs or propose features through the
[issue tracker](https://github.com/D-sudoasd/AbsSAXS/issues). Include the
smallest portable example that reproduces the problem and the command or API
call used. Do not attach beamline-private data, credentials, or large generated
outputs; replace them with anonymized fixtures where possible.

For a question that is not a bug or feature proposal, use the maintainer contact
listed in [CITATION.cff](CITATION.cff). Follow the
[Code of Conduct](CODE_OF_CONDUCT.md) in issues, discussions, and pull requests.

## Development setup

Python 3.10 or later is required. From a fresh checkout:

```bash
git clone https://github.com/D-sudoasd/AbsSAXS.git
cd AbsSAXS
python -m pip install -e ".[dev]"
python scripts/select_checks.py --full
```

The `dev` extra installs pytest, Ruff, and development dependencies. To run the
same optional workflows installed in continuous integration, install all
supported extras:

```bash
python -m pip install -e ".[dev,gui,bl19b2,hdf5]"
```

The CLI and core API do not require a display. Changes to GUI workflows may also
need the `gui` extra and a local display. See the
[manual verification checklist](examples/manual-verification.md) for the
portable synthetic 2D path and Workbench checks.

Select checks for the actual diff, then run the returned test and lint paths.
Do not repeat installation in an already working environment. See the
[agent workflow](docs/agent-workflow.md) for commands and expansion criteria.
For a fresh environment, shared scientific/build changes, or release validation,
use `--full` and run its returned test and lint paths with the same workflow.

## Pull requests

Keep each pull request focused. For a behavior change:

- add or update focused tests for the changed behavior;
- keep reusable scientific calculations and I/O in `src/saxsabs/`, with GUI
  orchestration separate;
- update the README, API reference, or workflow documentation when public
  behavior changes;
- run the selected tests and Ruff checks, and include the exact commands and
  results in the pull-request description;
- describe any instrument-specific assumptions or inputs needed to reproduce
  the workflow.

Use anonymized, small fixtures in tests and examples. Do not commit
beamline-private datasets, credentials, generated outputs, or audit artifacts.
Reviews focus on scientific input semantics, provenance, reproducibility, and
behavior with supported optional dependencies.

## Release expectations

Version `2.0.0` is the current unreleased JOSS candidate; `v1.1.1` is the latest
archived release. Keep the candidate untagged during JOSS review. After review,
the maintainer should identify the finalized commit, confirm its validation and
release metadata, then create the matching version tag and GitHub Release and
archive that same version with Zenodo. Update the changelog and citation metadata
from the finalized commit, and publish a version-specific DOI only after Zenodo
assigns it. The project-level concept DOI remains suitable for general citation.

## Code of Conduct

All contributors are expected to follow the
[Code of Conduct](CODE_OF_CONDUCT.md). The document describes how to report
unacceptable behaviour.
