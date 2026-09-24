# Contributing

Thanks for contributing to `saxsabs`. The canonical repository is
<https://github.com/D-sudoasd/AbsSAXS>.

## Get help or report a problem

- Report reproducible bugs through the [issue tracker](https://github.com/D-sudoasd/AbsSAXS/issues).
- Use a feature request when proposing a new workflow or capability.
- For a question that is neither a defect nor a proposal, contact the project
  maintainers through the repository before opening a broad pull request.

Please do not include beamline-private data, credentials, or large generated
outputs in an issue or pull request.

## Development setup

```bash
git clone https://github.com/D-sudoasd/AbsSAXS.git
cd SASAbs
python -m pip install -e ".[dev]"
pytest -q
ruff check SASAbs.py saxs_mpl_style.py src tests paper/*.py scripts/*.py
```

Install `.[gui]`, `.[hdf5]`, `.[io]`, or `.[bl19b2]` only when the change needs
those optional workflows.

## Pull requests

Keep pull requests focused. For a behavior change:

- add or update focused tests;
- keep reusable scientific logic in `src/saxsabs/` and GUI orchestration separate;
- update public CLI/API documentation when its behavior changes;
- run `pytest -q` and
  `ruff check SASAbs.py saxs_mpl_style.py src tests paper/*.py scripts/*.py`
  locally;
- describe the workflow, validation performed, and any remaining limitations.

Maintainers review pull requests for scientific input semantics, provenance,
reproducibility, and compatibility with supported optional dependencies.

## Release expectations

Releases are created from version tags after the validation workflow succeeds.
Before tagging, replace the `Unreleased` changelog heading with the ISO release
date, add the same `date-released` to `CITATION.cff`, and set its message to
`Cite the version-specific archive record for this release.` The release
metadata validator rejects provisional or inconsistent values.
Before describing a release-specific DOI in project metadata or release notes,
ensure Zenodo has archived that release and assigned its DOI. The project-level
concept DOI remains suitable for general project citation.

## Code of Conduct

This project follows the [Contributor Covenant Code of Conduct](https://www.contributor-covenant.org/version/2/1/code_of_conduct/).
Report unacceptable behaviour to the repository maintainer.
