# SASAbs

<p align="center">
  <strong>Traceable absolute-intensity calibration for small-angle X-ray scattering.</strong><br>
  Python API · command-line workflows · bilingual desktop workbench
</p>

<p align="center">
  <a href="https://github.com/D-sudoasd/SASAbs/actions/workflows/ci.yml"><img src="https://github.com/D-sudoasd/SASAbs/actions/workflows/ci.yml/badge.svg" alt="Continuous integration status"></a>
  <a href="https://doi.org/10.5281/zenodo.19687103"><img src="https://img.shields.io/badge/DOI-10.5281%2Fzenodo.19687103-168AAD" alt="Zenodo concept DOI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-BSD--3--Clause-4C566A" alt="BSD-3-Clause license"></a>
  <img src="https://img.shields.io/badge/python-3.10%2B-3776AB" alt="Python 3.10 or later">
</p>

<p align="center">
  <img src="assets/readme/hero.svg" width="100%" alt="Measured SAXS intensity is calibrated against a reference and exported with provenance.">
</p>

`saxsabs` combines robust K-factor estimation, explicit intensity states,
reusable data writers, and provenance checks. The result and the processing
record remain reviewable together.

Version status:

- Current source candidate: branch [`main`](https://github.com/D-sudoasd/SASAbs),
  version `2.0.0`, unreleased.
- Stable archive: GitHub Release
  [`v1.1.1`](https://github.com/D-sudoasd/SASAbs/releases/tag/v1.1.1) release assets.
- The `2.0.0` candidate is source-only: no PyPI installation is documented, and
  no version tag, GitHub Release, or Zenodo version archive has been created.
  The DOI above is the project concept DOI.

<p align="center">
  <a href="#quick-start"><strong>Quick start</strong></a> ·
  <a href="#choose-a-workflow">Choose a workflow</a> ·
  <a href="docs/api.md">API reference</a> ·
  <a href="docs/architecture.md">Architecture</a> ·
  <a href="SUBMISSION_READINESS.md">Submission readiness</a> ·
  <a href="#citation">Citation</a>
</p>

## Quick start

Install from the repository and verify the headless CLI:

```bash
git clone https://github.com/D-sudoasd/SASAbs.git
cd SASAbs
python -m pip install -e .

saxsabs norm-factor --mode rate --exp 1.0 --mon 100000 --trans 0.8
# 80000.0
```

Launch the desktop application:

```bash
python -m pip install -e ".[gui]"
saxsabs-workbench --lang en
```

On Windows, `py -m pip install -e ".[gui]"` and `py saxsabs_workbench.py --lang en`
are equivalent Python-launcher forms.

The core package requires Python 3.10+, NumPy, pandas, and xraydb. The commands
above install from the source tree.

<details>
<summary><strong>Optional dependency groups</strong></summary>

```bash
python -m pip install -e ".[hdf5]"     # NXcanSAS HDF5
python -m pip install -e ".[io]"       # FabIO detector-image I/O
python -m pip install -e ".[bl19b2]"   # strict BL19B2 workflow
python -m pip install -e ".[dev]"      # tests and Ruff
```

The Workbench uses Tk. Windows and macOS Python installers commonly include it.
On Linux, install the distribution's Tk package (often `python3-tk`) if
`python -m tkinter` cannot open a test window. API and CLI workflows do not need
a display server.

</details>

## Choose a workflow

<p align="center">
  <img src="assets/readme/workflow.svg" width="100%" alt="Four SASAbs entry points converge on a traceable absolute-intensity result.">
</p>

| Route | Best for | Start here |
| --- | --- | --- |
| **CLI utilities** | normalization, header and 1D parsing, gated K estimation, gated buffer and fluorescence subtraction | `saxsabs --help` |
| **SAXSAbs Workbench** | interactive K calibration, batch processing, external-1D scaling | `saxsabs-workbench --lang en` |
| **Strict BL19B2 runner** | validated campaign inputs under current BL19B2 conventions | [batch runbook](docs/bl19b2_abs2d_batch_runbook.md) |
| **Python API** | reusable scientific calculations and file I/O | [API reference](docs/api.md) |

The routes share numerical and I/O modules where implemented, but the Workbench
is not presented as equivalent to the stricter BL19B2 campaign runner.

## What the software records

- reference-derived calibration using NIST SRM 3600, water, or a supplied profile;
- explicit `raw_counts`, `relative`, `absolute_cm^-1`, and `ambiguous` states;
- transmission, thickness, monitor semantics, units, and applied corrections;
- partial uncertainty status without silently substituting zero for unknown terms;
- source identity where available, calibration context, and processing metadata;
- CSV/TSV, canSAS1d XML, and optional NXcanSAS HDF5 outputs.

<details>
<summary><strong>Open the detailed architecture diagram</strong></summary>

<p align="center">
  <img src="paper/fig_workflow.png" width="100%" alt="SASAbs software architecture from user interfaces through scientific and I/O modules to traceable outputs.">
</p>

</details>

## Workbench

<p align="center">
  <img src="assets/readme/workbench.png" width="82%" alt="SAXSAbs Workbench in English showing calibration inputs, physical parameters, and the plotting area.">
</p>

The desktop interface exposes K-factor calibration, 2D batch processing,
external-1D scaling, and built-in help. The image above was captured from the
English interface in the current source tree; it is interface documentation,
not experimental evidence.

## Reproducible example

The bundled example plants deterministic synthetic dark, background,
standard, and sample frames on a 9×9 array, subtracts a NIST blank in detector
space, and reduces with a homemade integer-bin radial average (not pyFAI):

```bash
python examples/minimal_2d/run_minimal_2d_pipeline.py
```

It writes inspectable CSV, TSV, and XML outputs, plus HDF5 when `h5py` is
installed. The script gates the standard profile as `relative` before $K$,
writes `absolute_cm^-1` metadata, and checks that the XML exposes `i_abs`
rather than `i_rel`. The acceptance summary requires `k_relative_error < 0.005`
and `sample_max_relative_error < 0.01`. See the
[example documentation](examples/minimal_2d/README.md) for construction details
and expected files.

<p align="center">
  <img src="assets/readme/kfactor-demo.png" width="92%" alt="Deterministic synthetic K-factor example showing retained and rejected ratios.">
</p>

> This example recovers a planted synthetic $K$ and sample curve from a 9×9
> homemade radial average and checks labeled file content. It is not pyFAI
> integration, BL19B2 campaign validation, measured-beamline validation, or
> independent third-party format validation.

## Documentation

- [API reference](docs/api.md) — public functions, inputs, outputs, and boundaries
- [Architecture](docs/architecture.md) — module responsibilities and interface limits
- [BL19B2 runbook](docs/bl19b2_abs2d_batch_runbook.md) — strict 2D campaign path
- [Manual verification](examples/manual-verification.md) — GUI and workflow checks
- [Reviewer FAQ](docs/reviewer-faq.md) — evidence, scope, and known limitations
- [Submission readiness](SUBMISSION_READINESS.md) — verified checks and remaining gates
- [Author confirmation form](docs/author-confirmation-form.md) — author-controlled facts required before submission
- [Changelog](CHANGELOG.md) — version history

## Scope and limitations

Absolute calibration depends on a suitable reference, detector geometry,
monitor semantics, transmission, thickness, and instrument-specific provenance.
The strict 2D workflow currently targets BL19B2 conventions. canSAS1d and
NXcanSAS layouts are covered by project-local round-trip tests. An offline
check on 15 August 2026 validated the deterministic example against the official
canSAS1d 1.1 XSD and punx 0.3.5 with its bundled v2018.5 definitions; that check
is not in CI. Current NeXus definitions and third-party consumers have not been
verified.

## Development

The [continuous-integration workflow](https://github.com/D-sudoasd/SASAbs/actions/workflows/ci.yml)
tests the configured Python and operating-system matrix.

```bash
python -m pip install -e ".[dev,gui,bl19b2,hdf5]"
pytest -q
ruff check SASAbs.py saxs_mpl_style.py src tests paper/*.py scripts/*.py
```

Before submission, run the fail-closed local decision gate with Pandoc available:

```bash
python scripts/check_submission_readiness.py \
  --as-of YYYY-MM-DD \
  --manual-confirmations path/to/submission-confirmations.json
```

Run the strict command from the exact branch and commit that will be submitted.
The submitted branch and 40-character SHA must identify the same revision as the
public README and paper blobs and the successful CI run. A PASS recorded for an
earlier revision does not cover a later commit; update `submitted_branch` and
`submitted_commit` and rerun both gates.

After the strict local gate passes, verify the same commit, branch, visible
README and paper, repository identity, and successful CI run against GitHub:

```bash
python scripts/check_public_candidate.py \
  --confirmations path/to/submission-confirmations.json
```

When the paper remains outside the default branch, the command prints the exact
`@editorialbot set branch-where-paper-is ...` instruction required in the JOSS
pre-review issue. Remote mismatches or unavailable evidence fail closed.

Until the author-controlled fields are complete, use
`--allow-author-placeholders --as-of 2026-08-26` only for mechanical preflight.
That override is not submission authorization. Start from the
[confirmation JSON template](docs/submission-confirmations.example.json) only
after completing the author confirmation form.

Please use the [issue tracker](https://github.com/D-sudoasd/SASAbs/issues) for
reproducible problems and read [CONTRIBUTING.md](CONTRIBUTING.md) before opening
a pull request. Project participation follows the
[Code of Conduct](CODE_OF_CONDUCT.md).

## Citation

For the project as a whole, use the Zenodo concept DOI:

> Gong, D. *SASAbs*. https://doi.org/10.5281/zenodo.19687103

Use a release-specific DOI only for the archived release it identifies.
Machine-readable metadata are available in [CITATION.cff](CITATION.cff).

## License

SASAbs is distributed under the [BSD-3-Clause license](LICENSE).
