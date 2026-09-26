# Reviewer FAQ

This page explains the scope of the included verification evidence and the
software's documented limits. For JOSS's formal assessment, see the official
[review checklist](https://joss.readthedocs.io/en/latest/review_checklist.html)
and [review criteria](https://joss.readthedocs.io/en/latest/review_criteria.html).

## Why keep the root Workbench module?

The root module is the maintained Tk desktop application and compatibility
entry point. Reusable scientific and I/O logic lives under `src/saxsabs/`; the
GUI remains separate because the current Workbench and strict BL19B2 campaign
runner have intentionally different ownership boundaries.

## Is fluorescence the same as empty-cell or buffer subtraction?

No. Empty-cell / NIST-blank subtraction happens in detector space before
absolute scaling. Buffer subtraction removes solvent on the absolute
cm$^{-1}$ scale. Fluorescence subtraction is an optional additive 1-D term
applied after K, thickness, and optional buffer. It is off by default, does
not change $K$, and is not written onto 2D raw counts.

## How can this be tested without GUI?

Core logic is exposed as importable APIs and CLI commands. Tests run headlessly in CI.

## Data cannot be fully public. How is reproducibility addressed?

The repository includes synthetic examples, a deterministic raw-frame
validation package (`examples/minimal_2d/`), and automated tests. A manual
verification checklist documents exact commands and expected acceptance ranges.

## Can reviewers verify the numerical 2D chain without beamline data?

Yes. Run:

```bash
python examples/minimal_2d/run_minimal_2d_pipeline.py
```

The script constructs independent dark, blank, SRM 3600, and sample frames on a
9×9 array, subtracts a NIST blank in detector space, reduces with a homemade
integer-bin radial average (not pyFAI), gates the standard profile as
`relative` before $K$, writes labeled `absolute_cm^-1` outputs with unknown
uncertainty, and records those limits in `summary.json`. It does not run the
BL19B2 campaign runner. This is a software golden test, not measured beamline
validation or third-party format validation.

## Have the structured exports been checked outside the project readers?

Yes, with bounded offline checks that are not part of CI. On 26 September 2026,
the minimal example's XML output validated with zero errors against `cansas1d.xsd`
from the official canSAS `1dwg` repository (blob
`c376e590bf6c297ee5664834183b6d09b5684318`). In a separate check on 15 August
2026, the HDF5 output passed punx 0.3.5 against its bundled NeXus v2018.5
definitions with 97 OK, 0 WARN, and 0 ERROR findings. punx 0.3.5 could not parse
the current NeXus `main` definitions (commit `6313522`), so the project does not
claim validation against current definitions or a third-party application
consumer.

## Which revision should be reviewed?

Review the unreleased 2.0.0 source revision identified in the JOSS review
record. GitHub Release v1.1.1 is an earlier archive and is not this candidate.
Do not create `v2.0.0` or a new Zenodo version record during review.

## What is the software boundary?

`saxsabs` is a reusable SAXS absolute-calibration package with deterministic
software validation and a documented protocol for separate beamline acceptance.
