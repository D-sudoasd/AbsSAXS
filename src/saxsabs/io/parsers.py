"""Robust parsing of SAXS instrument headers and external 1-D profiles.

This module addresses two common reproducibility pain points:

1. **Header heterogeneity** – different instruments store exposure time,
   monitor counts, and transmission under varying key names and units.
   :func:`parse_header_values` normalizes keys and coerces values.

2. **1-D text-format diversity** – external 1-D files come in CSV, space-
   delimited, and semicolon-delimited flavours, sometimes without a header
   row.  :func:`read_external_1d_profile` tries several parsing strategies
   and infers column roles heuristically.

3. **Community standard formats** – canSAS 1D XML (``urn:cansas1d:1.1``)
   and NXcanSAS HDF5 files can be read via :func:`read_cansas1d_xml` and
   :func:`read_nxcansas_h5` respectively.
"""

from __future__ import annotations

import csv
from io import StringIO
import re
import shlex
import unicodedata
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from saxsabs.core.intensity_state import (
    IntensityState,
    assess_intensity_state,
    is_cm_inv_intensity_unit,
)


FLOAT_PATTERN = re.compile(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?")
COMMA_THOUSANDS_PATTERN = re.compile(r"(?<!\d)[-+]?\d{1,3}(?:,\d{3})+(?:[eE][-+]?\d+)?(?!\d)")
_NONFINITE_NUMERIC_MARKERS = frozenset(
    {
        "nan",
        "+nan",
        "-nan",
        "inf",
        "+inf",
        "-inf",
        "infinity",
        "+infinity",
        "-infinity",
    }
)


def _is_numeric_syntax_token(value: object) -> bool:
    """Return whether a text token is numeric syntax for header detection.

    Explicit non-finite spellings are accepted here only to distinguish a
    headerless numeric first row from a textual header.  Downstream numeric
    parsing still applies its finite-value and uncertainty rules.
    """

    token = str(value).strip().lower()
    return FLOAT_PATTERN.fullmatch(token) is not None or token in _NONFINITE_NUMERIC_MARKERS


_SUPERSCRIPT_TRANSLATION = str.maketrans(
    {
        "⁰": "0",
        "¹": "1",
        "²": "2",
        "³": "3",
        "⁴": "4",
        "⁵": "5",
        "⁶": "6",
        "⁷": "7",
        "⁸": "8",
        "⁹": "9",
        "⁻": "-",
        "−": "-",
        "–": "-",
        "—": "-",
    }
)


_OPERATOR_PROVENANCE_ALIASES = {
    "calibrationcontextfingerprint": "calibration_context_fingerprint",
    "contextfingerprint": "calibration_context_fingerprint",
    "kfactor": "k_factor",
    "calibrationk": "k_factor",
    "formulaversion": "formula_version",
    "monitormode": "monitor_mode",
    "correctsolidangle": "correct_solid_angle",
    "polarizationfactor": "polarization_factor",
    "ponisha256": "poni_sha256",
    "geometrysha256": "poni_sha256",
    "masksha256": "mask_sha256",
    "flatsha256": "flat_sha256",
    "intensitystate": "intensity_state",
    "correctionsapplied": "corrections_applied",
    "donotrepeat": "do_not_repeat",
    "intensityunit": "intensity_unit",
    "thicknesscm": "thickness_cm",
    "inheritedthicknesscm": "thickness_cm",
    "thicknesssource": "thickness_source",
    "inheritedthicknesssource": "thickness_source",
    "buffersourcename": "buffer_source_name",
    "buffersourcesha256": "buffer_source_sha256",
    "bufferalpha": "buffer_alpha",
    "bufferalphauncertainty": "buffer_alpha_uncertainty",
    "fluorescencemethod": "fluorescence_method",
    "fluorescencef0": "fluorescence_f0",
    "fluorescencef0uncertainty": "fluorescence_f0_uncertainty",
    "fluorescencebeta": "fluorescence_beta",
    "fluorescencebetauncertainty": "fluorescence_beta_uncertainty",
    "fluorescencehighqwindow": "fluorescence_high_q_window",
    "fluorescencesourcename": "fluorescence_source_name",
    "fluorescencesourcesha256": "fluorescence_source_sha256",
    "uncertaintymodel": "uncertainty_model",
    "uncertaintytype": "uncertainty_type",
}


def profile_intensity(profile: dict[str, Any]) -> np.ndarray:
    """Return the intensity array without assuming a relative or absolute label."""

    for key in ("intensity", "i_abs", "i_rel"):
        if key in profile:
            return np.asarray(profile[key], dtype=np.float64)
    raise KeyError("profile has no intensity array")


def profile_uncertainty(profile: dict[str, Any]) -> np.ndarray:
    """Return the uncertainty array without assuming a relative or absolute label."""

    for key in ("uncertainty", "err_abs", "err_rel"):
        if key in profile:
            return np.asarray(profile[key], dtype=np.float64)
    raise KeyError("profile has no uncertainty array")


def _attach_intensity_arrays(
    payload: dict[str, Any],
    intensity: np.ndarray,
    uncertainty: np.ndarray,
) -> dict[str, Any]:
    """Expose intensity under a key that matches the assessed scientific state."""

    payload["intensity"] = intensity
    payload["uncertainty"] = uncertainty
    assessment = assess_intensity_state(payload)
    payload["intensity_state"] = assessment.state.value
    if assessment.state is IntensityState.ABSOLUTE_CM_INV:
        payload["i_abs"] = intensity
        payload["err_abs"] = uncertainty
    elif assessment.state is IntensityState.RELATIVE:
        payload["i_rel"] = intensity
        payload["err_rel"] = uncertainty
    return payload


def _operator_provenance_key(value: object) -> str | None:
    normalized = re.sub(r"[^a-z0-9]+", "", str(value).strip().lower())
    return _OPERATOR_PROVENANCE_ALIASES.get(normalized)


def _read_text_operator_provenance(path: str | Path) -> dict[str, str]:
    try:
        lines = Path(path).read_text(encoding="utf-8-sig", errors="strict").splitlines()
    except (OSError, UnicodeError):
        return {}
    provenance: dict[str, str] = {}
    for line in lines:
        stripped = line.strip()
        if not stripped.startswith("#"):
            continue
        match = re.match(
            r"^([^:=]+)\s*[:=]\s*(.*?)\s*$",
            stripped.lstrip("#").strip(),
        )
        if match is None:
            continue
        key = _operator_provenance_key(match.group(1))
        if key is not None:
            provenance[key] = match.group(2).strip()
    return provenance


def _normalise_unit_text(value: object) -> str:
    """Return a conservative ASCII token for a unit/header fragment."""

    text = unicodedata.normalize("NFKC", str(value or "").strip().lower())
    text = text.replace("å", "angstrom").replace("Å", "angstrom")
    text = re.sub(r"(?<=[a-z])(?:−|–|—)1", "^-1", text)
    text = text.translate(_SUPERSCRIPT_TRANSLATION)
    return text


def _unit_token(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", "", _normalise_unit_text(value))


def canonicalize_q_unit(value: object) -> str | None:
    """Canonicalize common reciprocal-length units used for a Q axis.

    Numeric Q values are intentionally left untouched by the parser.  Unknown
    or unsupported units return ``None`` instead of being guessed.  A bare
    length (``nm``/``angstrom``) is not reciprocal; the source must include
    ``1/``, an explicit ``-1`` exponent, or ``inverse``/``inv``.
    """

    if value is None:
        return None
    text = _normalise_unit_text(value)
    if not text or not _unit_delimiters_are_balanced(text):
        return None

    # A column label may include a leading Q (for example ``Q_A^-1``), but
    # the Q prefix is only syntax.  Remove it only at a token boundary so a
    # malformed name such as ``Q_nonsense_nm^-1`` cannot be rescued by a
    # substring match.
    if text.startswith("q") and (len(text) == 1 or not text[1].isalnum()):
        prefix = re.match(r"^q\s*(?:[_:\-]\s*)?", text)
        text = text[prefix.end() :] if prefix is not None else text[1:]

    # Parenthesized/square/braced unit forms are accepted only when the
    # delimiters wrap the complete unit token.  This rejects conflicting
    # forms such as ``Q (nm^-1) [A^-1]``.
    if text and text[:1] in "([{":
        matching = {"(": ")", "[": "]", "{": "}"}
        if not text.endswith(matching[text[0]]):
            return None
        text = text[1:-1].strip()

    unit = r"(?:a|angstrom|nm|m)"
    if re.fullmatch(rf"1\s*/\s*({unit})", text):
        matched_unit = re.fullmatch(rf"1\s*/\s*({unit})", text)
    else:
        matched_unit = None

    if matched_unit is None:
        matched_unit = re.fullmatch(rf"({unit})\s*(?:\^\s*)?-\s*1", text)
    if matched_unit is None:
        matched_unit = re.fullmatch(rf"(?:inverse|inv)\s*({unit})", text)
    if matched_unit is None:
        return None

    matched_name = matched_unit.group(1)
    if matched_name == "nm":
        return "nm^-1"
    if matched_name == "m":
        return "m^-1"
    return "A^-1"


def _unit_delimiters_are_balanced(text: str) -> bool:
    """Reject mismatched or unclosed unit delimiters before token inference."""

    matching = {"(": ")", "[": "]", "{": "}"}
    closing = set(matching.values())
    stack: list[str] = []
    for char in text:
        if char in matching:
            stack.append(matching[char])
        elif char in closing:
            if not stack or stack.pop() != char:
                return False
    return not stack


def q_axis_kind(name: object) -> str:
    """Classify a source X-column as Q, chi, two-theta, or unknown."""

    text = _normalise_unit_text(name).strip()
    if re.search(
        r"(?<![a-z0-9])(?:2theta|two[\s_:\-]*theta)(?=$|[^a-z0-9])",
        text,
        flags=re.IGNORECASE,
    ):
        return "two_theta"
    if re.search(r"(?<![a-z0-9])chi(?=$|[^a-z0-9])", text, flags=re.IGNORECASE):
        return "chi"
    # A leading ``q`` is not enough: quality/query/qwerty are ordinary text
    # fields.  Accept an explicit separator, a numeric suffix (q1), or a
    # directly bracketed unit (Q(...)); these are the unambiguous Q forms used
    # by common 1-D exporters.
    if re.fullmatch(r"q", text, flags=re.IGNORECASE):
        return "q"
    if re.fullmatch(
        r"q(?:a|angstrom|nm|m)(?:\s*\^?\s*-\s*1)",
        text,
        flags=re.IGNORECASE,
    ):
        return "q"
    if re.match(
        r"^q(?:\s*[_:\-]\s*|\s*[([{]|\s*\d+|\s+\S+)",
        text,
        flags=re.IGNORECASE,
    ):
        return "q"
    return "unknown"


def infer_q_unit_from_column(name: object) -> str | None:
    """Infer a canonical Q unit from a column header, without guessing plain Q."""

    if q_axis_kind(name) != "q":
        return None
    text = _normalise_unit_text(name)
    match = re.match(r"^q(?:\s*[_:\-]?\s*)(.*)$", text, flags=re.IGNORECASE)
    suffix = match.group(1) if match is not None else ""
    if not suffix.strip(" _-:()[]{}"):
        return None
    return canonicalize_q_unit("q_" + suffix)


def q_column_unit_hint(name: object) -> str | None:
    """Return an explicit, but possibly unsupported, Q-header unit hint."""

    if q_axis_kind(name) != "q":
        return None
    text = _normalise_unit_text(name)
    match = re.match(r"^q(?:\s*[_:\-]?\s*)(.*)$", text, flags=re.IGNORECASE)
    suffix = match.group(1) if match is not None else ""
    suffix = suffix.strip()
    if suffix[:1] in "_:-":
        suffix = suffix[1:].lstrip()
    if not suffix:
        return None
    if suffix[:1] in "([{":
        matching = {"(": ")", "[": "]", "{": "}"}
        opener = suffix[0]
        if (
            _unit_delimiters_are_balanced(suffix)
            and suffix.endswith(matching[opener])
        ):
            inner = suffix[1:-1].strip()
            return inner or suffix
    return suffix


def _q_header_has_unsupported_unit_syntax(name: object) -> bool:
    """Identify explicit Q-unit syntax that failed full-header parsing."""

    if q_axis_kind(name) != "q" or canonicalize_q_unit(name) is not None:
        return False
    text = _normalise_unit_text(name)
    hint = q_column_unit_hint(name)
    if not hint:
        return False
    if re.search(r"[\^/]|⁻|[−–—]|\b(?:inverse|inv)\b", text):
        return True
    if any(char in text for char in "()[]{}"):
        known_bare_units = {"a", "angstrom", "nm", "mm", "cm", "m", "um", "pm"}
        return hint not in known_bare_units or text.count("(") + text.count("[") + text.count("{") != 1
    return bool(
        re.search(
            r"(?<![a-z])(?:a|angstrom|nm|mm|cm|m|um|pm)(?:\^?-?\d+)",
            text,
        )
        or re.fullmatch(
            r"(?:inv|inverse)(?:a|angstrom|nm|mm|cm|m|um|pm)\d*",
            hint,
        )
    )


def _clean_column_name(name: Any) -> str:
    text = _normalise_unit_text(name).replace("σ", "sigma")
    return re.sub(r"[^a-z0-9]+", "", text)


def _error_column_preference(name: Any) -> int:
    """Rank explicit uncertainty semantics before source-column order."""

    normalized = _clean_column_name(name)
    if normalized in {"error", "errorcm1", "error1cm", "err", "errcm1", "idev"}:
        return 0
    if "combined" in normalized:
        return 1
    if "statistical" in normalized:
        return 3
    return 2


def _column_declares_absolute_cm_inv_header(value: object) -> bool:
    """Return whether an I/I_abs header explicitly carries cm^-1."""

    text = _normalise_unit_text(value).strip()
    match = re.match(r"^i(?:_?abs)?(?=$|[\s_:/([{])", text)
    if match is None:
        return False
    suffix = text[match.end() :].strip().strip("()[]{}").strip()
    return is_cm_inv_intensity_unit(suffix) or bool(
        re.fullmatch(r"/\s*cm", suffix)
    )


def _match_column_score(
    name: str,
    *,
    exact: set[str],
    prefixes: tuple[str, ...] = (),
    suffixes: tuple[str, ...] = (),
) -> int:
    if name in exact:
        return 300
    if any(name.startswith(prefix) and len(name) > len(prefix) for prefix in prefixes):
        return 200
    if any(name.endswith(suffix) and len(name) > len(suffix) for suffix in suffixes):
        return 150
    return 0


def _q_column_score(name: Any) -> int:
    """Score Q-like headers without accepting arbitrary q-prefixed words."""

    clean = _clean_column_name(name)
    if clean in {"q", "chi", "radial", "2theta", "twotheta", "s", "x"}:
        return 300
    if q_axis_kind(name) == "q":
        return 200
    text = _normalise_unit_text(name).strip()
    if re.search(r"(?:[_:\-\s])q$", text, flags=re.IGNORECASE):
        return 150
    if clean.startswith(("chi", "radial", "twotheta")):
        return 200
    return 0


def _intensity_column_score(name: Any) -> int:
    """Score intensity headers without treating every ``i...`` name as I."""

    clean = _clean_column_name(name)
    score = _match_column_score(
        clean,
        exact={
            "i",
            "intensity",
            "irel",
            "iref",
            "imeas",
            "iabs",
            "signal",
            "count",
            "counts",
            "y",
        },
        prefixes=("intensity", "signal", "count", "irel"),
        suffixes=("intensity",),
    )
    if clean.startswith("iabs") and (
        clean == "iabs" or _column_declares_absolute_cm_inv_header(name)
    ):
        score = max(score, 200)
    if _column_declares_absolute_cm_inv_header(name):
        score = max(score, 200)
    return score


def _pick_named_column(
    cols: list[Any],
    used: set[Any],
    *,
    exact: set[str],
    prefixes: tuple[str, ...] = (),
    suffixes: tuple[str, ...] = (),
) -> tuple[Any, bool]:
    best = None
    best_score = 0
    for col in cols:
        if col in used:
            continue
        if exact == {"q", "chi", "radial", "2theta", "twotheta", "s", "x"}:
            score = _q_column_score(col)
        elif exact == {
            "i",
            "intensity",
            "irel",
            "iref",
            "imeas",
            "iabs",
            "signal",
            "count",
            "counts",
            "y",
        }:
            score = _intensity_column_score(col)
        else:
            score = _match_column_score(
                _clean_column_name(col),
                exact=exact,
                prefixes=prefixes,
                suffixes=suffixes,
            )
        if score > best_score:
            best = col
            best_score = score
    return best, best_score > 0


def _comment_header_score(tokens: list[str]) -> int:
    score = 0
    for token in tokens:
        name = _clean_column_name(token)
        score += _q_column_score(token)
        score += _intensity_column_score(token)
        score += _match_column_score(
            name,
            exact={"err", "error", "errors", "sigma", "std", "stdev", "unc", "uncertainty", "idev"},
            prefixes=("err", "error", "sigma", "std", "unc", "idev"),
            suffixes=("error", "sigma", "uncertainty"),
        )
    return score


def _merge_parenthesized_header_tokens(
    tokens: list[str],
) -> list[str]:
    """Rejoin complete Q-unit syntax without absorbing an I/error column."""

    opening_to_closing = {"(": ")", "[": "]", "{": "}"}

    def consume_bracket_group(start: int) -> int | None:
        opener = tokens[start][:1]
        closer = opening_to_closing.get(opener)
        if closer is None:
            return None
        end = start
        while end < len(tokens):
            candidate = " ".join(tokens[start : end + 1])
            if candidate.endswith(closer) and _unit_delimiters_are_balanced(candidate):
                return end + 1
            end += 1
        return None

    def is_q_unit_token(token: str) -> bool:
        normalized = _normalise_unit_text(token).strip()
        if not normalized:
            return False
        if normalized in {
            "1",
            "/",
            "^",
            "-",
            "-1",
            "inverse",
            "inv",
            "a",
            "angstrom",
            "nm",
            "mm",
            "cm",
            "m",
            "um",
            "pm",
            "q",
        }:
            return True
        if re.fullmatch(
            r"(?:a|angstrom|nm|mm|cm|m|um|pm)(?:\^?-?\d+)?", normalized
        ):
            return True
        if re.fullmatch(
            r"(?:inv|inverse)(?:a|angstrom|nm|mm|cm|m|um|pm)\d*", normalized
        ):
            return True
        if canonicalize_q_unit(normalized) is not None:
            return True
        return any(marker in normalized for marker in ("/", "^", "⁻", "−"))

    merged: list[str] = []
    idx = 0
    while idx < len(tokens):
        token = tokens[idx]
        if q_axis_kind(token) == "q":
            parts = [token]
            end = idx + 1
            consumed = False
            while end < len(tokens):
                next_token = tokens[end]
                if _intensity_column_score(next_token) > 0 or _error_column_preference(next_token) < 2:
                    break
                if next_token[:1] in opening_to_closing:
                    bracket_end = consume_bracket_group(end)
                    if bracket_end is None:
                        break
                    parts.extend(tokens[end:bracket_end])
                    end = bracket_end
                    consumed = True
                    continue
                if is_q_unit_token(next_token):
                    parts.append(next_token)
                    end += 1
                    consumed = True
                    if canonicalize_q_unit(" ".join(parts)) is not None:
                        next_is_bracket = (
                            end < len(tokens)
                            and tokens[end][:1] in opening_to_closing
                        )
                        if not next_is_bracket:
                            break
                    continue
                break
            if consumed:
                merged.append(" ".join(parts))
                idx = end
                continue

        next_token = tokens[idx + 1] if idx + 1 < len(tokens) else ""
        opener = next_token[:1]
        closer = opening_to_closing.get(opener)
        if closer is not None:
            bracket_end = consume_bracket_group(idx + 1)
            if bracket_end is not None:
                merged.append(" ".join(tokens[idx:bracket_end]))
                idx = bracket_end
                continue
        merged.append(token)
        idx += 1
    return merged


def _has_malformed_unit_header_tokens(tokens: list[str]) -> bool:
    """Detect an unclosed or mismatched delimiter after a named Q column."""

    opening_to_closing = {"(": ")", "[": "]", "{": "}"}
    closing = set(opening_to_closing.values())
    for index, token in enumerate(tokens[:-1]):
        if q_axis_kind(token) != "q":
            continue
        next_token = tokens[index + 1]
        if q_axis_kind(next_token) == "q":
            return True
        opener = next_token[:1]
        expected = opening_to_closing.get(opener)
        if expected is None:
            continue
        for candidate in tokens[index + 1 :]:
            if candidate.endswith(expected):
                if not _unit_delimiters_are_balanced(candidate):
                    return True
                break
            if any(char in candidate for char in closing):
                return True
        else:
            return True
    return False


def _strip_inline_comment(line: str) -> str:
    in_quotes = False
    index = 0
    while index < len(line):
        char = line[index]
        if char == '"':
            if in_quotes and index + 1 < len(line) and line[index + 1] == '"':
                index += 2
                continue
            in_quotes = not in_quotes
        elif char == "#" and not in_quotes:
            return line[:index]
        index += 1
    return line


def _physical_width_from_data_lines(lines: list[str]) -> int:
    widths: list[int] = []
    for line in lines:
        stripped = _strip_inline_comment(line).strip()
        if not stripped or stripped.startswith("#"):
            continue
        widths.append(len(_tokenize_header_line(stripped)))
    if not widths:
        return 0
    if len(set(widths)) != 1:
        raise ValueError("data rows have inconsistent physical field widths")
    return widths[0]


def _physical_data_width(path: str | Path) -> int:
    lines = Path(path).read_text(encoding="utf-8-sig", errors="ignore").splitlines()
    first_data_index: int | None = None
    first_tokens: list[str] = []
    for index, line in enumerate(lines):
        stripped = _strip_inline_comment(line).strip()
        if not stripped or stripped.startswith("#"):
            continue
        first_data_index = index
        first_tokens = _tokenize_header_line(stripped)
        break
    if first_data_index is None:
        return 0
    first_is_numeric = all(_is_numeric_syntax_token(token) for token in first_tokens)
    data_lines = lines[first_data_index:] if first_is_numeric else lines[first_data_index + 1 :]
    return _physical_width_from_data_lines(data_lines)


def _read_plain_header_tokens(path: str | Path) -> list[str] | None:
    try:
        lines = Path(path).read_text(encoding="utf-8-sig", errors="ignore").splitlines()
    except ValueError:
        raise
    except Exception:
        return None
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            continue
        tokens = _tokenize_header_line(stripped)
        if len(tokens) >= 2 and any(
            not _is_numeric_syntax_token(token) for token in tokens
        ):
            return tokens
        return None
    return None


def _tokenize_header_line(line: str) -> list[str]:
    """Tokenize a header without splitting quoted fields or unit spaces."""

    text = str(line).strip()
    if not text:
        return []
    delimiter = ";" if ";" in text and "," not in text else "," if "," in text else None
    if delimiter is not None:
        return [field.strip() for field in next(csv.reader([text], delimiter=delimiter))]
    return [field.strip() for field in shlex.split(text, posix=True)]


def _normalise_inferred_header_columns(
    df: pd.DataFrame,
    *,
    header_tokens: list[str] | None = None,
    data_width: int | None = None,
) -> pd.DataFrame:
    """Rejoin parenthesized units in a header parsed by pandas.

    A whitespace-delimited header such as ``Q (nm^-1) I`` is read as three
    column names while its data still have three numeric columns.  The unit
    token is part of the Q label, not a data column; any remaining numeric
    column is retained as an unnamed column so it cannot be mistaken for I.
    """

    columns = [str(column) for column in (header_tokens or list(df.columns))]
    data_width = int(data_width if data_width is not None else df.shape[1])
    merged = _merge_parenthesized_header_tokens(columns)
    if merged != columns and len(merged) > data_width:
        raise ValueError(
            "header has more logical columns than the observed data width"
        )
    if merged == columns and header_tokens is None:
        return df
    if len(merged) < df.shape[1]:
        merged.extend(
            f"__unnamed_{index}"
            for index in range(len(merged), df.shape[1])
        )
    else:
        merged = merged[: df.shape[1]]
    out = df.copy()
    out.columns = merged
    return out


def _read_comment_header_dataframe(path: str | Path) -> pd.DataFrame | None:
    try:
        lines = Path(path).read_text(encoding="utf-8-sig", errors="ignore").splitlines()
    except Exception:
        return None

    header_candidates: list[tuple[int, list[str], int]] = []
    for idx, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            candidate = stripped.lstrip("#").strip()
            if not candidate or ":" in candidate or "=" in candidate:
                continue
            tokens = _tokenize_header_line(candidate)
            if _has_malformed_unit_header_tokens(tokens):
                raise ValueError("malformed Q-unit delimiter in comment header")
            score = _comment_header_score(tokens)
            if (
                len(tokens) >= 2
                and score > 0
                and any(FLOAT_PATTERN.fullmatch(token) is None for token in tokens)
            ):
                header_candidates.append((idx, tokens, score))
            continue
        break

    if not header_candidates:
        return None

    header_idx, header_tokens, _ = max(
        header_candidates,
        key=lambda candidate: (candidate[2], candidate[0]),
    )
    data_lines = lines[header_idx + 1 :]
    if not data_lines:
        return None

    text = "\n".join(data_lines).strip()
    if not text:
        return None

    try:
        raw_data = pd.read_csv(
            StringIO(text),
            sep=r"[,\s;]+",
            engine="python",
            comment="#",
            header=None,
        )
        df = _normalise_inferred_header_columns(
            raw_data,
            header_tokens=header_tokens,
            data_width=_physical_width_from_data_lines(data_lines),
        )
    except ValueError:
        raise
    except Exception:
        return None

    if df.empty or df.shape[1] < 2:
        return None
    return df


def norm_key(key: Any) -> str:
    if key is None:
        return ""
    s = str(key).strip().lower().replace(" ", "")
    s = s.replace("-", "").replace("_", "")
    return s


def extract_float(raw: Any) -> float | None:
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None

    if "," in s and "." not in s:
        grouped = COMMA_THOUSANDS_PATTERN.search(s)
        if grouped:
            s = grouped.group(0).replace(",", "")
        else:
            s = s.replace(",", ".")
    else:
        s = s.replace(",", "")

    m = FLOAT_PATTERN.search(s)
    if not m:
        return None
    try:
        return float(m.group(0))
    except Exception:
        return None


def _parse_semicolon_decimal_comma_token(value: str) -> float:
    """Parse one value when semicolon is the field delimiter.

    A comma inside a semicolon-delimited field can be a decimal mark or a
    thousands separator.  We accept only decimal-comma spellings that are
    unambiguous from the token itself; ambiguous three-digit groups fail
    closed instead of being silently split into extra columns.
    """

    token = value.strip().strip('"')
    if not token:
        raise ValueError("empty value in semicolon/decimal-comma profile")
    if token.lower() in {"nan", "+nan", "-nan"}:
        return float("nan")
    if token.lower() in {"inf", "+inf", "-inf", "infinity", "+infinity", "-infinity"}:
        raise ValueError(f"non-finite value {value!r}")
    if "," not in token:
        try:
            number = float(token)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"invalid numeric value {value!r}") from exc
    else:
        if "." in token or token.count(",") != 1:
            raise ValueError(
                f"ambiguous decimal-comma value {value!r}; use a single decimal comma"
            )
        match = re.fullmatch(r"[-+]?\d+,\d+", token)
        if match is None:
            raise ValueError(f"invalid decimal-comma value {value!r}")
        integer, fraction = token.rsplit(",", 1)
        # ``1,234`` is equally plausible as 1.234 or 1234.  A zero-leading
        # decimal (0,234) is also ambiguous with a grouped value in a generic
        # text file, so require a non-three-digit fractional width here.
        if (
            len(fraction) == 3
            and len(integer.lstrip("+-")) <= 3
            and int(integer) != 0
        ):
            raise ValueError(f"ambiguous decimal-comma value {value!r}")
        number = float(f"{integer}.{fraction}")
    if np.isinf(number):
        raise ValueError(f"non-finite value {value!r}")
    return number


def _read_semicolon_decimal_comma_dataframe(path: str | Path) -> pd.DataFrame | None:
    """Read an unambiguous semicolon/decimal-comma table, if present.

    The generic pandas delimiter inference treats both delimiters as field
    separators and can turn ``0,10;100,0`` into four columns.  This parser is
    selected only when the data rows clearly use semicolon as the outer
    delimiter, and validates every data value before returning.
    """

    lines = Path(path).read_text(encoding="utf-8-sig", errors="strict").splitlines()
    meaningful: list[tuple[int, str]] = []
    comment_header_tokens: list[str] | None = None
    for index, line in enumerate(lines):
        raw_stripped = line.strip()
        if raw_stripped.startswith("#"):
            candidate = raw_stripped.lstrip("#").strip()
            if ";" in candidate:
                candidate_tokens = [
                    field.strip()
                    for field in next(csv.reader([candidate], delimiter=";"))
                ]
                if (
                    len(candidate_tokens) >= 2
                    and _comment_header_score(candidate_tokens) > 0
                    and any(FLOAT_PATTERN.fullmatch(token) is None for token in candidate_tokens)
                ):
                    comment_header_tokens = candidate_tokens
            continue
        stripped = _strip_inline_comment(line).strip()
        if stripped:
            meaningful.append((index, stripped))
    if not meaningful:
        return None

    first_line = meaningful[0][1]
    if ";" not in first_line:
        return None
    first_tokens = [
        field.strip()
        for field in next(csv.reader([first_line], delimiter=";"))
    ]
    numeric_markers = {
        "nan", "+nan", "-nan", "inf", "+inf", "-inf",
        "infinity", "+infinity", "-infinity",
    }

    def is_numeric_token(token: str) -> bool:
        if token.strip().lower() in numeric_markers:
            return True
        try:
            _parse_semicolon_decimal_comma_token(token)
        except ValueError:
            return False
        return True

    first_is_numeric = len(first_tokens) >= 2 and all(
        is_numeric_token(token) for token in first_tokens
    )
    header_tokens = comment_header_tokens if first_is_numeric else first_tokens
    data_start = 0 if first_is_numeric else 1
    data_rows = meaningful[data_start:]
    if not data_rows:
        return None

    # A semicolon-only table belongs to the normal parser; this special route
    # is needed only when at least one data field contains a comma.
    if not any("," in text for _, text in data_rows):
        return None

    parsed_rows: list[list[float]] = []
    expected_width: int | None = None
    for _, text in data_rows:
        try:
            fields = next(csv.reader([text], delimiter=";"))
        except csv.Error as exc:
            raise ValueError("cannot parse semicolon/decimal-comma profile") from exc
        if expected_width is None:
            expected_width = len(fields)
        if len(fields) != expected_width or len(fields) < 2:
            raise ValueError("data rows have inconsistent semicolon field widths")
        parsed_rows.append([_parse_semicolon_decimal_comma_token(field) for field in fields])

    if header_tokens is not None and len(header_tokens) != expected_width:
        raise ValueError("header and data widths disagree in semicolon profile")
    frame = pd.DataFrame(
        parsed_rows,
        columns=header_tokens if header_tokens is not None else None,
    )
    # Full-file assertion: the special route must never hand a partially
    # parsed table to the heuristic column selector.
    if frame.empty or frame.shape[1] < 2 or np.isinf(frame.to_numpy(dtype=float)).any():
        raise ValueError("semicolon/decimal-comma profile contains invalid data")
    frame.attrs["saxsabs_semicolon_decimal_comma"] = True
    return frame


def normalize_transmission(trans: float | None, raw: Any = None, key: Any = None) -> float | None:
    if trans is None:
        return None
    try:
        t = float(trans)
    except Exception:
        return None
    if not np.isfinite(t):
        return None
    raw_s = str(raw).strip().lower() if raw is not None else ""
    key_s = norm_key(key) if key is not None else ""

    has_pct_hint = (
        "%" in raw_s
        or "percent" in raw_s
        or "pct" in raw_s
        or "percent" in key_s
        or "pct" in key_s
    )

    if has_pct_hint:
        t /= 100.0
    elif 2.0 <= t <= 100.0:
        t /= 100.0

    if not np.isfinite(t) or t <= 0 or t > 1.0:
        return None
    return t


def parse_header_values(header_mapping: dict[str, Any] | None) -> tuple[float | None, float | None, float | None]:
    meta: dict[str, str] = {}

    def add_meta(k: Any, v: Any) -> None:
        if k is None or v is None:
            return
        nk = norm_key(k)
        if nk:
            meta[nk] = str(v).strip()

    for k, v in (header_mapping or {}).items():
        add_meta(k, v)

    exp_keys = ["exposuretime", "counttime", "acqtime", "exposure", "time"]
    mon_keys = ["monitor", "beammonitor", "ionchamber", "mon", "i0", "flux"]
    trans_keys = ["sampletransmission", "transmission", "trans", "abs"]
    exp_exact_only = {"time"}
    mon_exact_only = {"mon", "i0"}
    trans_exact_only = {"abs"}

    def get_val(keys: list[str], exact_only: set[str] | None = None) -> tuple[str | None, str | None]:
        exact_only = set(exact_only or set())

        for k in keys:
            if k in meta:
                return meta[k], k

        for mk, mv in meta.items():
            for k in keys:
                if k in exact_only:
                    continue
                if mk.startswith(k) or mk.endswith(k):
                    return mv, mk

        for mk, mv in meta.items():
            for k in keys:
                if k in exact_only or len(k) < 6:
                    continue
                if k in mk:
                    return mv, mk

        return None, None

    exp_raw, exp_key = get_val(exp_keys, exp_exact_only)
    mon_raw, _ = get_val(mon_keys, mon_exact_only)
    trans_raw, trans_key = get_val(trans_keys, trans_exact_only)

    exp = extract_float(exp_raw)
    mon = extract_float(mon_raw)
    trans = extract_float(trans_raw)

    if exp is not None:
        exp_tag = f"{exp_key or ''} {exp_raw or ''}".lower()
        if "ms" in exp_tag:
            exp /= 1000.0
        elif "us" in exp_tag:
            exp /= 1_000_000.0

    trans = normalize_transmission(trans, raw=trans_raw, key=trans_key)
    return exp, mon, trans


def read_external_1d_profile(
    path: str | Path,
    *,
    allow_unidentified_intensity: bool = False,
) -> dict[str, Any]:
    p = Path(path)
    ext = p.suffix.lower()

    # Route to specialized readers based on file extension
    if ext == ".xml":
        try:
            return read_cansas1d_xml(p)
        except (ET.ParseError, OSError, UnicodeError, ValueError) as exc:
            raise ValueError(f"Cannot parse canSAS XML file: {p.name}") from exc
    elif ext in (".h5", ".hdf5", ".hdf", ".nxs"):
        return read_nxcansas_h5(p)

    dfs: list[pd.DataFrame] = []
    errs: list[str] = []

    # Detect this grammar before any generic pandas trial: splitting both
    # comma and semicolon would otherwise produce a plausible but wrong Q/I
    # pair and the later heuristic cannot recover the lost decimal marks.
    semicolon_decimal_df = _read_semicolon_decimal_comma_dataframe(p)
    if semicolon_decimal_df is not None:
        dfs.append(semicolon_decimal_df)
        has_comment_header = False
        plain_header_tokens = None
        physical_data_width = semicolon_decimal_df.shape[1]
    else:
        comment_header_df = _read_comment_header_dataframe(p)
        has_comment_header = comment_header_df is not None
        plain_header_tokens = _read_plain_header_tokens(p)
        physical_data_width = _physical_data_width(p)
        if comment_header_df is not None:
            dfs.append(comment_header_df)

    read_trials: list[dict[str, Any]] = [
        {"sep": None, "engine": "python", "comment": "#"},
        {"sep": r"[,\s;]+", "engine": "python", "comment": "#"},
        {"sep": r"[,\s;]+", "engine": "python", "comment": "#", "header": None},
    ]
    malformed_header_detected = False

    for kw in ([] if semicolon_decimal_df is not None else read_trials):
        try:
            df = pd.read_csv(path, encoding="utf-8-sig", **kw)
            if kw.get("header") is None and df is not None and not df.empty:
                position_columns = all(
                    isinstance(column, (int, np.integer)) for column in df.columns
                )
                if position_columns:
                    if has_comment_header or plain_header_tokens is not None:
                        continue
            if df is not None and "header" not in kw:
                header_for_malformed_check = (
                    plain_header_tokens
                    or [str(column) for column in df.columns]
                )
                if _has_malformed_unit_header_tokens(header_for_malformed_check):
                    malformed_header_detected = True
                    continue
                df = _normalise_inferred_header_columns(
                    df,
                    header_tokens=plain_header_tokens,
                    data_width=physical_data_width,
                )
            if df is not None and not df.empty and df.shape[1] >= 2:
                dfs.append(df)
        except ValueError as exc:
            if str(exc).startswith("header has more logical columns"):
                malformed_header_detected = True
            errs.append(str(exc))
        except Exception as exc:
            errs.append(str(exc))

    if malformed_header_detected:
        raise ValueError(f"Malformed Q-unit delimiter in {p.name}")
    if not dfs:
        raise ValueError(f"Cannot parse file: {Path(path).name} ({'; '.join(errs[:2])})")

    best: dict[str, Any] | None = None
    best_rank: tuple[int, int] = (-1, -1)

    for df in dfs:
        numeric_cols: dict[Any, pd.Series] = {}
        for col in df.columns:
            s = pd.to_numeric(df[col], errors="coerce")
            arr = s.to_numpy(dtype=np.float64, na_value=np.nan)
            cnt = int(np.isfinite(arr).sum())
            if cnt >= 3:
                numeric_cols[col] = s

        if len(numeric_cols) < 2:
            continue

        cols = list(numeric_cols.keys())

        x_col, x_named = _pick_named_column(
            cols,
            set(),
            exact={"q", "chi", "radial", "2theta", "twotheta", "s", "x"},
            prefixes=("q", "chi", "radial", "twotheta"),
            suffixes=("q",),
        )
        if x_col is None:
            x_col = cols[0]

        i_col, i_named = _pick_named_column(
            cols,
            {x_col},
            exact={
                "i",
                "intensity",
                "irel",
                "iref",
                "imeas",
                "iabs",
                "signal",
                "count",
                "counts",
                "y",
            },
            prefixes=("intensity", "signal", "count", "irel", "iabs", "i"),
            suffixes=("intensity",),
        )
        if i_col is None:
            position_columns = all(
                isinstance(column, (int, np.integer)) for column in df.columns
            )
            if not position_columns and not allow_unidentified_intensity:
                continue
            i_col = next((c for c in cols if c != x_col), None)
        if i_col is None:
            continue

        # Search every source column for an explicit uncertainty label, not
        # only columns with three finite values.  An all-NaN combined-standard
        # column is meaningful: it says the uncertainty budget is unknown and
        # must not be silently replaced by a finite statistical-only column.
        err_col, err_named = _pick_named_column(
            sorted(df.columns, key=_error_column_preference),
            {x_col, i_col},
            exact={"err", "error", "errors", "sigma", "std", "stdev", "unc", "uncertainty", "idev"},
            prefixes=("err", "error", "sigma", "std", "unc", "idev"),
            suffixes=("error", "sigma", "uncertainty"),
        )

        x = pd.to_numeric(df[x_col], errors="coerce").to_numpy(dtype=np.float64, na_value=np.nan)
        intensity = pd.to_numeric(df[i_col], errors="coerce").to_numpy(dtype=np.float64, na_value=np.nan)
        if df.attrs.get("saxsabs_semicolon_decimal_comma") and (
            not np.all(np.isfinite(x)) or not np.all(np.isfinite(intensity))
        ):
            raise ValueError("semicolon/decimal-comma Q and I must be finite in every row")
        mask = np.isfinite(x) & np.isfinite(intensity)
        if int(mask.sum()) < 3:
            continue

        x = x[mask]
        intensity = intensity[mask]

        if err_named and err_col is not None:
            err = pd.to_numeric(df[err_col], errors="coerce").to_numpy(dtype=np.float64, na_value=np.nan)[mask]
            err = np.where(np.isfinite(err), err, np.nan)
        else:
            err = np.full_like(intensity, np.nan, dtype=np.float64)

        order = np.argsort(x)
        x = x[order]
        intensity = intensity[order]
        err = err[order]

        pts = int(x.size)
        semantic_score = int(x_named) * 2 + int(i_named) * 3 + int(err_named)
        rank = (pts, semantic_score)
        if rank > best_rank:
            best_rank = rank
            best = {
                "x": x,
                "intensity": intensity,
                "uncertainty": err,
                "x_col": str(x_col),
                "x_unit": infer_q_unit_from_column(x_col),
                "x_unit_raw": (
                    q_column_unit_hint(x_col)
                    if infer_q_unit_from_column(x_col) is None
                    else ""
                ),
                "i_col": str(i_col),
                "err_col": str(err_col) if err_named and err_col is not None else "",
            }

    if best is None:
        raise ValueError(f"Cannot identify valid numeric columns in {Path(path).name}")
    if _q_header_has_unsupported_unit_syntax(best["x_col"]):
        raise ValueError(f"Unsupported or malformed Q-unit header in {Path(path).name}")
    best["operator_provenance"] = _read_text_operator_provenance(p)
    intensity = np.asarray(best.pop("intensity"), dtype=np.float64)
    uncertainty = np.asarray(best.pop("uncertainty"), dtype=np.float64)
    return _attach_intensity_arrays(best, intensity, uncertainty)


# ---------------------------------------------------------------------------
# canSAS 1D XML reader  (urn:cansas1d:1.1)
# ---------------------------------------------------------------------------
_CANSAS_NS = "urn:cansas1d:1.1"


def _intensity_unit_semantics(value: object) -> str | None:
    """Return a stable semantic token for an explicit intensity unit."""

    text = str(value or "").strip()
    if not text:
        return None
    if is_cm_inv_intensity_unit(text):
        return "cm^-1"
    token = _unit_token(text)
    return f"unit:{token}" if token else None


def _validate_intensity_unit_records(
    records: list[str],
    *,
    label: str,
) -> tuple[str | None, str]:
    """Validate per-point unit declarations and return semantic/raw units."""

    present = [bool(str(value).strip()) for value in records]
    if any(present) and not all(present):
        raise ValueError(f"canSAS XML contains mixed/missing {label} units")
    semantics = {_intensity_unit_semantics(value) for value in records if str(value).strip()}
    if len(semantics) > 1:
        raise ValueError(f"canSAS XML contains inconsistent {label} units")
    semantic = next(iter(semantics), None)
    raw = next((str(value).strip() for value in records if str(value).strip()), "")
    return semantic, raw


def _validate_i_dev_units(
    i_semantics: str | None,
    i_dev_records: list[str],
    *,
    has_i_dev: bool,
) -> None:
    if not has_i_dev:
        return
    present = [bool(str(value).strip()) for value in i_dev_records]
    if any(present) and not all(present):
        raise ValueError("canSAS XML contains mixed/missing Idev units")
    if not any(present):
        if i_semantics is not None:
            raise ValueError("canSAS XML Idev units are missing while I has units")
        return
    if any(present):
        if i_semantics is None:
            raise ValueError("canSAS XML Idev units conflict with missing I units")
        dev_semantics = {
            _intensity_unit_semantics(value)
            for value in i_dev_records
            if str(value).strip()
        }
        if dev_semantics != {i_semantics}:
            raise ValueError("canSAS XML Idev units do not match I units")


def read_cansas1d_xml(path: str | Path) -> dict[str, Any]:
    """Read a canSAS 1D XML file and return a profile dict.

    Returns the same profile dict as :func:`read_external_1d_profile`, with
    ``intensity`` always present and ``i_abs`` or ``i_rel`` only when the
    assessed state matches.
    """
    p = Path(path)
    tree = ET.parse(str(p))
    root = tree.getroot()

    # Handle both namespaced and non-namespaced XML.
    ns = ""
    if root.tag.startswith("{"):
        ns = root.tag.split("}")[0] + "}"

    # Find SASdata → Idata elements
    q_vals: list[float] = []
    i_vals: list[float] = []
    e_vals: list[float] = []
    i_unit_records: list[str] = []
    i_dev_unit_records: list[str] = []
    has_i_dev = False
    q_unit_records: list[tuple[str, str | None]] = []

    idata_elements = list(root.iter(f"{ns}Idata"))
    if not idata_elements:
        raise ValueError(f"canSAS XML contains no Idata points: {p.name}")
    for idata in idata_elements:
        q_el = idata.find(f"{ns}Q")
        i_el = idata.find(f"{ns}I")
        if q_el is None or i_el is None:
            raise ValueError(f"canSAS XML Idata point is missing Q or I: {p.name}")
        try:
            q_value = float((q_el.text or "").strip())
            i_value = float((i_el.text or "").strip())
        except (TypeError, ValueError) as exc:
            raise ValueError(f"canSAS XML contains non-numeric Q or I: {p.name}") from exc
        q_vals.append(q_value)
        i_vals.append(i_value)
        raw_q_unit = str(q_el.attrib.get("unit", "") or "").strip()
        q_unit_records.append((raw_q_unit, canonicalize_q_unit(raw_q_unit)))
        i_unit_records.append(str(i_el.attrib.get("unit", "") or "").strip())
        e_el = idata.find(f"{ns}Idev")
        if e_el is not None:
            has_i_dev = True
            i_dev_unit_records.append(str(e_el.attrib.get("unit", "") or "").strip())
            try:
                e_value = (
                    np.nan
                    if not (e_el.text or "").strip()
                    else float((e_el.text or "").strip())
                )
            except (TypeError, ValueError) as exc:
                raise ValueError(f"canSAS XML contains non-numeric Idev: {p.name}") from exc
            e_vals.append(e_value)
        else:
            e_vals.append(np.nan)

    if len(q_vals) < 2:
        raise ValueError(f"canSAS XML contains too few data points: {p.name}")
    x = np.asarray(q_vals, dtype=np.float64)
    intensity = np.asarray(i_vals, dtype=np.float64)
    if x.ndim != 1 or intensity.ndim != 1 or x.shape != intensity.shape:
        raise ValueError(f"canSAS XML Q and I must be matching 1-D arrays: {p.name}")
    if not np.all(np.isfinite(x)) or not np.all(np.isfinite(intensity)):
        raise ValueError(f"canSAS XML Q and I must contain only finite values: {p.name}")
    err = np.asarray(e_vals, dtype=np.float64)
    if err.shape != x.shape:
        raise ValueError(f"canSAS XML Idev shape does not match Q/I: {p.name}")
    if np.any(np.isinf(err)) or np.any(np.isfinite(err) & (err < 0)):
        raise ValueError(
            f"canSAS XML Idev must be NaN or finite and non-negative: {p.name}"
        )

    intensity_semantics, intensity_unit = _validate_intensity_unit_records(
        i_unit_records,
        label="I",
    )
    _validate_i_dev_units(
        intensity_semantics,
        i_dev_unit_records,
        has_i_dev=has_i_dev,
    )

    canonical_by_point = [canonical for _, canonical in q_unit_records]
    if any(not raw for raw, _ in q_unit_records):
        raise ValueError(f"canSAS XML Q unit is required: {p.name}")
    if any(canonical is None for _, canonical in q_unit_records):
        raise ValueError(f"canSAS XML contains unsupported Q unit: {p.name}")
    known_q_units = {unit for unit in canonical_by_point if unit is not None}
    raw_q_unit_tokens = {_unit_token(raw) for raw, _ in q_unit_records}
    # Canonically equivalent spellings (1/A and 1/angstrom) are consistent;
    # a mixture of canonical, unknown, or conflicting units is not safe.
    if len(set(canonical_by_point)) > 1 or (
        len(known_q_units) == 1 and any(unit is None for unit in canonical_by_point)
    ):
        raise ValueError(f"canSAS XML contains inconsistent Q units: {p.name}")
    if not known_q_units and len(raw_q_unit_tokens) > 1:
        raise ValueError(f"canSAS XML contains inconsistent Q units: {p.name}")
    q_unit = next(iter(known_q_units), None)
    q_unit_raw = next(
        (raw for raw, canonical in q_unit_records if raw and canonical is None),
        "",
    )

    operator_provenance: dict[str, str] = {}
    for process in root.iter(f"{ns}SASprocess"):
        for term in process.iter(f"{ns}term"):
            key = _operator_provenance_key(term.attrib.get("name", ""))
            if key is not None and term.text is not None:
                operator_provenance[key] = term.text.strip()
    order = np.argsort(x)
    return _attach_intensity_arrays(
        {
            "x": x[order],
            "x_col": "Q",
            "x_unit": q_unit,
            "x_unit_raw": q_unit_raw,
            "i_col": "I",
            "err_col": "Idev" if has_i_dev else "",
            "intensity_unit": intensity_unit,
            "operator_provenance": operator_provenance,
        },
        intensity[order],
        err[order],
    )


# ---------------------------------------------------------------------------
# NXcanSAS HDF5 reader
# ---------------------------------------------------------------------------

def read_nxcansas_h5(path: str | Path) -> dict[str, Any]:
    """Read an NXcanSAS HDF5 file and return a profile dict.

    Requires the ``h5py`` package.  Returns the same profile dict as
    :func:`read_external_1d_profile`.
    """
    try:
        import h5py
    except ImportError as exc:
        raise ImportError(
            "h5py is required for reading NXcanSAS files. "
            "Install it with:  pip install saxsabs[hdf5]"
        ) from exc

    p = Path(path)
    operator_provenance: dict[str, str] = {}
    with h5py.File(str(p), "r") as f:
        # Walk groups to find the first SASdata containing Q and I datasets.
        q_ds = None
        i_ds = None
        e_ds = None
        intensity_unit = ""
        i_dev_unit = ""
        q_unit: str | None = None
        q_unit_raw = ""
        q_unit_declared = False

        def _find_sasdata(group: Any) -> bool:
            nonlocal q_ds, i_ds, e_ds, intensity_unit, i_dev_unit
            nonlocal q_unit, q_unit_raw, q_unit_declared
            cls = group.attrs.get("canSAS_class", "")
            if isinstance(cls, bytes):
                cls = cls.decode()
            if cls == "SASdata" or group.name.rsplit("/", 1)[-1].startswith("sasdata"):
                if "Q" in group and "I" in group:
                    q_ds = group["Q"][()]
                    i_ds = group["I"][()]
                    raw_q_unit = group["Q"].attrs.get(
                        "units", group["Q"].attrs.get("unit", "")
                    )
                    if isinstance(raw_q_unit, bytes):
                        raw_q_unit = raw_q_unit.decode("utf-8", errors="replace")
                    q_unit_declared = bool(str(raw_q_unit or "").strip())
                    q_unit = canonicalize_q_unit(raw_q_unit)
                    q_unit_raw = str(raw_q_unit or "") if q_unit is None else ""
                    raw_unit = group["I"].attrs.get("units", "")
                    if isinstance(raw_unit, bytes):
                        raw_unit = raw_unit.decode("utf-8", errors="replace")
                    intensity_unit = str(raw_unit or "").strip()
                    if "Idev" in group:
                        e_ds = group["Idev"][()]
                        raw_i_dev_unit = group["Idev"].attrs.get("units", "")
                        if isinstance(raw_i_dev_unit, bytes):
                            raw_i_dev_unit = raw_i_dev_unit.decode(
                                "utf-8", errors="replace"
                            )
                        i_dev_unit = str(raw_i_dev_unit or "").strip()
                    return True
            for key in group:
                item = group[key]
                if hasattr(item, "keys"):  # is a group
                    if _find_sasdata(item):
                        return True
            return False

        _find_sasdata(f)

        def _collect_operator_provenance(_name: str, item: Any) -> None:
            if not isinstance(item, h5py.Group):
                return
            cls = item.attrs.get("canSAS_class", "")
            if isinstance(cls, bytes):
                cls = cls.decode("utf-8", errors="replace")
            group_name = item.name.rsplit("/", 1)[-1].lower()
            if cls != "SASprocess" and not group_name.startswith("sasprocess"):
                return
            for dataset_name, dataset in item.items():
                key = _operator_provenance_key(dataset_name)
                if key is None or not isinstance(dataset, h5py.Dataset):
                    continue
                raw = dataset[()]
                if isinstance(raw, np.ndarray) and raw.shape == ():
                    raw = raw.item()
                if isinstance(raw, bytes):
                    value = raw.decode("utf-8", errors="strict")
                else:
                    value = str(raw)
                operator_provenance[key] = value.strip()

        f.visititems(_collect_operator_provenance)
    if not q_unit_declared:
        raise ValueError(f"NXcanSAS Q unit is required: {p.name}")
    if q_unit_raw:
        raise ValueError(f"NXcanSAS contains unsupported Q unit: {p.name}")
    if q_ds is None or i_ds is None:
        raise ValueError(f"Cannot find SASdata/Q,I datasets in {p.name}")

    x = np.asarray(q_ds, dtype=np.float64)
    intensity = np.asarray(i_ds, dtype=np.float64)
    if x.ndim != 1 or intensity.ndim != 1:
        raise ValueError(f"NXcanSAS Q and I must be 1-D arrays in {p.name}")
    if x.shape != intensity.shape:
        raise ValueError(
            f"NXcanSAS dataset length mismatch in {p.name}: "
            f"Q has {x.size} points, I has {intensity.size}"
        )
    if x.size < 2:
        raise ValueError(f"NXcanSAS contains too few data points: {p.name}")
    if not np.all(np.isfinite(x)) or not np.all(np.isfinite(intensity)):
        raise ValueError(f"NXcanSAS Q and I must contain only finite values: {p.name}")
    err = (
        np.asarray(e_ds, dtype=np.float64)
        if e_ds is not None
        else np.full_like(x, np.nan)
    )

    if err.shape != x.shape:
        raise ValueError(
            f"NXcanSAS dataset length mismatch in {p.name}: "
            f"Q has {x.size} points, Idev has {err.size}"
        )
    if np.any(np.isinf(err)) or np.any(np.isfinite(err) & (err < 0)):
        raise ValueError(
            f"NXcanSAS Idev must be NaN or finite and non-negative in {p.name}"
        )
    intensity_semantics = _intensity_unit_semantics(intensity_unit)
    if e_ds is not None:
        if i_dev_unit:
            if (
                intensity_semantics is None
                or _intensity_unit_semantics(i_dev_unit) != intensity_semantics
            ):
                raise ValueError(f"NXcanSAS Idev units do not match I units in {p.name}")
        elif intensity_semantics is not None:
            raise ValueError(f"NXcanSAS Idev unit is missing while I has units in {p.name}")

    order = np.argsort(x)
    return _attach_intensity_arrays(
        {
            "x": x[order],
            "x_col": "Q",
            "x_unit": q_unit,
            "x_unit_raw": q_unit_raw,
            "i_col": "I",
            "err_col": "Idev" if e_ds is not None else "",
            "intensity_unit": intensity_unit,
            "operator_provenance": operator_provenance,
        },
        intensity[order],
        err[order],
    )


# ---------------------------------------------------------------------------
# Acquisition timestamp extraction (for 机时 / session grouping)
# ---------------------------------------------------------------------------

_ACQ_TIME_KEYS = [
    # common synchrotron / area detector header keys (case-insensitive after norm)
    "starttime",
    "acquisitiontime",
    "acqtime",
    "exposurestart",
    "startdate",
    "collectiontime",
    "headertime",
    "datetime",
    "date",
    "time",
    "unixepoch",
    "epoc",
    "mtime",  # last resort in some detectors
]

def _try_parse_datetime(value: Any) -> float | None:
    """Best-effort conversion of many date/time header formats to unix timestamp."""

    def parse_numeric_epoch(number: float) -> float | None:
        if not np.isfinite(number):
            return None
        # Choose the unit whose conversion lands in a plausible Unix epoch
        # range.  Testing the converted value, rather than only the raw
        # magnitude, distinguishes seconds, milliseconds, microseconds and
        # nanoseconds for both native numerics and numeric strings.
        for scale in (1.0, 1.0e3, 1.0e6, 1.0e9):
            seconds = number / scale
            if 1.0e9 <= seconds <= 5.0e9:
                return seconds
        return None

    if value is None:
        return None
    if isinstance(value, (int, float, np.number)):
        return parse_numeric_epoch(float(value))

    s = str(value).strip()
    if not s or s.lower() in ("none", "null", "nan"):
        return None

    # Try common numeric unix cases first
    try:
        parsed = parse_numeric_epoch(float(s))
        if parsed is not None:
            return parsed
    except (TypeError, ValueError):
        pass

    # Try python's datetime + dateutil if present
    try:
        from datetime import datetime

        # ISO8601 / common beamline formats
        for fmt in (
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%Y/%m/%d %H:%M:%S",
            "%d/%m/%Y %H:%M:%S",
            "%Y-%m-%d",
        ):
            try:
                dt = datetime.strptime(s.split(".")[0], fmt)
                return dt.timestamp()
            except Exception:
                continue
    except Exception:
        pass

    # dateutil is the most robust fallback (optional dependency)
    try:
        from dateutil import parser as du_parser  # type: ignore

        dt = du_parser.parse(s, fuzzy=True)
        return dt.timestamp()
    except Exception:
        pass

    return None


def extract_acquisition_timestamp(
    header: dict[str, Any] | None,
    *,
    fallback_mtime: float | None = None,
) -> float | None:
    """Extract acquisition / start time from a heterogeneous instrument header.

    Returns a unix timestamp (seconds since epoch) when successful, otherwise None.
    This is intentionally best-effort and used primarily for same-机时 grouping.
    """
    if not header:
        return fallback_mtime

    # Build normalized lookup
    norm: dict[str, Any] = {}
    for k, v in header.items():
        nk = str(k).strip().lower().replace("_", "").replace(" ", "").replace("/", "")
        norm[nk] = v

    for key in _ACQ_TIME_KEYS:
        if key in norm:
            ts = _try_parse_datetime(norm[key])
            if ts is not None:
                return ts

        # also try contains match for longer keys
        for nk, nv in norm.items():
            if key in nk and len(nk) <= len(key) + 8:
                ts = _try_parse_datetime(nv)
                if ts is not None:
                    return ts

    return fallback_mtime


def parse_header_values_with_meta(
    header_mapping: dict[str, Any] | None,
) -> tuple[float | None, float | None, float | None, float | None]:
    """Like parse_header_values but also returns best-effort acquisition timestamp.

    Returns (exp, mon, trans, acq_ts_unix).
    The timestamp is best-effort and may be None.
    """
    exp, mon, trans = parse_header_values(header_mapping)
    ts = extract_acquisition_timestamp(header_mapping)
    return exp, mon, trans, ts
