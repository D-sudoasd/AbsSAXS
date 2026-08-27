"""Command-line interface for headless SAXS calibration operations.

Provides eight subcommands: six small utilities plus the safe BL19B2 workflow
and its explicit v1 migration entry.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import re
import sys
import unicodedata

import numpy as np
import pandas as pd

from . import __version__
from .core.buffer_subtraction import subtract_buffer
from .core.fluorescence_subtraction import subtract_fluorescence
from .core.calibration import estimate_k_factor_robust
from .core.intensity_state import require_relative_input_for_absolute_scaling
from .core.normalization import compute_norm_factor
from .io.parsers import (
    _attach_intensity_arrays,
    _normalise_inferred_header_columns,
    _physical_data_width,
    _read_plain_header_tokens,
    _read_comment_header_dataframe,
    _unit_delimiters_are_balanced,
    parse_header_values,
    profile_intensity,
    profile_uncertainty,
    read_external_1d_profile,
    canonicalize_q_unit,
    infer_q_unit_from_column,
    q_column_unit_hint,
    q_axis_kind,
)


def _die(message: str) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(1)


_EXPECTED_INPUT_ERRORS = (OSError, UnicodeError, ValueError, TypeError, ImportError)


def _clean_column_name(name: object) -> str:
    return "".join(ch for ch in str(name).strip().lower() if ch.isalnum())


def _column_score(name: str, role: str) -> int:
    raw_name = str(name)
    name = _clean_column_name(name)
    if role == "q":
        exact = {"q", "chi", "radial", "2theta", "twotheta", "s", "x"}
        prefixes = ("chi", "radial", "twotheta")
        suffixes = ("q",)
    else:
        exact = {"i", "intensity", "irel", "iabs", "signal", "count", "counts", "y"}
        prefixes = ("intensity", "signal", "count", "irel", "iabs")
        suffixes = ("intensity",)

    if name in exact:
        return 300
    if role == "q" and q_axis_kind(raw_name) == "q":
        return 200
    if any(name.startswith(prefix) and len(name) > len(prefix) for prefix in prefixes):
        return 200
    if any(name.endswith(suffix) and len(name) > len(suffix) for suffix in suffixes):
        return 150
    return 0


def _available_columns_message(columns: list[object]) -> str:
    return "Available columns: " + ", ".join(str(col) for col in columns)


def _read_tabular_dataframe(path: Path) -> pd.DataFrame:
    comment_header_df = _read_comment_header_dataframe(path)
    if comment_header_df is not None:
        return comment_header_df

    errors: list[str] = []
    header_tokens = _read_plain_header_tokens(path)
    data_width = _physical_data_width(path)
    read_trials = [
        {"sep": None, "engine": "python", "comment": "#"},
        {"sep": r"[,\s;]+", "engine": "python", "comment": "#"},
    ]
    for kwargs in read_trials:
        try:
            df = pd.read_csv(path, **kwargs)
        except Exception as exc:
            errors.append(str(exc))
            continue
        if df is not None and not df.empty and df.shape[1] >= 2:
            df = _normalise_inferred_header_columns(
                df,
                header_tokens=header_tokens,
                data_width=data_width,
            )
            return df

    detail = f" ({'; '.join(errors[:2])})" if errors else ""
    raise ValueError(f"Cannot parse tabular profile for column overrides: {path.name}{detail}")


def _resolve_column(
    columns: list[object],
    requested: str | None,
    role: str,
    profile_label: str,
) -> object:
    if requested:
        if requested in columns:
            return requested
        requested_clean = _clean_column_name(requested)
        matches = [col for col in columns if _clean_column_name(col) == requested_clean]
        if role == "intensity" and requested_clean == "i":
            matches.extend(
                col
                for col in columns
                if re.fullmatch(
                    r"i\s*(?:[([{][^()\[\]{}]*[)\]}])?", str(col).strip(), re.IGNORECASE
                )
                and col not in matches
            )
        if len(matches) == 1:
            return matches[0]
        raise ValueError(
            f"{profile_label} {role} column '{requested}' not found. "
            f"{_available_columns_message(columns)}"
        )

    best_col = None
    best_score = 0
    for col in columns:
        score = _column_score(col, role)
        if score > best_score:
            best_col = col
            best_score = score
    if best_col is not None:
        return best_col

    raise ValueError(
        f"Cannot identify {profile_label} {role} column. {_available_columns_message(columns)}"
    )


def _has_explicit_q_unit_hint(raw_hint: object, x_col: object) -> bool:
    """Recognize unit-like hints while allowing semantic names such as ``q_ref``."""

    hint = str(raw_hint or "").strip().lower()
    column = unicodedata.normalize("NFKC", str(x_col or "")).lower()
    text = f"{hint} {column}"
    if any(marker in text for marker in ("^", "/", "⁻", "−", "inverse")):
        return True
    if any(char in column for char in "()[]{}"):
        return True
    return any(
        re.search(rf"(?<![a-z]){token}(?![a-z])", text)
        for token in ("a", "angstrom", "nm", "mm", "cm", "m", "um", "pm")
    )


def _is_bare_q_length_header(x_col: object) -> bool:
    """Reject ``Q (nm)``/``Q (angstrom)`` before they become reciprocal Q."""

    text = unicodedata.normalize("NFKC", str(x_col or "")).strip().lower()
    text = text.replace("å", "angstrom").replace("Å", "angstrom")
    if not text.startswith("q"):
        return False
    suffix = re.sub(r"[^a-z0-9]+", "", text[1:])
    return suffix in {"a", "angstrom", "nm", "mm", "cm", "m", "um", "pm"}


def _unitless_column_prefix(name: object) -> str:
    text = str(name or "").strip()
    prefix = re.split(r"[\s(\[{_:]", text, maxsplit=1)[0]
    return _clean_column_name(prefix)


def _q_selector_matches_unitful_profile(requested: object, resolved: object) -> bool:
    prefix_match = (
        _clean_column_name(requested) == _unitless_column_prefix(resolved)
        and _clean_column_name(requested) != _clean_column_name(resolved)
    )
    if not prefix_match:
        return False
    if q_axis_kind(resolved) == "q":
        return True
    unit, raw_hint = _explicit_q_unit_from_header(resolved)
    return unit is not None or raw_hint is not None


def _explicit_q_unit_from_header(name: object) -> tuple[str | None, str | None]:
    """Extract a complete explicit reciprocal-unit suffix from any header."""

    inferred = infer_q_unit_from_column(name)
    if inferred is not None:
        return inferred, None

    text = unicodedata.normalize("NFKC", str(name or "").strip().lower())
    matching = {"(": ")", "[": "]", "{": "}"}
    delimiter_chars = set(matching) | set(matching.values())
    if any(char in text for char in delimiter_chars):
        bracketed = re.fullmatch(
            r"([a-z][a-z0-9_]*)\s*([([{])(.*)([)\]}])",
            text,
        )
        if bracketed is None:
            return None, text
        opener = bracketed.group(2)
        if (
            matching[opener] != bracketed.group(4)
            or not _unit_delimiters_are_balanced(text)
        ):
            return None, text
        candidate = bracketed.group(3).strip()
        if not candidate or any(char in candidate for char in delimiter_chars):
            return None, text
        return canonicalize_q_unit(candidate), candidate

    candidates: list[str] = []
    for separator in ("_", ":", "-", " "):
        marker = text.find(separator)
        if marker > 0:
            candidates.append(text[marker + 1 :].strip())
    for candidate in candidates:
        if not candidate:
            continue
        canonical = canonicalize_q_unit(candidate)
        if canonical is not None or _has_explicit_q_unit_hint(candidate, text):
            return canonical, candidate
    return None, None


def _q_column_matches_profile_values(
    dataframe: pd.DataFrame,
    column: object,
    profile: dict[str, object],
) -> bool:
    try:
        source = pd.to_numeric(dataframe[column], errors="coerce").to_numpy(dtype=float)
        parsed = np.asarray(profile["x"], dtype=float)
    except (KeyError, TypeError, ValueError):
        return False
    source = np.sort(source[np.isfinite(source)])
    parsed = np.sort(parsed[np.isfinite(parsed)])
    return source.shape == parsed.shape and np.allclose(source, parsed, rtol=0.0, atol=1e-12)


def _read_profile_for_estimate(
    path: Path,
    *,
    q_col: str | None,
    i_col: str | None,
    profile_label: str,
) -> dict[str, object]:
    if q_col is None and i_col is None:
        return read_external_1d_profile(path)

    parsed_profile = read_external_1d_profile(
        path,
        allow_unidentified_intensity=i_col is not None,
    )
    requested_q_matches = q_col is None or (
        _clean_column_name(q_col) == _clean_column_name(parsed_profile.get("x_col", ""))
    )
    requested_i_matches = i_col is None or (
        _clean_column_name(i_col) == _clean_column_name(parsed_profile.get("i_col", ""))
    )
    if requested_q_matches and requested_i_matches:
        reused = dict(parsed_profile)
        reused["x_axis_override"] = q_col is not None
        if q_col is not None and not reused.get("x_unit"):
            resolved_name = str(reused.get("x_col", ""))
            selected_unit, selected_raw_hint = _explicit_q_unit_from_header(resolved_name)
            reused["x_unit"] = selected_unit or infer_q_unit_from_column(resolved_name)
            raw_q_hint = q_column_unit_hint(resolved_name)
            reused["x_unit_raw"] = (
                raw_q_hint
                if reused["x_unit"] is None
                and raw_q_hint
                and _has_explicit_q_unit_hint(raw_q_hint, resolved_name)
                else (selected_raw_hint or "") if reused["x_unit"] is None else ""
            )
        return reused

    df = _read_tabular_dataframe(path)
    columns = list(df.columns)
    preserve_parsed_q_metadata = False
    if q_col is not None and _q_selector_matches_unitful_profile(
        q_col, parsed_profile.get("x_col", "")
    ):
        try:
            raw_q_col = _resolve_column(columns, q_col, "q", profile_label)
        except ValueError:
            # Whitespace-delimited headers are normalized to the complete
            # parenthesized Q name.  A semantic ``Q`` selector may therefore
            # resolve through the parser-selected unit-bearing column.
            parsed_q_name = str(parsed_profile.get("x_col", ""))
            raw_q_col = next(
                (
                    column
                    for column in columns
                    if _clean_column_name(column) == _clean_column_name(parsed_q_name)
                ),
                None,
            )
            if raw_q_col is None:
                raise ValueError(
                    f"{profile_label} q selector {q_col!r} is ambiguous; "
                    "select the complete unit-bearing Q column"
                ) from None
        if not _q_column_matches_profile_values(df, raw_q_col, parsed_profile):
            raise ValueError(
                f"{profile_label} q selector {q_col!r} does not match the parsed Q column; "
                "refusing to discard its unit metadata"
            )
        resolved_q_col = raw_q_col
        preserve_parsed_q_metadata = True
    else:
        resolved_q_col = _resolve_column(columns, q_col, "q", profile_label)
    resolved_i_col = _resolve_column(columns, i_col, "intensity", profile_label)

    q = pd.to_numeric(df[resolved_q_col], errors="coerce").to_numpy(dtype=float)
    intensity = pd.to_numeric(df[resolved_i_col], errors="coerce").to_numpy(dtype=float)
    mask = np.isfinite(q) & np.isfinite(intensity)
    if int(mask.sum()) < 3:
        raise ValueError(
            f"{profile_label}: selected Q/intensity columns contain fewer than 3 finite rows"
        )
    order = np.argsort(q[mask])
    q = q[mask][order]
    intensity = intensity[mask][order]
    profile = dict(parsed_profile)
    profile["x"] = q
    profile["intensity"] = intensity
    profile["i_col"] = str(resolved_i_col)
    if preserve_parsed_q_metadata:
        profile["x_col"] = str(parsed_profile.get("x_col", resolved_q_col))
        selected_unit, selected_raw_hint = _explicit_q_unit_from_header(resolved_q_col)
        profile["x_unit"] = selected_unit
        profile["x_unit_raw"] = "" if selected_unit is not None else (selected_raw_hint or "")
    else:
        profile["x_col"] = str(resolved_q_col)
        selected_unit, selected_raw_hint = _explicit_q_unit_from_header(resolved_q_col)
        profile["x_unit"] = selected_unit or infer_q_unit_from_column(resolved_q_col)
        raw_q_hint = q_column_unit_hint(resolved_q_col)
        profile["x_unit_raw"] = (
            raw_q_hint
            if profile["x_unit"] is None
            and raw_q_hint
            and _has_explicit_q_unit_hint(raw_q_hint, resolved_q_col)
            else (selected_raw_hint or "") if profile["x_unit"] is None else ""
        )
    parsed_error_col = str(parsed_profile.get("err_col", "") or "").strip()
    error_source_col = next(
        (
            column
            for column in columns
            if parsed_error_col
            and _clean_column_name(column) == _clean_column_name(parsed_error_col)
        ),
        None,
    )
    if error_source_col is None:
        uncertainty = np.full(q.shape, np.nan, dtype=float)
    else:
        raw_uncertainty = pd.to_numeric(
            df[error_source_col], errors="coerce"
        ).to_numpy(dtype=float)
        if raw_uncertainty.shape == mask.shape:
            uncertainty = raw_uncertainty[mask][order]
            uncertainty = np.where(np.isfinite(uncertainty), uncertainty, np.nan)
        else:
            uncertainty = np.full(q.shape, np.nan, dtype=float)
    profile["uncertainty"] = uncertainty
    profile.pop("i_abs", None)
    profile.pop("i_rel", None)
    profile.pop("err_abs", None)
    profile.pop("err_rel", None)
    profile.pop("intensity_state", None)
    profile = _attach_intensity_arrays(profile, intensity, uncertainty)
    profile["x_axis_override"] = q_col is not None
    return profile


def _apply_declared_intensity_state(
    profile: dict[str, object],
    declared_state: str | None,
) -> dict[str, object]:
    if not declared_state:
        return profile
    provenance = dict(profile.get("operator_provenance") or {})
    provenance["intensity_state"] = declared_state
    updated = dict(profile)
    updated["operator_provenance"] = provenance
    updated["intensity_state"] = declared_state
    return updated


def _normalize_q_profile(
    profile: dict[str, object],
    *,
    profile_label: str = "profile",
) -> dict[str, object]:
    """Return a shallow profile copy whose Q values are in Å⁻¹.

    Parsers preserve source values and report ``x_unit``.  The numerical
    kernels used by these CLI commands have a single Å⁻¹ contract, so this is
    the only conversion boundary.  Calling it repeatedly is harmless because
    the returned profile is explicitly marked ``A^-1``.
    """

    x_col = str(profile.get("x_col", "")).strip()
    axis_kind = q_axis_kind(x_col)
    if axis_kind == "chi":
        raise ValueError(f"{profile_label}: chi is an angle axis, not Q")
    if axis_kind == "two_theta":
        raise ValueError(f"{profile_label}: 2theta requires an explicit wavelength conversion")
    if axis_kind == "unknown" and profile.get("x_axis_override"):
        axis_kind = "q"
    if axis_kind != "q":
        raise ValueError(
            f"{profile_label}: unsupported or non-Q axis {x_col!r}; expected a Q column"
        )
    if _is_bare_q_length_header(x_col):
        raise ValueError(
            f"{profile_label}: Q unit must explicitly state a reciprocal length "
            "(for example nm^-1 or 1/angstrom)"
        )

    raw_unit = profile.get("x_unit")
    declared_unit = canonicalize_q_unit(raw_unit) if raw_unit not in (None, "") else None
    if raw_unit not in (None, "") and declared_unit is None:
        raise ValueError(f"{profile_label}: unsupported Q unit {raw_unit!r}")
    raw_unit_hint = str(profile.get("x_unit_raw", "") or "").strip()
    if raw_unit_hint and declared_unit is None:
        if _has_explicit_q_unit_hint(raw_unit_hint, x_col):
            raise ValueError(f"{profile_label}: unsupported Q unit {raw_unit_hint!r}")
        # Semantic suffixes such as ``q_ref`` are historical aliases for a
        # bare q column, not unit declarations.  Keep rejecting unit-like
        # unknown hints while preserving that CLI compatibility policy.
        raw_unit_hint = ""
    inferred_unit = infer_q_unit_from_column(x_col)
    if declared_unit is not None and inferred_unit is not None and declared_unit != inferred_unit:
        raise ValueError(
            f"{profile_label}: Q unit metadata conflicts with column {x_col!r}"
        )
    source_unit = declared_unit or inferred_unit
    if source_unit is None:
        # A bare q column is the historical CLI contract and is interpreted
        # as Å⁻¹; no conversion is applied.
        source_unit = "A^-1"

    try:
        x = np.asarray(profile["x"], dtype=np.float64)
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"{profile_label}: Q values must be numeric") from exc
    if x.ndim != 1 or not np.all(np.isfinite(x)):
        raise ValueError(f"{profile_label}: Q values must be a finite 1-D array")

    conversion = "none"
    if source_unit == "nm^-1":
        x = x / 10.0
        conversion = "nm^-1_to_A^-1"
    elif source_unit == "m^-1":
        x = x * 1.0e-10
        conversion = "m^-1_to_A^-1"

    updated = dict(profile)
    updated["x"] = x.copy()
    updated["x_unit"] = "A^-1"
    updated["x_col"] = "Q_A^-1"
    provenance = dict(profile.get("operator_provenance") or {})
    normalized_input = x_col == "Q_A^-1" and source_unit == "A^-1"
    if normalized_input:
        provenance.setdefault("q_unit_original", str(profile.get("x_unit") or source_unit))
        provenance.setdefault("q_unit_conversion", conversion)
    else:
        provenance["q_unit_original"] = str(profile.get("x_unit") or source_unit)
        provenance["q_unit_conversion"] = conversion
    updated["operator_provenance"] = provenance
    return updated


def _add_bl19b2_arguments(
    parser: argparse.ArgumentParser,
    *,
    legacy_v1: bool = False,
) -> None:
    parser.add_argument("--input-root", required=True, type=Path)
    geometry = parser.add_mutually_exclusive_group(required=True)
    geometry.add_argument("--poni", type=Path)
    geometry.add_argument("--pydidas-cali-yaml", type=Path)
    parser.add_argument("--mask", type=Path, default=None)
    parser.add_argument("--dark", type=Path, default=None, help="Explicit BL19B2 dark reference TIFF")
    parser.add_argument(
        "--background",
        type=Path,
        default=None,
        help="Explicit BL19B2 background TIFF",
    )
    parser.add_argument(
        "--standard",
        type=Path,
        default=None,
        help="Explicit BL19B2 standard TIFF",
    )
    parser.add_argument(
        "--direct-beam",
        type=Path,
        default=None,
        help="Optional direct-beam provenance TIFF (no transmission QC is applied)",
    )
    parser.add_argument("--output-root", type=Path, default=None)

    parser.add_argument(
        '--include-manifest',
        type=Path,
        default=None,
        help='UTF-8 CSV allowlist with a required relative_path column',
    )
    parser.add_argument(
        '--thickness-derivation-json',
        type=Path,
        default=None,
        help='JSON provenance for a configured fixed sample thickness',
    )

    thickness_mode = parser.add_mutually_exclusive_group(required=not legacy_v1)
    thickness_mode.add_argument(
        "--mu",
        type=float,
        default=None,
        help=(
            "mu in cm^-1 for Beer-Lambert thickness d=-ln(ABS)/mu; "
            "must match material and X-ray energy"
        ),
    )
    thickness_mode.add_argument(
        "--sample-thickness-cm",
        type=float,
        default=None,
        help="Fixed sample thickness in cm; mutually exclusive with --mu",
    )
    if legacy_v1:
        thickness_mode.add_argument(
            "--legacy-assume-mu-20-2",
            action="store_const",
            const=20.2,
            dest="mu",
            help=(
                "Explicitly reproduce the historical v1 implicit mu=20.2 cm^-1; "
                "use only when material and X-ray energy match that assumption"
            ),
        )

    if legacy_v1:
        monitor_mode = parser.add_mutually_exclusive_group()
        monitor_mode.add_argument("--monitor-mode", choices=["rate", "integrated"])
        monitor_mode.add_argument(
            "--legacy-assume-monitor-rate",
            action="store_const",
            const="rate",
            dest="monitor_mode",
            help="Explicitly reproduce the historical v1 rate-monitor assumption",
        )
    else:
        parser.add_argument(
            "--monitor-mode",
            choices=["rate", "integrated"],
            required=True,
            help="Whether MON is a rate (normalization exp*MON*T) or integrated counts (MON*T)",
        )

    parser.add_argument("--transmission-abs-uncertainty", type=float, default=None)
    parser.add_argument("--monitor-relative-standard-uncertainty", type=float, default=None)
    parser.add_argument(
        "--sample-thickness-relative-standard-uncertainty",
        type=float,
        default=None,
    )
    parser.add_argument(
        "--standard-thickness-relative-standard-uncertainty",
        type=float,
        default=None,
        help="Relative standard uncertainty of the calibration-standard thickness",
    )
    parser.add_argument(
        "--standard-transmission-abs-uncertainty",
        type=float,
        default=None,
    )
    parser.add_argument(
        "--standard-monitor-relative-standard-uncertainty",
        type=float,
        default=None,
    )
    parser.add_argument(
        "--calibration-background-monitor-relative-standard-uncertainty",
        type=float,
        default=None,
    )
    parser.add_argument("--system-coverage-factor", type=float, default=None)
    parser.add_argument("--mu-relative-standard-uncertainty", type=float, default=None)
    parser.add_argument("--alpha-standard-uncertainty", type=float, default=None)
    parser.add_argument("--alpha", type=float, default=1.0, help="background scaling factor")
    parser.add_argument("--qmin", type=float, default=0.01)
    parser.add_argument("--qmax", type=float, default=0.2)
    parser.add_argument("--npt", type=int, default=1000)
    parser.add_argument("--max-frames", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--no-preview", action="store_true")
    parser.add_argument("--dtype", choices=["float32", "float64"], default="float32")
    parser.add_argument("--standard-thickness-cm", type=float, default=None)
    parser.add_argument(
        "--standard-key",
        default="SRM3600",
        help="Reference-curve key used for standard calibration (default: SRM3600)",
    )
    solid_angle = parser.add_mutually_exclusive_group()
    solid_angle.add_argument(
        "--correct-solid-angle-for-k",
        action="store_true",
        dest="correct_solid_angle_for_k",
        help="Apply solid-angle correction during 1D integration used to estimate K",
    )
    solid_angle.add_argument(
        "--no-correct-solid-angle-for-k",
        action="store_false",
        dest="correct_solid_angle_for_k",
        help="Do not apply solid-angle correction during K estimation",
    )
    polarization = parser.add_mutually_exclusive_group()
    polarization.add_argument(
        "--polarization-factor",
        type=float,
        default=None,
        help="Polarization factor applied during 1D integration used to estimate K",
    )
    polarization.add_argument(
        "--no-polarization-correction",
        action="store_const",
        const=None,
        dest="polarization_factor",
        help="Explicitly disable polarization correction during K estimation",
    )
    parser.set_defaults(correct_solid_angle_for_k=True, polarization_factor=None)
    parser.add_argument(
        "--dark-hot-pixel-threshold",
        type=float,
        default=10.0,
        help="Dark pixels with abs(dark) greater than this detector count value are added to the mask",
    )


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="saxsabs", description="SAXS absolute intensity utilities")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    p_norm = sub.add_parser("norm-factor", help="Compute normalization factor")
    p_norm.add_argument("--exp", type=float, default=None)
    p_norm.add_argument("--mon", type=float, required=True)
    p_norm.add_argument("--trans", type=float, required=True)
    p_norm.add_argument("--mode", choices=["rate", "integrated"], required=True)

    p_head = sub.add_parser("parse-header", help="Parse header JSON file and extract exp/mon/trans")
    p_head.add_argument("--header-json", required=True, type=Path)

    p_profile = sub.add_parser("parse-external1d", help="Parse external 1D profile file")
    p_profile.add_argument("--input", required=True, type=Path)

    p_k = sub.add_parser("estimate-k", help="Estimate robust K-factor from measured and reference CSV")
    p_k.add_argument(
        "--meas",
        required=True,
        type=Path,
        help="Measured profile on the same intensity scale as the reference (cm^-1 for SRM 3600)",
    )
    p_k.add_argument(
        "--ref",
        default=None,
        type=Path,
        help="Reference profile CSV; omit to use the built-in NIST SRM 3600 curve",
    )
    p_k.add_argument("--q-col", default=None, help="Measured q column override")
    p_k.add_argument("--i-col", default=None, help="Measured intensity column override")
    p_k.add_argument("--ref-q-col", default=None, help="Reference q column override")
    p_k.add_argument("--ref-i-col", default=None, help="Reference intensity column override")
    p_k.add_argument("--qmin", type=float, default=0.01)
    p_k.add_argument("--qmax", type=float, default=0.2)
    p_k.add_argument(
        "--intensity-state",
        default=None,
        help="Declare measured intensity_state when the file has no provenance "
        "(relative required for K estimation)",
    )
    p_k.add_argument(
        "--thickness-cm",
        type=float,
        default=None,
        help=(
            "Standard thickness in cm used to convert measured intensity to cm^-1 "
            "before K estimation. Workbench Tab 1 enters millimetres "
            "(1.055 mm = 0.1055 cm)."
        ),
    )

    p_sub = sub.add_parser(
        "subtract-buffer",
        help="Subtract an absolute buffer from an absolute sample profile",
    )
    p_sub.add_argument("--sample", required=True, type=Path)
    p_sub.add_argument("--buffer", required=True, type=Path)
    p_sub.add_argument("--alpha", type=float, default=1.0)
    p_sub.add_argument("--alpha-uncertainty", type=float, default=None)

    p_fluo = sub.add_parser(
        "subtract-fluorescence",
        help="Subtract additive fluorescence from an absolute sample profile",
    )
    p_fluo.add_argument("--sample", required=True, type=Path)
    p_fluo.add_argument(
        "--method",
        required=True,
        choices=["constant", "high_q_mean", "high_q_median", "measured"],
        help="How F(q) is obtained",
    )
    p_fluo.add_argument("--f0", type=float, default=None, help="Constant F0 in cm^-1")
    p_fluo.add_argument("--f0-uncertainty", type=float, default=None)
    p_fluo.add_argument("--beta", type=float, default=1.0)
    p_fluo.add_argument("--beta-uncertainty", type=float, default=None)
    p_fluo.add_argument("--qmin", type=float, default=None, help="High-q window minimum")
    p_fluo.add_argument("--qmax", type=float, default=None, help="High-q window maximum")
    p_fluo.add_argument(
        "--fluorescence",
        type=Path,
        default=None,
        help="Measured additive fluorescence profile",
    )

    p_bl = sub.add_parser(
        "bl19b2-abs2d",
        help="Process BL19B2 data with explicit monitor and thickness semantics",
        epilog=(
            "Historical v1 commands must use bl19b2-abs2d-v1-legacy and explicitly "
            "select the former monitor and attenuation assumptions."
        ),
    )
    _add_bl19b2_arguments(p_bl)

    p_bl_legacy = sub.add_parser(
        "bl19b2-abs2d-v1-legacy",
        help="Migrate historical BL19B2 v1 commands without silently restoring old defaults",
        description=(
            "Legacy migration entry. Monitor semantics and thickness must still be explicit; "
            "the legacy-assume flags document the historical v1 assumptions in provenance."
        ),
    )
    _add_bl19b2_arguments(p_bl_legacy, legacy_v1=True)
    return p


def main() -> None:
    args = build_parser().parse_args()
    if args.command == "norm-factor":
        out = compute_norm_factor(args.exp, args.mon, args.trans, args.mode)
        if not math.isfinite(out):
            _die(
                "Invalid normalization factor: non-finite result. "
                "Check that mon > 0, trans must be 0 < T <= 1, "
                "and exp > 0 for rate mode."
            )
        print(out)
        return

    if args.command == "parse-header":
        try:
            header = json.loads(args.header_json.read_text(encoding="utf-8-sig"))
            if not isinstance(header, dict):
                raise ValueError("header JSON top level must be an object")
            exp, mon, trans = parse_header_values(header)
        except _EXPECTED_INPUT_ERRORS as exc:
            _die(f"parse-header failed: {exc}")
        print(json.dumps({"exp_s": exp, "i0": mon, "trans": trans}, ensure_ascii=False))
        return

    if args.command == "parse-external1d":
        try:
            result = read_external_1d_profile(args.input)
        except _EXPECTED_INPUT_ERRORS as exc:
            _die(f"parse-external1d failed: {exc}")
        print(
            json.dumps(
                {
                    "points": int(result["x"].size),
                    "x_col": result["x_col"],
                    "x_unit": result.get("x_unit"),
                    "i_col": result["i_col"],
                    "err_col": result["err_col"],
                    "intensity_state": result.get("intensity_state"),
                },
                ensure_ascii=False,
            )
        )
        return

    if args.command == "estimate-k":
        try:
            measured = _apply_declared_intensity_state(
                _read_profile_for_estimate(
                    args.meas,
                    q_col=args.q_col,
                    i_col=args.i_col,
                    profile_label="measured",
                ),
                args.intensity_state,
            )
            measured = _normalize_q_profile(measured, profile_label="measured")
            assessment = require_relative_input_for_absolute_scaling(
                measured, profile_name=str(args.meas)
            )
            i_meas = profile_intensity(measured)
            if args.thickness_cm is not None:
                thickness_cm = float(args.thickness_cm)
                if not math.isfinite(thickness_cm) or thickness_cm <= 0:
                    raise ValueError("--thickness-cm must be finite and > 0")
                if "thickness" in assessment.corrections_applied:
                    raise ValueError(
                        "measured profile already records thickness; "
                        "refuse a second --thickness-cm"
                    )
                i_meas = i_meas / thickness_cm
            if args.ref is None:
                if args.ref_q_col is not None or args.ref_i_col is not None:
                    raise ValueError("--ref-q-col and --ref-i-col require --ref")
                out = estimate_k_factor_robust(
                    q_meas=measured["x"],
                    i_meas_per_cm=i_meas,
                    q_window=(args.qmin, args.qmax),
                )
            else:
                reference = _read_profile_for_estimate(
                    args.ref,
                    q_col=args.ref_q_col,
                    i_col=args.ref_i_col,
                    profile_label="reference",
                )
                reference = _normalize_q_profile(reference, profile_label="reference")
                out = estimate_k_factor_robust(
                    q_meas=measured["x"],
                    i_meas_per_cm=i_meas,
                    q_ref=reference["x"],
                    i_ref=profile_intensity(reference),
                    q_window=(args.qmin, args.qmax),
                )
        except _EXPECTED_INPUT_ERRORS as exc:
            _die(f"estimate-k failed: {exc}")
        print(
            json.dumps(
                {
                    "k_factor": out.k_factor,
                    "k_std": out.k_std,
                    "k_std_semantics": "inlier ratio scatter; not combined K uncertainty",
                    "k_statistical_standard_uncertainty": (
                        out.k_statistical_standard_uncertainty
                    ),
                    "k_standard_uncertainty": out.k_standard_uncertainty,
                    "k_expanded_uncertainty": out.k_expanded_uncertainty,
                    "coverage_factor": out.coverage_factor,
                    "q_min_overlap": out.q_min_overlap,
                    "q_max_overlap": out.q_max_overlap,
                    "points_used": out.points_used,
                    "points_total": out.points_total,
                },
                ensure_ascii=False,
            )
        )
        return

    if args.command == "subtract-buffer":
        try:
            sample = _normalize_q_profile(
                read_external_1d_profile(args.sample), profile_label="sample"
            )
            buffer_profile = _normalize_q_profile(
                read_external_1d_profile(args.buffer), profile_label="buffer"
            )
            result = subtract_buffer(
                sample["x"],
                profile_intensity(sample),
                profile_uncertainty(sample),
                buffer_profile["x"],
                profile_intensity(buffer_profile),
                profile_uncertainty(buffer_profile),
                alpha=args.alpha,
                alpha_uncertainty=args.alpha_uncertainty,
                sample_profile=sample,
                buffer_profile=buffer_profile,
            )
        except _EXPECTED_INPUT_ERRORS as exc:
            _die(f"subtract-buffer failed: {exc}")
        print(
            json.dumps(
                {
                    "points": int(result.q.size),
                    "alpha": result.alpha,
                    "alpha_uncertainty": result.alpha_uncertainty,
                    "high_q_residual_mean": result.high_q_residual_mean,
                    "high_q_check_passed": result.high_q_check_passed,
                },
                ensure_ascii=False,
            )
        )
        return

    if args.command == "subtract-fluorescence":
        try:
            sample = _normalize_q_profile(
                read_external_1d_profile(args.sample), profile_label="sample"
            )
            high_q_window = None
            if args.qmin is not None or args.qmax is not None:
                if args.qmin is None or args.qmax is None:
                    raise ValueError("--qmin and --qmax must be provided together")
                high_q_window = (args.qmin, args.qmax)
            q_fluo = i_fluo = err_fluo = None
            fluo_profile = None
            if args.fluorescence is not None:
                fluo_profile = _normalize_q_profile(
                    read_external_1d_profile(args.fluorescence),
                    profile_label="fluorescence",
                )
                q_fluo = fluo_profile["x"]
                i_fluo = profile_intensity(fluo_profile)
                err_fluo = profile_uncertainty(fluo_profile)
            result = subtract_fluorescence(
                sample["x"],
                profile_intensity(sample),
                profile_uncertainty(sample),
                sample_profile=sample,
                method=args.method,
                f0=args.f0,
                f0_uncertainty=args.f0_uncertainty,
                beta=args.beta,
                beta_uncertainty=args.beta_uncertainty,
                high_q_window=high_q_window,
                q_fluorescence=q_fluo,
                i_fluorescence=i_fluo,
                err_fluorescence=err_fluo,
                fluorescence_profile=fluo_profile,
            )
        except _EXPECTED_INPUT_ERRORS as exc:
            _die(f"subtract-fluorescence failed: {exc}")
        print(
            json.dumps(
                {
                    "points": int(result.q.size),
                    "method": result.method,
                    "beta": result.beta,
                    "beta_uncertainty": result.beta_uncertainty,
                    "f0": result.f0,
                    "f0_uncertainty": result.f0_uncertainty,
                    "high_q_residual_mean": result.high_q_residual_mean,
                    "high_q_check_passed": result.high_q_check_passed,
                    "high_q_points": result.high_q_points,
                    "negative_fraction": result.negative_fraction,
                },
                ensure_ascii=False,
            )
        )
        return

    if args.command in {"bl19b2-abs2d", "bl19b2-abs2d-v1-legacy"}:
        from .workflows.bl19b2_abs2d import BL19B2Abs2DConfig, run_bl19b2_abs2d

        if args.command == "bl19b2-abs2d-v1-legacy" and (
            args.monitor_mode is None
            or (args.mu is None and args.sample_thickness_cm is None)
        ):
            print(
                "Legacy v1 migration requires explicit monitor and thickness semantics. "
                "Provide --monitor-mode/--mu/--sample-thickness-cm, or explicitly select "
                "--legacy-assume-monitor-rate and --legacy-assume-mu-20-2.",
                file=sys.stderr,
            )
            raise SystemExit(2)

        out = run_bl19b2_abs2d(
            BL19B2Abs2DConfig(
                input_root=args.input_root,
                poni_path=args.poni,
                pydidas_cali_yaml=args.pydidas_cali_yaml,
                mask_path=args.mask,
                dark_path=args.dark,
                background_path=args.background,
                standard_path=args.standard,
                direct_path=args.direct_beam,
                output_root=args.output_root,
                include_manifest_path=args.include_manifest,
                thickness_derivation_path=args.thickness_derivation_json,
                mu_cm_inv=args.mu,
                sample_thickness_cm=args.sample_thickness_cm,
                monitor_mode=args.monitor_mode,
                transmission_abs_uncertainty=args.transmission_abs_uncertainty,
                monitor_relative_standard_uncertainty=(
                    args.monitor_relative_standard_uncertainty
                ),
                sample_thickness_relative_standard_uncertainty=(
                    args.sample_thickness_relative_standard_uncertainty
                ),
                standard_thickness_relative_standard_uncertainty=(
                    args.standard_thickness_relative_standard_uncertainty
                ),
                standard_transmission_abs_uncertainty=(
                    args.standard_transmission_abs_uncertainty
                ),
                standard_monitor_relative_standard_uncertainty=(
                    args.standard_monitor_relative_standard_uncertainty
                ),
                calibration_background_monitor_relative_standard_uncertainty=(
                    args.calibration_background_monitor_relative_standard_uncertainty
                ),
                system_coverage_factor=args.system_coverage_factor,
                mu_relative_standard_uncertainty=args.mu_relative_standard_uncertainty,
                alpha_standard_uncertainty=args.alpha_standard_uncertainty,
                alpha=args.alpha,
                q_window=(args.qmin, args.qmax),
                npt=args.npt,
                dtype=args.dtype,
                dry_run=args.dry_run,
                max_frames=args.max_frames,
                overwrite=args.overwrite,
                write_preview=not args.no_preview,
                standard_thickness_cm=args.standard_thickness_cm,
                standard_key=args.standard_key,
                correct_solid_angle_for_k=args.correct_solid_angle_for_k,
                polarization_factor=args.polarization_factor,
                dark_hot_pixel_threshold=args.dark_hot_pixel_threshold,
            )
        )
        print(json.dumps(out, ensure_ascii=False))
        if out.get("status") in {"partial", "failed"}:
            raise SystemExit(1)
        return


if __name__ == "__main__":
    main()
