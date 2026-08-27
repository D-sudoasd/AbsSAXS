"""Export SAXS profiles in standard community formats.

Supported output formats:

* **canSAS 1D XML** — ``urn:cansas1d:1.1`` (no external dependencies)
* **NXcanSAS HDF5** — NeXus ``NXcanSAS`` application definition (requires h5py)
"""

from __future__ import annotations

import os
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import numpy as np

from saxsabs.core.intensity_state import (
    IntensityState,
    assess_intensity_state,
    is_cm_inv_intensity_unit,
)


# ---------------------------------------------------------------------------
# canSAS 1D XML  (cansas1d:1.1)
# ---------------------------------------------------------------------------
_CANSAS_NS = "urn:cansas1d:1.1"
_CANSAS_XSI = "http://www.w3.org/2001/XMLSchema-instance"
_CANSAS_SCHEMA = (
    "urn:cansas1d:1.1 "
    "http://www.cansas.org/formats/canSAS1d/1.1/doc/cansas1d.xsd"
)


_OPERATOR_PROVENANCE_KEYS = (
    "calibration_context_fingerprint",
    "k_factor",
    "formula_version",
    "monitor_mode",
    "correct_solid_angle",
    "polarization_factor",
    "poni_sha256",
    "mask_sha256",
    "flat_sha256",
    "intensity_state",
    "corrections_applied",
    "do_not_repeat",
    "intensity_unit",
    "thickness_cm",
    "thickness_source",
    "buffer_source_name",
    "buffer_source_sha256",
    "buffer_alpha",
    "buffer_alpha_uncertainty",
    "fluorescence_method",
    "fluorescence_f0",
    "fluorescence_f0_uncertainty",
    "fluorescence_beta",
    "fluorescence_beta_uncertainty",
    "fluorescence_high_q_window",
    "fluorescence_source_name",
    "fluorescence_source_sha256",
    "uncertainty_model",
    "uncertainty_type",
)


def _operator_provenance_from_metadata(metadata: dict[str, Any]) -> dict[str, str]:
    """Normalize portable operator provenance carried by a 1-D writer."""
    nested = metadata.get("operator_provenance")
    nested_values = nested if isinstance(nested, dict) else {}
    provenance: dict[str, str] = {}
    for key in _OPERATOR_PROVENANCE_KEYS:
        source = nested_values if key in nested_values else metadata
        if key not in source:
            continue
        value = source[key]
        if value is None:
            provenance[key] = "null"
        elif isinstance(value, bool):
            provenance[key] = "true" if value else "false"
        else:
            provenance[key] = str(value).strip()
    return provenance


def _require_absolute_cm_inv_unit(metadata: dict[str, Any]) -> str:
    """Stamp 1/cm only when the caller declared absolute cm^-1 intensity."""

    assessment = assess_intensity_state(metadata)
    if assessment.state is not IntensityState.ABSOLUTE_CM_INV:
        raise ValueError(
            "absolute-intensity writers require intensity_state=absolute_cm^-1 "
            f"and a cm^-1 intensity_unit; assessed state is {assessment.state.value}"
        )
    nested = metadata.get("operator_provenance")
    nested = nested if isinstance(nested, dict) else {}
    unit = metadata.get("intensity_unit", nested.get("intensity_unit", ""))
    if not is_cm_inv_intensity_unit(unit):
        raise ValueError(
            "absolute-intensity writers refuse to stamp 1/cm without an explicit "
            "cm^-1 intensity_unit"
        )
    return "1/cm"


def _prepare_profile_arrays(
    q: np.ndarray,
    i_abs: np.ndarray,
    err: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray | None]:
    q_arr = np.asarray(q, dtype=np.float64)
    i_arr = np.asarray(i_abs, dtype=np.float64)
    if q_arr.ndim != 1 or i_arr.ndim != 1:
        raise ValueError("q and intensity must be 1-D arrays")
    if q_arr.shape != i_arr.shape:
        raise ValueError("q and intensity must have the same shape")
    if q_arr.size == 0:
        raise ValueError("q and intensity must not be empty")
    if not np.all(np.isfinite(q_arr)):
        raise ValueError("q must contain only finite values")
    if not np.all(np.isfinite(i_arr)):
        raise ValueError("intensity must contain only finite values")

    e_arr = None
    if err is not None:
        e_arr = np.asarray(err, dtype=np.float64)
        if e_arr.ndim != 1:
            raise ValueError("uncertainty must be a 1-D array")
        if e_arr.shape != q_arr.shape:
            raise ValueError("q and uncertainty must have the same shape")
        if np.any(np.isinf(e_arr)):
            raise ValueError("uncertainty must not contain infinite values")
        if np.any(np.isfinite(e_arr) & (e_arr < 0)):
            raise ValueError("uncertainty must be non-negative or NaN")

    return q_arr, i_arr, e_arr


def write_cansas1d_xml(
    path: str | Path,
    q: np.ndarray,
    i_abs: np.ndarray,
    err: np.ndarray | None = None,
    metadata: dict[str, Any] | None = None,
) -> Path:
    """Write a 1-D SAXS profile in canSAS 1D XML format.

    Parameters
    ----------
    path : str or Path
        Output file path (should end in ``.xml``).
    q : ndarray
        Momentum-transfer values (Å⁻¹).
    i_abs : ndarray
        Absolute intensity (cm⁻¹).
    err : ndarray or None
        Uncertainty (cm⁻¹).
    metadata : dict or None
        Optional keys: ``title``, ``run``, ``wavelength_A``, ``sdd_m``,
        ``sample_name``, ``instrument_name``, ``detector_name``,
        ``process_name``, ``process_note``, and ``note``.

    Returns
    -------
    Path
        The written file path.
    """
    meta = metadata or {}
    intensity_unit = _require_absolute_cm_inv_unit(meta)
    out = Path(path)

    root = ET.Element("SASroot")
    root.set("version", "1.1")
    root.set("xmlns", _CANSAS_NS)
    root.set("xmlns:xsi", _CANSAS_XSI)
    root.set("xsi:schemaLocation", _CANSAS_SCHEMA)

    entry = ET.SubElement(root, "SASentry", name="entry01")
    ET.SubElement(entry, "Title").text = meta.get("title", "SAXS profile")
    ET.SubElement(entry, "Run").text = meta.get("run", "001")

    # --- SASdata ---
    sasdata = ET.SubElement(entry, "SASdata")
    q_arr, i_arr, e_arr = _prepare_profile_arrays(q, i_abs, err)

    for idx in range(q_arr.size):
        idata = ET.SubElement(sasdata, "Idata")
        qel = ET.SubElement(idata, "Q", unit="1/A")
        qel.text = f"{q_arr[idx]:.8g}"
        iel = ET.SubElement(idata, "I", unit=intensity_unit)
        iel.text = f"{i_arr[idx]:.8g}"
        if e_arr is not None and np.isfinite(e_arr[idx]):
            eel = ET.SubElement(idata, "Idev", unit=intensity_unit)
            eel.text = f"{e_arr[idx]:.8g}"

    # --- SASsample ---
    sassample = ET.SubElement(entry, "SASsample")
    ET.SubElement(sassample, "ID").text = meta.get("sample_name", "unknown")

    # --- SASinstrument ---
    sasinst = ET.SubElement(entry, "SASinstrument")
    ET.SubElement(sasinst, "name").text = meta.get("instrument_name", "")
    source = ET.SubElement(sasinst, "SASsource")
    ET.SubElement(source, "radiation").text = "x-ray"
    if "wavelength_A" in meta:
        wl = ET.SubElement(source, "wavelength", unit="A")
        wl.text = f"{meta['wavelength_A']:.6g}"
    ET.SubElement(sasinst, "SAScollimation")
    det = ET.SubElement(sasinst, "SASdetector")
    ET.SubElement(det, "name").text = meta.get("detector_name", "")
    if "sdd_m" in meta:
        sdd = ET.SubElement(det, "SDD", unit="m")
        sdd.text = f"{meta['sdd_m']:.4g}"

    # --- SASprocess ---
    sasproc = ET.SubElement(entry, "SASprocess")
    ET.SubElement(sasproc, "name").text = meta.get(
        "process_name", "SAXSAbs absolute calibration"
    )
    for key, value in _operator_provenance_from_metadata(meta).items():
        ET.SubElement(sasproc, "term", name=key).text = value
    ET.SubElement(sasproc, "SASprocessnote").text = str(
        meta.get("process_note") or "Profile exported by saxsabs."
    )
    ET.SubElement(entry, "SASnote").text = str(
        meta.get("note") or "Generated by saxsabs."
    )

    # Write
    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")
    out.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(
        prefix=f".{out.name}.", suffix=".tmp", dir=str(out.parent)
    )
    os.close(fd)
    temporary = Path(temporary_name)
    committed = False
    try:
        tree.write(str(temporary), xml_declaration=True, encoding="utf-8")
        os.replace(str(temporary), str(out))
        committed = True
    finally:
        if not committed:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass
    return out


# ---------------------------------------------------------------------------
# NXcanSAS HDF5
# ---------------------------------------------------------------------------
def write_nxcansas_h5(
    path: str | Path,
    q: np.ndarray,
    i_abs: np.ndarray,
    err: np.ndarray | None = None,
    metadata: dict[str, Any] | None = None,
) -> Path:
    """Write a 1-D SAXS profile in NXcanSAS (NeXus HDF5) format.

    Requires the ``h5py`` package (``pip install saxsabs[hdf5]``).

    Parameters
    ----------
    path, q, i_abs, err, metadata
        Same as :func:`write_cansas1d_xml`.

    Returns
    -------
    Path
        The written file path.
    """
    try:
        import h5py
    except ImportError as exc:
        raise ImportError(
            "h5py is required for NXcanSAS output. "
            "Install it with:  pip install saxsabs[hdf5]"
        ) from exc

    meta = metadata or {}
    intensity_unit = _require_absolute_cm_inv_unit(meta)
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    q_arr, i_arr, e_arr = _prepare_profile_arrays(q, i_abs, err)

    # h5py creates/truncates its target before validating every metadata
    # assignment.  Build beside the destination and replace only after the
    # complete file has closed successfully, so a failed write cannot destroy
    # a previously valid result.
    fd, temporary_name = tempfile.mkstemp(
        prefix=f".{out.name}.", suffix=".tmp", dir=str(out.parent)
    )
    os.close(fd)
    temporary = Path(temporary_name)
    committed = False
    try:
        with h5py.File(str(temporary), "w") as f:
            entry = f.create_group("sasentry01")
            entry.attrs["NX_class"] = "NXentry"
            entry.attrs["canSAS_class"] = "SASentry"
            entry.attrs["version"] = "1.1"
            entry["definition"] = "NXcanSAS"
            entry["title"] = meta.get("title", "SAXS profile")
            entry["run"] = meta.get("run", "001")

            # SASdata
            data = entry.create_group("sasdata01")
            data.attrs["NX_class"] = "NXdata"
            data.attrs["canSAS_class"] = "SASdata"
            data.attrs["signal"] = "I"
            data.attrs["I_axes"] = "Q"
            data.attrs["Q_indices"] = 0

            ds_q = data.create_dataset("Q", data=q_arr)
            ds_q.attrs["units"] = "1/angstrom"

            ds_i = data.create_dataset("I", data=i_arr)
            ds_i.attrs["units"] = intensity_unit

            if e_arr is not None:
                ds_e = data.create_dataset("Idev", data=e_arr)
                ds_e.attrs["units"] = intensity_unit

            # SASinstrument (minimal)
            inst = entry.create_group("sasinstrument01")
            inst.attrs["NX_class"] = "NXinstrument"
            inst.attrs["canSAS_class"] = "SASinstrument"
            if meta.get("instrument_name"):
                inst["name"] = meta["instrument_name"]

            src = inst.create_group("source01")
            src.attrs["NX_class"] = "NXsource"
            src["radiation"] = "x-ray"
            if "wavelength_A" in meta:
                ds_wl = src.create_dataset(
                    "incident_wavelength", data=meta["wavelength_A"]
                )
                ds_wl.attrs["units"] = "angstrom"

            # SASprocess
            process = entry.create_group("sasprocess01")
            process.attrs["NX_class"] = "NXprocess"
            process.attrs["canSAS_class"] = "SASprocess"
            process["name"] = meta.get("process_name", "SAXSAbs absolute calibration")
            for key, value in _operator_provenance_from_metadata(meta).items():
                process[key] = value
            # SASsample
            sample = entry.create_group("sassample01")
            sample.attrs["NX_class"] = "NXsample"
            sample.attrs["canSAS_class"] = "SASsample"
            sample["name"] = meta.get("sample_name", "unknown")

        os.replace(str(temporary), str(out))
        committed = True
    finally:
        if not committed:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass

    return out
