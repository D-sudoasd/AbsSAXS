# API and command-line reference

This page covers the public calculation and I/O functions exported by
`saxsabs`, plus the installed `saxsabs` command. Inputs are not inferred when
their physical meaning is ambiguous; callers must supply the applicable
measurement semantics and provenance.

## Core calculations

### Monitor normalization

```python
compute_norm_factor(exp: float | None, mon: float | None,
                    trans: float | None, mode: str) -> float
```

The `mode` describes how the beam monitor value was recorded. For `mode="rate"`,
`mon` is a monitor count rate in counts/s and `exp` is exposure time in seconds;
the normalization product is `exp * mon * trans`. For `mode="integrated"`,
`mon` is the integrated monitor count for the exposure and the product is
`mon * trans`; `exp` is ignored. Detector images are accumulated counts in both
modes. Transmission must be in `(0, 1]`; missing, non-positive, or non-finite
required values return `math.nan`. An unknown mode raises `ValueError`.

```python
from saxsabs import compute_norm_factor

# MON = 100,000 counts/s; exposure = 1 s; transmission = 0.8
factor = compute_norm_factor(1.0, 100000.0, 0.8, "rate")
assert factor == 80000.0

# Or supply 100,000 monitor counts integrated over the exposure.
assert compute_norm_factor(None, 100000.0, 0.8, "integrated") == 80000.0
```

### Robust K-factor estimation

```python
estimate_k_factor_robust(
    q_meas: np.ndarray, i_meas_per_cm: np.ndarray,
    q_ref: np.ndarray | None = None, i_ref: np.ndarray | None = None,
    q_window: tuple[float, float] = (0.01, 0.2),
    positive_floor: float = 1e-9, min_points: int = 3, *,
    i_ref_standard_uncertainty: np.ndarray | None = None,
    coverage_factor: float | None = None,
    standard_thickness_cm: float | None = None,
    parallelism_relative_tolerance: float | None = None,
) -> KFactorEstimationResult
```

Interpolates the measured profile on the reference q grid in `q_window`, forms
`I_ref / I_meas`, and applies median/MAD outlier rejection. If both reference
arrays are omitted, it uses the built-in NIST SRM 3600 reference and fails
closed if any ratio exceeds the certificate-derived relative-intensity limit
before that filter. K estimation needs a measured profile that has already been
reduced to `relative` intensity, with appropriate background/dark subtraction
and monitor/transmission normalization applied. Record the corrections in the
profile metadata and handle thickness with `--thickness-cm` when it has not
already been applied. The CLI state gate requires an explicit relative state and
refuses raw-count, ambiguous, and already absolute measured profiles. The
reference curve is absolute intensity in cm$^{-1}$. This array-based function
cannot inspect intensity-state metadata or correction history, so direct callers
must provide physically compatible arrays. The result contains the estimate
and diagnostics; inspect it before applying a scale.

For the built-in NIST SRM 3600 reference, use the certified mean coupon
thickness of 1.055 mm (0.1055 cm), rather than measuring each coupon separately.
The [NIST certificate](https://tsapps.nist.gov/srmext/certificates/3600.pdf)
includes coupon-to-coupon thickness variability in its reference uncertainty
(Table 1). In BL19B2 uncertainty accounting, set
`--standard-thickness-relative-standard-uncertainty 0.0` when there is no
additional independent thickness uncertainty; this avoids counting the same
coupon variability twice. Enter a nonzero value only for an additional
independently characterized thickness source that is absent from the reference
uncertainty and has negligible covariance with it. For a custom standard, supply
a separate relative thickness uncertainty only when its reference-curve
uncertainty excludes specimen thickness and their covariance is negligible.

```python
from saxsabs import estimate_k_factor_robust

result = estimate_k_factor_robust(q_meas, i_meas_per_cm, q_ref, i_ref)
print(result.k_factor, result.points_used)
```

### Attenuation and thickness

```python
calculate_mu(composition: dict[str, float], density_g_cm3: float,
             energy_keV: float) -> MuResult
calculate_material_attenuation(composition: Mapping[str, object], *,
    composition_basis: str, table: AttenuationTable = NIST_30_KEV_TABLE,
    material_key: str | None = None, material_name: str | None = None,
    porosity_risk: bool = False) -> MaterialAttenuationResult
derive_fixed_thickness(material: MaterialAttenuationResult,
    transmissions: Iterable[object], *,
    anchor_scope: str = "provided_transmissions",
    drift_warning_relative_span: float = ...) -> FixedThicknessDerivation
```

`calculate_mu` accepts element weight fractions or weight percent, bulk density
in g/cm³, and energy in keV. `calculate_material_attenuation` requires
`composition_basis="wt_fraction"` exactly, so wt% and atomic fractions are not
silently guessed. `derive_fixed_thickness` derives a fixed thickness from the
median supplied transmission and returns warnings alongside its provenance.

```python
from saxsabs import calculate_mu

mu = calculate_mu({"Ti": 0.9, "Nb": 0.1}, density_g_cm3=5.0, energy_keV=30.0)
print(mu.mu_linear_cm_inv)
```

### State checks, subtraction, and uncertainty

```python
assess_intensity_state(profile: Mapping[str, object]) -> IntensityStateAssessment
subtract_buffer(q_sample, i_sample, err_sample, q_buffer, i_buffer, err_buffer,
                alpha: float = 1.0, high_q_diag: tuple[float, float] = (0.15, 0.25),
                *, alpha_uncertainty: float | None = None,
                sample_profile: Mapping[str, object],
                buffer_profile: Mapping[str, object]) -> BufferSubtractionResult
subtract_fluorescence(q, i_abs, err_abs, *, sample_profile, method,
                f0=None, f0_uncertainty=None, beta=1.0, beta_uncertainty=None,
                high_q_window=None, q_fluorescence=None, i_fluorescence=None,
                err_fluorescence=None, fluorescence_profile=None,
                residual_window=None) -> FluorescenceSubtractionResult
propagate_absolute_uncertainty(intensity: np.ndarray, *,
    statistical_standard_uncertainty=None, k_relative_standard_uncertainty=None,
    standard_relative_standard_uncertainty=None,
    transmission_relative_standard_uncertainty=None,
    monitor_relative_standard_uncertainty=None,
    thickness_relative_standard_uncertainty=None,
    mu_relative_standard_uncertainty=None, alpha_standard_uncertainty=None,
    buffer_intensity=None, coverage_factor=None) -> AbsoluteUncertaintyBudget
```

`assess_intensity_state` classifies metadata, units, and correction information;
conflicting evidence remains ambiguous. A unitless metadata label `absolute` is
ambiguous and is not treated as cm$^{-1}$. `subtract_buffer` requires
`sample_profile` and `buffer_profile` provenance, interpolates a buffer onto
the sample q grid when necessary, and propagates supplied uncertainties.
`subtract_fluorescence` is an opt-in additive correction on absolute cm$^{-1}$
data after K, thickness, and optional buffer. Methods are `constant`,
`high_q_mean`, `high_q_median`, and `measured_profile`. A high-q constant is
valid only where elastic SAXS is negligible in that window. Missing `u(F0)` or
`u(β)` keeps combined uncertainty NaN. Negative intensities are reported, not
clipped. This is not detector-dark, NIST-blank, or solvent subtraction.
`propagate_absolute_uncertainty` combines statistical and supplied standard
uncertainty components; relative inputs must be relative standard uncertainties.

## I/O

```python
read_external_1d_profile(path: str | Path) -> dict[str, Any]
write_cansas1d_xml(path: str | Path, q: np.ndarray, i_abs: np.ndarray,
                   err: np.ndarray | None = None,
                   metadata: dict[str, Any] | None = None) -> Path
write_nxcansas_h5(path: str | Path, q: np.ndarray, i_abs: np.ndarray,
                  err: np.ndarray | None = None,
                  metadata: dict[str, Any] | None = None) -> Path
```

`read_external_1d_profile` reads supported text/tabular profiles and routes XML
and HDF5 extensions to canSAS/NXcanSAS readers. The returned mapping always
includes `intensity` and `uncertainty`. It adds `i_abs`/`err_abs` only for
assessed `absolute_cm^-1` profiles and `i_rel`/`err_rel` only for assessed
`relative` profiles. Writers expect q in Å⁻¹ and stamp `1/cm` only when
metadata declares `intensity_state=absolute_cm^-1` and an explicit cm⁻¹ unit.
NXcanSAS writing requires the optional `h5py` dependency.

```python
from saxsabs.io import profile_intensity, read_external_1d_profile

profile = read_external_1d_profile("examples/profile_example.csv")
print(profile["x"], profile_intensity(profile), profile.get("intensity_state"))
```

Do not assume `i_rel` is present. Call `write_cansas1d_xml` or
`write_nxcansas_h5` only after a validated calibration has established the
absolute intensity, uncertainty, units, and provenance.

Workbench K-only scaling is fail-closed: the imported relative profile must
declare `thickness` in `corrections_applied`, a finite positive
`thickness_cm`, and a non-empty `thickness_source`. These provenance keys are
preserved by the text, canSAS, and NXcanSAS paths so a downstream operation does
not rely on a ledger marker alone.

## Command line

Run `saxsabs --help` for the installed command and `saxsabs <command> --help`
for parameters. Required inputs are shown in angle brackets:

```text
saxsabs norm-factor --mon <monitor-rate-or-integrated-counts> --trans <0<T<=1> --mode <rate|integrated> [--exp <seconds>]
saxsabs parse-header --header-json <path>
saxsabs parse-external1d --input <path>
saxsabs estimate-k --meas <path> [--ref <path>] [--q-col <name>] [--i-col <name>]
                    [--ref-q-col <name>] [--ref-i-col <name>] [--qmin <value>] [--qmax <value>]
                    [--intensity-state relative] [--thickness-cm <cm>]
saxsabs subtract-buffer --sample <path> --buffer <path> [--alpha <value>]
                    [--alpha-uncertainty <value>]
saxsabs subtract-fluorescence --sample <path> --method <constant|high_q_mean|high_q_median|measured>
                    [--f0 <cm^-1>] [--f0-uncertainty <value>] [--beta <value>]
                    [--beta-uncertainty <value>] [--qmin <Å^-1>] [--qmax <Å^-1>]
                    [--fluorescence <path>]
saxsabs bl19b2-abs2d --input-root <path> (--poni <path>|--pydidas-cali-yaml <path>)
                         (--mu <cm^-1>|--sample-thickness-cm <cm>)
                         --monitor-mode <rate|integrated> [workflow options]
saxsabs bl19b2-abs2d-v1-legacy --input-root <path>
                                   (--poni <path>|--pydidas-cali-yaml <path>) [migration options]
```

For `norm-factor`, `rate` means `--mon` is a monitor rate in counts/s and requires
`--exp` in seconds. `integrated` means `--mon` is the monitor count integrated
over the acquisition interval; `--exp` is not used. Both modes normalize
accumulated detector counts and include sample transmission.

The main commands are:

| Command | Input | Output |
| --- | --- | --- |
| `norm-factor` | exposure, monitor, transmission, mode | normalization value |
| `parse-header` | header JSON | extracted exposure/monitor/transmission JSON |
| `parse-external1d` | profile path | parsed-profile summary JSON |
| `estimate-k` | relative measured profile; optional reference (built-in SRM 3600 if omitted); optional `--thickness-cm` | K-factor result JSON |
| `subtract-buffer` | absolute sample and buffer profiles with cm⁻¹ units | subtraction diagnostic JSON |
| `subtract-fluorescence` | absolute sample profile; constant, high-q window, or measured F(q) | fluorescence diagnostic JSON |
| `bl19b2-abs2d` | explicit BL19B2 inputs and semantics | batch result JSON and requested files |
| `bl19b2-abs2d-v1-legacy` | explicit migration choices | legacy-compatible batch result with documented assumptions |

The BL19B2 commands require explicit monitor mode and either attenuation
coefficient or fixed thickness. Read the [batch runbook](bl19b2_abs2d_batch_runbook.md)
for their full input contract and provenance requirements.

## Scientific boundary

These APIs provide software operations and checks; they do not establish that a
beamline measurement is calibrated. Users remain responsible for appropriate
reference standards, independently measured inputs, detector geometry, valid
units, and experiment-specific acceptance. The included synthetic 2D example recovers a planted $K$ and sample curve from
a 9×9 homemade radial average (not pyFAI) and checks labeled file content; it
is not experimental beamline validation.
