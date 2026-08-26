"""Additive fluorescence subtraction for absolute 1-D SAXS profiles.

Implements an opt-in correction on the absolute cm^-1 scale:

    I_corr(q)  = I_abs(q) − β × F(q)
    σ_corr²(q) = σ_abs²(q) + β² × σ_F²(q) + F(q)² × σ_β²

``F(q)`` is a non-negative additive term (sample X-ray fluorescence and any
q-independent inelastic background that remains after empty-cell subtraction).
It is applied after K, thickness, and optional buffer subtraction.  Unknown
uncertainties stay NaN.

This kernel is not detector-dark, NIST-blank, or solvent subtraction, and it
must not be applied in detector-count space without a solid-angle correction.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum

import numpy as np

from saxsabs.core.intensity_state import require_absolute_input_for_fluorescence_subtraction

DEFAULT_RESIDUAL_WINDOW = (0.15, 0.25)


class FluorescenceMethod(str, Enum):
    """How the additive fluorescence term ``F(q)`` is obtained."""

    CONSTANT = "constant"
    HIGH_Q_MEAN = "high_q_mean"
    HIGH_Q_MEDIAN = "high_q_median"
    MEASURED_PROFILE = "measured_profile"


@dataclass(frozen=True)
class FluorescenceSubtractionResult:
    """Container for fluorescence-subtracted SAXS data."""

    q: np.ndarray
    i_subtracted: np.ndarray
    err_subtracted: np.ndarray
    method: str
    beta: float
    f0: float
    f_profile: np.ndarray
    high_q_residual_mean: float | None = None
    high_q_check_passed: bool | None = None
    high_q_window: tuple[float, float] | None = None
    high_q_points: int = 0
    negative_fraction: float = 0.0
    beta_uncertainty: float | None = None
    f0_uncertainty: float | None = None
    err_statistical: np.ndarray | None = None


def parse_fluorescence_method(method: object) -> FluorescenceMethod:
    """Parse a method token; ``measured`` is accepted as measured_profile."""

    token = str(method or "").strip().lower().replace("-", "_")
    aliases = {
        "constant": FluorescenceMethod.CONSTANT,
        "high_q_mean": FluorescenceMethod.HIGH_Q_MEAN,
        "high_qmean": FluorescenceMethod.HIGH_Q_MEAN,
        "high_q_median": FluorescenceMethod.HIGH_Q_MEDIAN,
        "high_qmedian": FluorescenceMethod.HIGH_Q_MEDIAN,
        "measured": FluorescenceMethod.MEASURED_PROFILE,
        "measured_profile": FluorescenceMethod.MEASURED_PROFILE,
    }
    parsed = aliases.get(token)
    if parsed is None:
        raise ValueError(
            "fluorescence method must be constant, high_q_mean, high_q_median, "
            f"or measured_profile; got {method!r}"
        )
    return parsed


def _as_1d_float_array(
    name: str, values: np.ndarray | None, *, require_finite: bool = True
) -> np.ndarray:
    if values is None:
        raise ValueError(f"{name} is required")
    arr = np.asarray(values, dtype=np.float64)
    if arr.ndim != 1:
        raise ValueError(f"{name} must be a 1-D array")
    if require_finite and not np.all(np.isfinite(arr)):
        raise ValueError(f"{name} contains non-finite values")
    return arr


def _optional_nonnegative_uncertainty(name: str, value: float | None) -> float | None:
    if value is None:
        return None
    out = float(value)
    if not np.isfinite(out) or out < 0:
        raise ValueError(f"{name} must be finite and >= 0")
    return out


def _square_uncertainty(name: str, values: np.ndarray | float) -> np.ndarray:
    """Square uncertainty values without exposing floating-point overflow."""

    with np.errstate(over="ignore", invalid="ignore"):
        squared = np.square(values)
    if np.any(np.isinf(squared)):
        raise ValueError(f"{name} uncertainty propagation overflowed")
    return np.asarray(squared, dtype=np.float64)


def _validate_beta(beta: float) -> float:
    value = float(beta)
    if not np.isfinite(value) or value <= 0:
        raise ValueError("Fluorescence scale factor beta must be finite and > 0")
    return value


def _validate_f0(f0: float) -> float:
    value = float(f0)
    if not np.isfinite(value) or value < 0:
        raise ValueError("f0 must be finite and >= 0")
    return value


def _validate_window(
    window: tuple[float, float] | None, *, name: str
) -> tuple[float, float] | None:
    if window is None:
        return None
    try:
        q_lo, q_hi = (float(value) for value in window)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must contain two finite increasing values") from exc
    if not np.isfinite(q_lo) or not np.isfinite(q_hi) or q_lo >= q_hi:
        raise ValueError(f"{name} must contain two finite increasing values")
    return (q_lo, q_hi)


def _prepare_source_grid(
    q_source: np.ndarray,
    y_source: np.ndarray,
    *,
    label: str,
) -> tuple[np.ndarray, np.ndarray]:
    order = np.argsort(q_source)
    q_sorted = q_source[order]
    y_sorted = y_source[order]
    uq, inv = np.unique(q_sorted, return_inverse=True)
    if uq.size < 2:
        raise ValueError(f"{label} q grid must contain at least 2 unique points")
    if uq.size != q_sorted.size:
        y_sum = np.zeros_like(uq, dtype=np.float64)
        counts = np.zeros_like(uq, dtype=np.float64)
        for idx, group in enumerate(inv):
            y_sum[group] += y_sorted[idx]
            counts[group] += 1.0
        y_sorted = y_sum / np.clip(counts, 1.0, None)
        q_sorted = uq
    return q_sorted, y_sorted


def _interpolate_on_grid(
    q_target: np.ndarray,
    q_source: np.ndarray,
    y_source: np.ndarray,
    *,
    label: str,
) -> np.ndarray:
    q_src, y_src = _prepare_source_grid(q_source, y_source, label=label)
    tol = max(
        1e-12,
        1e-9 * max(abs(q_src[0]), abs(q_src[-1]), abs(q_target).max(initial=0.0)),
    )
    if np.min(q_target) < q_src[0] - tol or np.max(q_target) > q_src[-1] + tol:
        raise ValueError(
            f"sample q grid extends outside {label} q range "
            f"({q_src[0]:.6g} to {q_src[-1]:.6g})"
        )
    return np.interp(q_target, q_src, y_src)


def _prepare_variance_grid(
    q_source: np.ndarray,
    sigma_source: np.ndarray,
    *,
    label: str,
) -> tuple[np.ndarray, np.ndarray]:
    order = np.argsort(q_source)
    q_sorted = q_source[order]
    variance_sorted = _square_uncertainty(label, sigma_source[order])
    uq, inv = np.unique(q_sorted, return_inverse=True)
    if uq.size < 2:
        raise ValueError(f"{label} q grid must contain at least 2 unique points")
    if uq.size == q_sorted.size:
        return q_sorted, variance_sorted

    variance_of_mean = np.full(uq.shape, np.nan, dtype=np.float64)
    for group in range(uq.size):
        group_variance = variance_sorted[inv == group]
        if np.all(np.isfinite(group_variance)):
            with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
                value = group_variance.sum() / group_variance.size**2
            if not np.isfinite(value):
                raise ValueError(f"{label} uncertainty propagation overflowed")
            variance_of_mean[group] = float(value)
    return uq, variance_of_mean


def _interpolate_variance_on_grid(
    q_target: np.ndarray,
    q_source: np.ndarray,
    sigma_source: np.ndarray,
    *,
    label: str,
) -> np.ndarray:
    q_src, variance_src = _prepare_variance_grid(q_source, sigma_source, label=label)
    tol = max(
        1e-12,
        1e-9 * max(abs(q_src[0]), abs(q_src[-1]), abs(q_target).max(initial=0.0)),
    )
    if np.min(q_target) < q_src[0] - tol or np.max(q_target) > q_src[-1] + tol:
        raise ValueError(
            f"sample q grid extends outside {label} q range "
            f"({q_src[0]:.6g} to {q_src[-1]:.6g})"
        )

    upper = np.searchsorted(q_src, q_target, side="right")
    upper = np.clip(upper, 1, q_src.size - 1)
    lower = upper - 1
    span = q_src[upper] - q_src[lower]
    weight_upper = (q_target - q_src[lower]) / span
    weight_upper = np.clip(weight_upper, 0.0, 1.0)
    weight_lower = 1.0 - weight_upper

    out = np.full(q_target.shape, np.nan, dtype=np.float64)
    exact_lower = np.isclose(weight_upper, 0.0, rtol=0.0, atol=1e-14)
    exact_upper = np.isclose(weight_upper, 1.0, rtol=0.0, atol=1e-14)
    between = ~(exact_lower | exact_upper)
    out[exact_lower] = variance_src[lower[exact_lower]]
    out[exact_upper] = variance_src[upper[exact_upper]]
    known = between & np.isfinite(variance_src[lower]) & np.isfinite(variance_src[upper])
    out[known] = (
        np.square(weight_lower[known]) * variance_src[lower[known]]
        + np.square(weight_upper[known]) * variance_src[upper[known]]
    )
    return out


def _window_mask(q: np.ndarray, i: np.ndarray, window: tuple[float, float]) -> np.ndarray:
    q_lo, q_hi = window
    return (q >= q_lo) & (q <= q_hi) & np.isfinite(i)


def _estimate_high_q_constant(
    q: np.ndarray,
    i_abs: np.ndarray,
    window: tuple[float, float],
    *,
    use_median: bool,
) -> tuple[float, int]:
    mask = _window_mask(q, i_abs, window)
    n_points = int(mask.sum())
    if n_points < 3:
        raise ValueError("high_q window must contain at least 3 finite intensity points")
    values = i_abs[mask]
    estimate = float(np.median(values) if use_median else np.mean(values))
    if not np.isfinite(estimate) or estimate < 0:
        raise ValueError("estimated fluorescence constant must be finite and >= 0")
    return estimate, n_points


def _residual_diagnostics(
    q: np.ndarray,
    i_corr: np.ndarray,
    window: tuple[float, float],
) -> tuple[float | None, bool | None, int]:
    mask = _window_mask(q, i_corr, window)
    n_points = int(mask.sum())
    if n_points >= 3:
        residual_mean = float(np.mean(i_corr[mask]))
        residual_std = float(np.std(i_corr[mask]))
        check_ok = abs(residual_mean) < 3.0 * max(residual_std, 1e-30)
        return residual_mean, check_ok, n_points
    return None, None, n_points


def subtract_fluorescence(
    q: np.ndarray,
    i_abs: np.ndarray,
    err_abs: np.ndarray | None,
    *,
    sample_profile: Mapping[str, object] | None = None,
    method: str,
    f0: float | None = None,
    f0_uncertainty: float | None = None,
    beta: float = 1.0,
    beta_uncertainty: float | None = None,
    high_q_window: tuple[float, float] | None = None,
    q_fluorescence: np.ndarray | None = None,
    i_fluorescence: np.ndarray | None = None,
    err_fluorescence: np.ndarray | None = None,
    fluorescence_profile: Mapping[str, object] | None = None,
    residual_window: tuple[float, float] | None = None,
) -> FluorescenceSubtractionResult:
    """Subtract an additive fluorescence term from an absolute SAXS curve.

    Parameters
    ----------
    q, i_abs, err_abs
        Sample profile on the absolute cm^-1 scale.  Missing errors remain
        unknown (NaN).
    sample_profile
        Intensity-state provenance.  Required; unlabeled arrays are refused.
    method
        ``constant``, ``high_q_mean``, ``high_q_median``, or ``measured_profile``.
    f0, f0_uncertainty
        User constant and its standard uncertainty.  Required for ``constant``.
        Forbidden for ``high_q_*`` and ``measured_profile``.  ``None``
        uncertainty keeps the combined result unknown.
    beta, beta_uncertainty
        Scale applied to ``F(q)``.  ``None`` uncertainty keeps combined
        uncertainty unknown; pass ``0.0`` only when β is treated as exact.
    high_q_window
        Required for ``high_q_*`` methods.
    q_fluorescence, i_fluorescence, err_fluorescence, fluorescence_profile
        Measured additive curve for ``measured_profile``.
    residual_window
        High-q diagnostic window.  Defaults to ``high_q_window`` when present,
        otherwise ``(0.15, 0.25)``.
    """
    if sample_profile is None:
        raise ValueError(
            "subtract_fluorescence requires sample_profile with explicit "
            "absolute_cm^-1 intensity_state and a cm^-1 intensity_unit"
        )
    require_absolute_input_for_fluorescence_subtraction(
        sample_profile, profile_name="sample"
    )
    parsed_method = parse_fluorescence_method(method)
    beta_value = _validate_beta(beta)
    f0_uncertainty = _optional_nonnegative_uncertainty("f0_uncertainty", f0_uncertainty)
    beta_uncertainty = _optional_nonnegative_uncertainty(
        "beta_uncertainty", beta_uncertainty
    )
    high_q_window = _validate_window(high_q_window, name="high_q_window")
    residual_window = _validate_window(residual_window, name="residual_window")

    q_s = _as_1d_float_array("q", q)
    i_s = _as_1d_float_array("i_abs", i_abs)
    if q_s.shape != i_s.shape:
        raise ValueError("q and i_abs shape mismatch")
    e_s = (
        _as_1d_float_array("err_abs", err_abs, require_finite=False)
        if err_abs is not None
        else np.full_like(i_s, np.nan)
    )
    if e_s.shape != i_s.shape:
        raise ValueError("err_abs shape mismatch")
    if np.any(np.isinf(e_s)):
        raise ValueError("err_abs contains infinite values")
    if np.any(np.isfinite(e_s) & (e_s < 0)):
        raise ValueError("err_abs contains negative values")

    estimate_points = 0
    f_variance: np.ndarray
    if parsed_method is FluorescenceMethod.CONSTANT:
        if f0 is None:
            raise ValueError("constant fluorescence method requires f0")
        if high_q_window is not None:
            raise ValueError("constant fluorescence method does not accept high_q_window")
        if fluorescence_profile is not None or i_fluorescence is not None:
            raise ValueError("constant fluorescence method does not accept a measured curve")
        f0_value = _validate_f0(f0)
        f_profile = np.full_like(i_s, f0_value)
        if f0_uncertainty is None:
            f_variance = np.full_like(i_s, np.nan)
        else:
            f_variance = np.full_like(
                i_s,
                _square_uncertainty("f0", f0_uncertainty),
            )
    elif parsed_method in {
        FluorescenceMethod.HIGH_Q_MEAN,
        FluorescenceMethod.HIGH_Q_MEDIAN,
    }:
        if f0 is not None:
            raise ValueError("high_q fluorescence methods estimate f0 and refuse a user f0")
        if high_q_window is None:
            raise ValueError("high_q fluorescence methods require high_q_window")
        if fluorescence_profile is not None or i_fluorescence is not None:
            raise ValueError("high_q fluorescence methods do not accept a measured curve")
        f0_value, estimate_points = _estimate_high_q_constant(
            q_s,
            i_s,
            high_q_window,
            use_median=parsed_method is FluorescenceMethod.HIGH_Q_MEDIAN,
        )
        f_profile = np.full_like(i_s, f0_value)
        if f0_uncertainty is None:
            f_variance = np.full_like(i_s, np.nan)
        else:
            f_variance = np.full_like(
                i_s,
                _square_uncertainty("f0", f0_uncertainty),
            )
    else:
        if f0 is not None:
            raise ValueError("measured_profile refuses a scalar f0")
        if high_q_window is not None:
            raise ValueError("measured_profile does not accept high_q_window")
        if f0_uncertainty is not None:
            raise ValueError("measured_profile uses curve uncertainties, not f0_uncertainty")
        if fluorescence_profile is None:
            raise ValueError(
                "measured_profile requires fluorescence_profile with explicit "
                "absolute_cm^-1 intensity_state and a cm^-1 intensity_unit"
            )
        require_absolute_input_for_fluorescence_subtraction(
            fluorescence_profile, profile_name="fluorescence"
        )
        q_f = _as_1d_float_array("q_fluorescence", q_fluorescence)
        i_f = _as_1d_float_array("i_fluorescence", i_fluorescence)
        if q_f.shape != i_f.shape:
            raise ValueError("q_fluorescence and i_fluorescence shape mismatch")
        if np.any(np.isfinite(i_f) & (i_f < 0)):
            raise ValueError("i_fluorescence contains negative values")
        e_f = (
            _as_1d_float_array("err_fluorescence", err_fluorescence, require_finite=False)
            if err_fluorescence is not None
            else np.full_like(i_f, np.nan)
        )
        if e_f.shape != i_f.shape:
            raise ValueError("err_fluorescence shape mismatch")
        if np.any(np.isinf(e_f)):
            raise ValueError("err_fluorescence contains infinite values")
        if np.any(np.isfinite(e_f) & (e_f < 0)):
            raise ValueError("err_fluorescence contains negative values")
        if q_s.shape != q_f.shape or not np.allclose(q_s, q_f, rtol=0.0, atol=1e-8):
            f_profile = _interpolate_on_grid(
                q_s, q_f, i_f, label="fluorescence"
            )
            f_variance = _interpolate_variance_on_grid(
                q_s, q_f, e_f, label="fluorescence uncertainty"
            )
        else:
            f_profile = i_f
            f_variance = _square_uncertainty("err_fluorescence", e_f)
        finite_f = f_profile[np.isfinite(f_profile)]
        f0_value = float(np.mean(finite_f)) if finite_f.size else float("nan")
        if not np.isfinite(f0_value) or f0_value < 0:
            raise ValueError("measured fluorescence intensity must be finite and >= 0")
        f0_uncertainty = None

    with np.errstate(over="ignore", invalid="ignore"):
        subtracted_term = beta_value * f_profile
    if np.any(np.isinf(subtracted_term)):
        raise ValueError("fluorescence subtraction produced non-finite intensity")
    i_corr = i_s - subtracted_term
    if np.any(np.isinf(i_corr)):
        raise ValueError("fluorescence subtraction produced non-finite intensity")

    beta_squared = _square_uncertainty("beta", beta_value)
    sample_variance = _square_uncertainty("err_abs", e_s)
    with np.errstate(over="ignore", invalid="ignore"):
        variance_statistical = sample_variance + beta_squared * f_variance
    if np.any(np.isinf(variance_statistical)):
        raise ValueError("fluorescence uncertainty propagation overflowed")
    if parsed_method is not FluorescenceMethod.MEASURED_PROFILE and f0_uncertainty is None:
        # Unknown u(F0) is a combined-budget gap, not a missing sample error.
        variance_statistical = sample_variance
    err_statistical = np.sqrt(variance_statistical)
    if beta_uncertainty is None or (
        parsed_method is not FluorescenceMethod.MEASURED_PROFILE and f0_uncertainty is None
    ):
        variance_combined = np.full_like(i_s, np.nan)
    else:
        with np.errstate(over="ignore", invalid="ignore"):
            beta_term = f_profile * beta_uncertainty
        beta_variance = _square_uncertainty("beta", beta_term)
        with np.errstate(over="ignore", invalid="ignore"):
            variance_combined = variance_statistical + beta_variance
        if np.any(np.isinf(variance_combined)):
            raise ValueError("fluorescence uncertainty propagation overflowed")
    err_combined = np.sqrt(variance_combined)
    if np.any(np.isinf(err_statistical)) or np.any(np.isinf(err_combined)):
        raise ValueError("fluorescence uncertainty propagation overflowed")

    diag_window = residual_window
    if diag_window is None:
        diag_window = high_q_window if high_q_window is not None else DEFAULT_RESIDUAL_WINDOW
    residual_mean, check_ok, residual_points = _residual_diagnostics(q_s, i_corr, diag_window)
    report_points = estimate_points if estimate_points else residual_points
    finite = np.isfinite(i_corr)
    if finite.any():
        negative_fraction = float(np.mean(i_corr[finite] < 0.0))
    else:
        negative_fraction = float("nan")

    return FluorescenceSubtractionResult(
        q=q_s,
        i_subtracted=i_corr,
        err_subtracted=err_combined,
        method=parsed_method.value,
        beta=beta_value,
        f0=f0_value,
        f_profile=f_profile,
        high_q_residual_mean=residual_mean,
        high_q_check_passed=check_ok,
        high_q_window=high_q_window,
        high_q_points=report_points,
        negative_fraction=negative_fraction,
        beta_uncertainty=beta_uncertainty,
        f0_uncertainty=f0_uncertainty,
        err_statistical=err_statistical,
    )


def combine_sequential_standard_uncertainties(
    previous_statistical: np.ndarray,
    previous_combined: np.ndarray | None,
    next_statistical: np.ndarray,
    next_combined: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Compose two additive steps without mixing extras into the statistical term.

    ``next_statistical`` must have been computed using ``previous_statistical``
    as the incoming sample uncertainty.  Any unknown combined term stays NaN.
    """
    stat = np.asarray(next_statistical, dtype=np.float64)
    nxt = np.asarray(next_combined, dtype=np.float64)
    prev_stat = np.asarray(previous_statistical, dtype=np.float64)
    prev_comb = (
        None
        if previous_combined is None
        else np.asarray(previous_combined, dtype=np.float64)
    )
    if (
        stat.shape != nxt.shape
        or prev_stat.shape != stat.shape
        or (prev_comb is not None and prev_comb.shape != prev_stat.shape)
    ):
        raise ValueError("all uncertainty arrays must have exactly equal shapes")
    supplied_arrays = (prev_stat, stat, nxt)
    if prev_comb is not None:
        supplied_arrays += (prev_comb,)
    if any(np.any(np.isinf(values)) for values in supplied_arrays):
        raise ValueError("sequential uncertainty inputs must not contain infinities")
    if previous_combined is None:
        return stat, nxt
    assert prev_comb is not None
    with np.errstate(over="ignore", invalid="ignore"):
        prev_comb_squared = np.square(prev_comb)
        prev_stat_squared = np.square(prev_stat)
        next_comb_squared = np.square(nxt)
        next_stat_squared = np.square(stat)
    if any(
        np.any(np.isinf(values))
        for values in (
            prev_comb_squared,
            prev_stat_squared,
            next_comb_squared,
            next_stat_squared,
        )
    ):
        raise ValueError("sequential uncertainty propagation overflowed")
    extra_prev = prev_comb_squared - prev_stat_squared
    extra_next = next_comb_squared - next_stat_squared
    extra_prev = np.clip(extra_prev, 0.0, None)
    extra_next = np.clip(extra_next, 0.0, None)
    with np.errstate(over="ignore", invalid="ignore"):
        combined = np.sqrt(next_stat_squared + extra_prev + extra_next)
    if np.any(np.isinf(combined)):
        raise ValueError("sequential uncertainty propagation overflowed")
    unknown = (
        ~np.isfinite(prev_comb)
        | ~np.isfinite(nxt)
        | ~np.isfinite(prev_stat)
        | ~np.isfinite(stat)
    )
    combined = np.where(unknown, np.nan, combined)
    return stat, combined
