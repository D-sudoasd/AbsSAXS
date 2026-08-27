# Architecture

## Layers

```
┌─────────────────────────────────────────────────┐
│  saxsabs_workbench.py   (launcher + logging)    │
│  SASAbs.py              (tkinter GUI, bilingual)│
├─────────────────────────────────────────────────┤
│  saxsabs.cli            (headless CLI)          │
│  saxsabs.workbench_launcher (installed launcher)│
├─────────────────────────────────────────────────┤
│  saxsabs.core.normalization  (monitor norms)    │
│  saxsabs.core.calibration    (K-factor est.)    │
│  saxsabs.core.material_attenuation (NIST 30 keV)│
│  saxsabs.core.mu_calculator  (Elam diagnostic μ)│
│  saxsabs.core.intensity_state (1D ledger)       │
│  saxsabs.core.workbench_preflight_gate          │
│  saxsabs.core.buffer_subtraction (BioSAXS)      │
│  saxsabs.core.fluorescence_subtraction (1D)     │
│  saxsabs.workflows.bl19b2_abs2d / integrate1d   │
│  saxsabs.io.parsers          (header + 1D I/O)  │
│  saxsabs.io.writers          (canSAS/NXcanSAS)  │
│  saxsabs.constants           (standards registry)│
└─────────────────────────────────────────────────┘
```

- **`saxsabs_workbench.py`**: application launcher with CLI flags (`--lang`, `--session`, `--version`), structured logging, and graceful error handling. Dynamically loads `SASAbs.py`.
- **`SASAbs.py`**: production GUI (tkinter) with full bilingual (中文 / English)
	internationalisation, multi-background capillary subtraction, and integrated
	calibration workflows.
- **`src/saxsabs/core`**: pure computation logic (normalization, robust
	K-factor estimation, fingerprinted NIST 30 keV material attenuation,
	xraydb/Elam diagnostic attenuation, 1D intensity/correction state, Workbench
	preflight fingerprints, buffer subtraction, and optional 1D fluorescence
	subtraction). No GUI side-effects —
	deterministic and testable.
- **`src/saxsabs/io`**: robust input parsing plus standard-format writers
	(canSAS XML and NXcanSAS HDF5).
- **`src/saxsabs/cli.py`**: eight headless subcommands: six focused utilities
  (`norm-factor`, `parse-header`, `parse-external1d`, `estimate-k`,
  `subtract-buffer`, `subtract-fluorescence`), the safety-first `bl19b2-abs2d`
  workflow, and the explicit `bl19b2-abs2d-v1-legacy` migration entry.
  `estimate-k`, `subtract-buffer`, and `subtract-fluorescence` apply the
  intensity-state gates; the first three utilities remain thin
  parsers/calculators. The legacy entry requires explicit monitor and
  thickness semantics and never silently restores v1 defaults.
- **`src/saxsabs/constants.py`**: pluggable reference-standard registry
	(SRM 3600, water, custom curves).
- **`src/saxsabs/workbench_launcher.py`**: packaged launcher used by
	`saxsabs-workbench` entry point.
- **`src/saxsabs/workflows`**: strict BL19B2 2D absolute-correction and 1D
  integration workflows. These are the campaign-grade provenance baseline;
  the Workbench still contains separate orchestration/scientific callbacks and
  is not yet an equivalent GUI front end to these runners.

## Release-safety contracts

- Calibration-record v2 verifies portable standard/background/dark/reference source paths, ordered SHA-256 identities, built-in reference model versions, integration settings, and robust-estimator parameters. Schema v1 remains readable but cannot authorize formal output.
- Tab 2 and Tab 3 formal outputs require a source-verified calibration record and an operator-compatible `CalibrationContext`. External 1D profiles must also carry matching operator provenance.
- BL19B2 schema v4 validates the complete K/QC contract. Shared background-monitor covariance is propagated jointly; unquantified shared raw-count/dark covariance keeps the combined budget explicitly `partial` and system expanded uncertainty unavailable.
- The reusable `saxsabs.io.calibrated2d` package publishes its multi-file package
  transactionally and resumes only after image, mask, PONI, context, and
  processing-parameter consistency checks. This contract does not make a strict
  BL19B2 whole campaign atomic.
- Detector arrays, headers, and source identities come from one stable snapshot; a source changed during reading is rejected before scientific output publication.
- Workbench formal Tab 2 is fixed-thickness only. The per-frame Beer-Lambert
  control and both Tab 2/Tab 3 existence-only resume controls are UI-disabled;
  forced values make Dry Check BLOCKED and are rejected again at Run. K and μ
  are read-only in Tab 2, and K is read-only in Tab 3.
- Workbench identities bind resolved path, size, mtime, and a streaming SHA-256
  for selected queue files and currently active configured inputs. A disabled
  optional field may retain a stale raw path, but its identity is normalized as
  disabled: it is not hashed and does not block Run. When that input is enabled,
  a missing, unreadable, or changing file is unverified and blocks Run; replacing
  content at the same path with the same size/mtime changes the preflight
  fingerprint. Changing a switch or configuration still invalidates approval;
  language refresh only redraws display text and retains current Tab 2/Tab 3
  approvals. `CAUTION` currently permits Run without a separately persisted
  acknowledgement; these are deliberate open boundaries, not properties of the
  strict runners. BG/Dark reference-library mutations explicitly invalidate the
  in-memory Tab 2 approval.
- Tab 3 raw correction is disabled. Formal K/Kd accepts only an explicitly
  reduced `relative` profile; `raw_counts`, `absolute_cm^-1`, and `ambiguous`
  states fail closed. K/d requires `d > 0`; K-only applies K without repeating
  thickness and requires inherited thickness in `corrections_applied`, a finite
  positive `thickness_cm`, and a non-empty `thickness_source`. Tab 3
  combines inherited corrections with the actual K, optional
  thickness, and optional buffer operations and records that set per frame;
  Tab 2 derives its ledger from the active detector context.
- `corrections_applied` and `do_not_repeat` are parsed separately and unioned for
  duplicate-operation checks. `do_not_repeat` is an execution guard, never proof
  of a required existing correction or absolute physical state; those claims must
  come from `corrections_applied`. If both are present but disagree, intensity
  state becomes ambiguous and formal scaling fails closed.
- Buffer subtraction is absolute-scale only: the buffer must declare
  `absolute_cm^-1`, `1/cm`, K+thickness in `corrections_applied`, no prior buffer
  subtraction, an explicit full active `CalibrationContext` fingerprint, and a
  numeric `k_factor` matching the active K. Operator-payload fallback is not
  sufficient. Dry Check also proves q-range coverage. State, unit, ledger,
  context fingerprint, `BufferKFactor`, `BufferAlphaUncertainty`, alpha, path,
  and hash enter audit output. Optional `u(alpha)` must be finite and non-negative;
  blank maps to `None`, preserving unknown combined uncertainty as NaN.
  The kernel returns the statistical component separately from the combined
  standard uncertainty. Text output writes both columns and uses the combined
  result as the legacy `Error_cm^-1` alias; canSAS/NXcanSAS carry the best
  available combined uncertainty and record the buffer's safe filename/SHA-256,
  alpha, `u(alpha)`, propagation model, and uncertainty type as operator
  provenance.
  The Workbench calls the shared core `subtract_buffer`; if it is unavailable,
  formal subtraction fails closed with no weaker local fallback.
- Fluorescence subtraction is opt-in and absolute-scale only. It is an additive
  1-D term `I_corr = I_abs − β F(q)` applied after K, thickness, and optional
  buffer. Methods are `constant`, `high_q_mean`, `high_q_median`, and
  `measured_profile`. High-q estimation is valid only where elastic SAXS is
  negligible in the stated window. The ledger token is `fluorescence`. Unknown
  `u(F0)` or `u(β)` keeps combined uncertainty NaN. The kernel never clips
  negative intensities. Detector-space NIST blank subtraction is unchanged:
  a q-independent 1-D constant must not be written back onto raw counts.
- The NIST 30 keV GUI export is a material-attenuation provenance JSON. It is
  invalidated whenever source/energy/preset/composition/density/porosity input
  changes. Nominal identity is inferred from the edited composition, not copied
  from the selected preset. PONI path/hash/energy are recorded; an available
  non-30 keV PONI is rejected. Missing PONI energy remains explicitly
  `not geometry-bound`. Elam output records xraydb version and cannot select the
  NIST-only porosity flag. This payload is still not a full per-folder thickness
  derivation anchored to accepted raw transmission frames.
  Export re-resolves and re-hashes PONI path, content, and energy, so changes
  after calculation require recalculation. Formal fixed Tab 2 metadata/preflight
  excludes diagnostic attenuation and records `mu_used_in_thickness_model=false`.

## Resource and publication boundaries

- FabIO handles go through one common copy-and-close helper
  (`saxsabs.io.detector_images`). The shared reference loader, the strict 2D
  main and resume readers, the integrate1d mask/EDF loaders, and Workbench
  detector-image paths copy pixels/header out and close the handle, including
  after a read failure. Callers can inject `open_image_fn` at the I/O edge.
- The reusable calibrated-2D package has transactional multi-file publication
  and signature-aware resume. Workbench existence-only resume is now disabled
  and hard-blocked, but no equivalent content-signature resume exists. The strict
  BL19B2 runner and Workbench both still lack atomic whole-campaign publication.
- The desktop UI has screen-aware initial geometry and a `900 x 600` minimum,
  but it still has no cancellable background `JobController`; high-volume work
  can therefore occupy the Tk event thread.

## Design goals

1. Preserve scientific behaviour from the existing BL19B2 workflow.
2. Make core math independent from GUI toolkits.
3. Enable CI validation and reviewer reproducibility.
4. Support bilingual operation for international beamline user communities.

## Supported boundary and known limitations

- **Implemented**: normalization, header parsing, external 1D parsing, robust K
  estimation, NIST 30 keV material core, Elam diagnostic calculator, 1D
  intensity ledger, signed-in-memory Workbench preflight, fixed-thickness
  enforcement, content-aware source identities, disabled legacy/resume controls,
  exact K-only/Kd/buffer gates,
  absolute-buffer validation, optional absolute 1D fluorescence subtraction,
  provenance-aware scrollable μ UI, disabled Tab 3 raw mode, screen-aware
  startup, strict BL19B2 workflows, standard writers, bilingual GUI, CLI, CI,
  and paper assets. K-only formal scaling requires both
  the inherited-thickness ledger entry and numeric/source provenance.
- **Strict campaign ownership**: formal multi-folder and per-sample campaigns
  remain owned by the strict CLI/batch runner. The Workbench is an interactive
  interface and is not advertised as an equivalent campaign owner.
- **Publication and resume**: reusable calibrated-2D packages are transactional,
  but whole-campaign atomic publication and content-signature resume are not
  implemented in the Workbench or strict runner. Existence-only Workbench resume
  is disabled rather than treated as safe.
- **Desktop operation**: long GUI jobs run on the Tk event thread and are not
  cancellable. Users should prefer headless workflows for unattended or large
  campaigns. Tab 2/Tab 3 progress resets at job entry and is marked failed on
  an outer run error, but whole-job atomic publication is not implemented.
  `CAUTION` remains visible but is not separately persisted as an
  acknowledgement.
- **Input resources**: Workbench and headless detector readers share
  `saxsabs.io.detector_images`. Reviewers should still use the documented
  portable fixtures rather than private beamline files.
