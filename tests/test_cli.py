import json
import sys
from pathlib import Path

import numpy as np
import pytest

from saxsabs.cli import _normalize_q_profile, main
from saxsabs.workflows import bl19b2_abs2d


def test_cli_norm_factor(capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        sys,
        "argv",
        ["saxsabs", "norm-factor", "--mode", "integrated", "--mon", "10", "--trans", "0.5"],
    )
    main()
    out = capsys.readouterr().out.strip()
    assert out == "5.0"


def test_cli_norm_factor_rejects_non_finite_result(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(
        sys,
        "argv",
        ["saxsabs", "norm-factor", "--mode", "integrated", "--mon", "10", "--trans", "0"],
    )

    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 1
    err = capsys.readouterr().err
    assert "non-finite" in err
    assert "trans must be 0 < T <= 1" in err


def test_cli_parse_header(tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch):
    f = tmp_path / "header.json"
    f.write_text('{"ExposureTime":"1000 ms","I0":"100","Transmission":"80%"}', encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["saxsabs", "parse-header", "--header-json", str(f)])
    main()
    out = json.loads(capsys.readouterr().out)
    assert out["exp_s"] == 1.0
    assert out["i0"] == 100.0
    assert out["trans"] == 0.8


def test_cli_estimate_k(tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch):
    meas = tmp_path / "meas.csv"
    ref = tmp_path / "ref.csv"
    meas.write_text("q,i\n0.01,17.1\n0.02,15.4\n0.05,13.4\n0.10,11.8\n", encoding="utf-8")
    ref.write_text("q,i\n0.01,34.2\n0.02,30.8\n0.05,26.8\n0.10,23.6\n", encoding="utf-8")

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "saxsabs",
            "estimate-k",
            "--meas",
            str(meas),
            "--ref",
            str(ref),
            "--intensity-state",
            "relative",
            "--qmin",
            "0.01",
            "--qmax",
            "0.2",
        ],
    )
    main()
    out = json.loads(capsys.readouterr().out)
    assert out["k_factor"] == pytest.approx(2.0, rel=1e-6)
    assert out["k_std_semantics"] == "inlier ratio scatter; not combined K uncertainty"
    assert out["k_statistical_standard_uncertainty"] == pytest.approx(0.0, abs=1e-12)
    assert out["k_standard_uncertainty"] is None
    assert out["k_expanded_uncertainty"] is None
    assert out["coverage_factor"] is None


def test_cli_estimate_k_accepts_common_intensity_column_names(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
):
    meas = tmp_path / "meas.csv"
    ref = tmp_path / "ref.csv"
    meas.write_text(
        "q,intensity,error\n0.01,17.1,0.1\n0.02,15.4,0.1\n0.05,13.4,0.1\n0.10,11.8,0.1\n",
        encoding="utf-8",
    )
    ref.write_text(
        "q,intensity,error\n0.01,34.2,0.1\n0.02,30.8,0.1\n0.05,26.8,0.1\n0.10,23.6,0.1\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "saxsabs",
            "estimate-k",
            "--meas",
            str(meas),
            "--ref",
            str(ref),
            "--intensity-state",
            "relative",
        ],
    )
    main()
    out = json.loads(capsys.readouterr().out)
    assert out["k_factor"] == pytest.approx(2.0, rel=1e-6)


def test_cli_estimate_k_accepts_scattering_column_names_with_units(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
):
    meas = tmp_path / "meas.csv"
    ref = tmp_path / "ref.csv"
    meas.write_text(
        "Q_A^-1,I_rel\n0.01,17.1\n0.02,15.4\n0.05,13.4\n0.10,11.8\n",
        encoding="utf-8",
    )
    ref.write_text(
        "Q_A^-1,I_rel\n0.01,34.2\n0.02,30.8\n0.05,26.8\n0.10,23.6\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "saxsabs",
            "estimate-k",
            "--meas",
            str(meas),
            "--ref",
            str(ref),
            "--intensity-state",
            "relative",
        ],
    )
    main()
    out = json.loads(capsys.readouterr().out)
    assert out["k_factor"] == pytest.approx(2.0, rel=1e-6)


def test_cli_estimate_k_converts_nm_inverse_q_to_angstrom_inverse(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
):
    meas = tmp_path / "meas_nm.csv"
    ref = tmp_path / "ref_nm.csv"
    meas.write_text(
        "Q (nm⁻¹),I_rel\n0.10,17.1\n0.20,15.4\n0.50,13.4\n1.00,11.8\n",
        encoding="utf-8",
    )
    ref.write_text(
        "Q (nm⁻¹),I_rel\n0.10,34.2\n0.20,30.8\n0.50,26.8\n1.00,23.6\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "saxsabs",
            "estimate-k",
            "--meas",
            str(meas),
            "--ref",
            str(ref),
            "--intensity-state",
            "relative",
            "--qmin",
            "0.01",
            "--qmax",
            "0.11",
        ],
    )

    main()

    out = json.loads(capsys.readouterr().out)
    assert out["k_factor"] == pytest.approx(2.0, rel=1e-6)
    assert out["points_total"] == 4


def test_cli_estimate_k_reuses_normalized_whitespace_header_columns(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
):
    meas = tmp_path / "meas_plain_nm.dat"
    ref = tmp_path / "ref_plain_nm.dat"
    meas.write_text(
        "Q (nm^-1) I\n0.10 17.1 0.1\n0.20 15.4 0.1\n0.50 13.4 0.1\n1.00 11.8 0.1\n",
        encoding="utf-8",
    )
    ref.write_text(
        "Q (nm^-1) I\n0.10 34.2 0.1\n0.20 30.8 0.1\n0.50 26.8 0.1\n1.00 23.6 0.1\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "saxsabs",
            "estimate-k",
            "--meas",
            str(meas),
            "--ref",
            str(ref),
            "--q-col",
            "Q (nm^-1)",
            "--i-col",
            "I",
            "--ref-q-col",
            "Q (nm^-1)",
            "--ref-i-col",
            "I",
            "--intensity-state",
            "relative",
            "--qmin",
            "0.01",
            "--qmax",
            "0.11",
        ],
    )

    main()

    full_header_out = json.loads(capsys.readouterr().out)

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "saxsabs",
            "estimate-k",
            "--meas",
            str(meas),
            "--ref",
            str(ref),
            "--q-col",
            "Q",
            "--i-col",
            "I",
            "--ref-q-col",
            "Q",
            "--ref-i-col",
            "I",
            "--intensity-state",
            "relative",
            "--qmin",
            "0.01",
            "--qmax",
            "0.11",
        ],
    )
    main()

    prefix_out = json.loads(capsys.readouterr().out)
    assert full_header_out["k_factor"] == pytest.approx(2.0, rel=1e-6)
    assert prefix_out["k_factor"] == pytest.approx(full_header_out["k_factor"], rel=1e-12)
    assert prefix_out["points_total"] == full_header_out["points_total"] == 4


def test_cli_parse_external1d_reports_q_unit(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
):
    profile = tmp_path / "profile_nm.csv"
    profile.write_text(
        "Q (nm⁻¹),I\n0.1,10\n0.2,9\n0.3,8\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(sys, "argv", ["saxsabs", "parse-external1d", "--input", str(profile)])

    main()

    out = json.loads(capsys.readouterr().out)
    assert out["x_unit"] == "nm^-1"


def test_cli_estimate_k_rejects_chi_axis(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
):
    meas = tmp_path / "meas_chi.csv"
    ref = tmp_path / "ref.csv"
    meas.write_text("chi_deg,I_rel\n1,17.1\n2,15.4\n3,13.4\n", encoding="utf-8")
    ref.write_text("q,I_rel\n0.01,34.2\n0.02,30.8\n0.03,26.8\n", encoding="utf-8")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "saxsabs",
            "estimate-k",
            "--meas",
            str(meas),
            "--ref",
            str(ref),
            "--intensity-state",
            "relative",
        ],
    )

    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 1
    assert "chi" in capsys.readouterr().err.lower()


def test_cli_q_normalization_is_shallow_and_idempotent():
    profile = {
        "x": [1.0, 2.0],
        "x_col": "Q",
        "x_unit": "nm^-1",
        "operator_provenance": {},
    }

    converted = _normalize_q_profile(profile, profile_label="sample")
    repeated = _normalize_q_profile(converted, profile_label="sample")

    assert profile["x"] == [1.0, 2.0]
    np.testing.assert_allclose(converted["x"], [0.1, 0.2])
    np.testing.assert_allclose(repeated["x"], converted["x"])
    assert converted["x_unit"] == repeated["x_unit"] == "A^-1"


def test_cli_q_normalization_rejects_unknown_unit_with_explicit_override():
    profile = {
        "x": [1.0, 2.0],
        "x_col": "Q (mm^-1)",
        "x_unit": None,
        "x_unit_raw": "mm^-1",
        "x_axis_override": True,
    }

    with pytest.raises(ValueError, match="unsupported Q unit"):
        _normalize_q_profile(profile, profile_label="sample")


@pytest.mark.parametrize("header", ["Q (nm)", "Q (angstrom)", "Q (A)", "Q (Å)"])
def test_cli_q_normalization_rejects_bare_length_unit_headers(header):
    profile = {
        "x": [1.0, 2.0],
        "x_col": header,
        "x_unit": "nm^-1" if "nm" in header else "A^-1",
        "x_unit_raw": "",
    }

    with pytest.raises(ValueError, match="reciprocal length"):
        _normalize_q_profile(profile, profile_label="sample")


@pytest.mark.parametrize("header", ["Q (nm^-1)", "Q (Å⁻¹)", "Q (1/nm)"])
def test_cli_q_normalization_accepts_explicit_reciprocal_unit_headers(header):
    profile = {"x": [1.0, 2.0], "x_col": header, "x_unit": None, "x_unit_raw": ""}

    converted = _normalize_q_profile(profile, profile_label="sample")

    assert converted["x_unit"] == "A^-1"


def test_cli_estimate_k_accepts_explicit_column_overrides(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
):
    meas = tmp_path / "meas.csv"
    ref = tmp_path / "ref.csv"
    meas.write_text(
        "angle,I_meas\n0.01,17.1\n0.02,15.4\n0.05,13.4\n0.10,11.8\n",
        encoding="utf-8",
    )
    ref.write_text(
        "q_ref,I_ref\n0.01,34.2\n0.02,30.8\n0.05,26.8\n0.10,23.6\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "saxsabs",
            "estimate-k",
            "--meas",
            str(meas),
            "--ref",
            str(ref),
            "--q-col",
            "angle",
            "--i-col",
            "I_meas",
            "--ref-q-col",
            "q_ref",
            "--ref-i-col",
            "I_ref",
            "--intensity-state",
            "relative",
        ],
    )
    main()
    out = json.loads(capsys.readouterr().out)
    assert out["k_factor"] == pytest.approx(2.0, rel=1e-6)


def test_cli_estimate_k_invalid_override_lists_available_columns(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
):
    meas = tmp_path / "meas.csv"
    ref = tmp_path / "ref.csv"
    meas.write_text(
        "q,intensity\n0.01,17.1\n0.02,15.4\n0.05,13.4\n0.10,11.8\n",
        encoding="utf-8",
    )
    ref.write_text("q,i\n0.01,34.2\n0.02,30.8\n0.05,26.8\n0.10,23.6\n", encoding="utf-8")

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "saxsabs",
            "estimate-k",
            "--meas",
            str(meas),
            "--ref",
            str(ref),
            "--q-col",
            "missing_q",
            "--i-col",
            "intensity",
            "--intensity-state",
            "relative",
        ],
    )

    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 1
    err = capsys.readouterr().err
    assert "missing_q" in err
    assert "Available columns: q, intensity" in err


def test_cli_parse_external1d(tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch):
    profile = tmp_path / "profile.csv"
    profile.write_text("q,i,err\n0.01,10,0.2\n0.02,9,0.2\n0.03,8,0.2\n", encoding="utf-8")

    monkeypatch.setattr(sys, "argv", ["saxsabs", "parse-external1d", "--input", str(profile)])
    main()
    out = json.loads(capsys.readouterr().out)
    assert out["points"] == 3
    assert out["x_col"] == "q"
    assert out["i_col"] == "i"
    assert out["err_col"] == "err"
    assert out["intensity_state"] == "ambiguous"


def test_cli_estimate_k_refuses_i_abs_column_name(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
):
    meas = tmp_path / "meas.csv"
    ref = tmp_path / "ref.csv"
    meas.write_text(
        "Q_A^-1,I_abs\n0.01,17.1\n0.02,15.4\n0.05,13.4\n0.10,11.8\n",
        encoding="utf-8",
    )
    ref.write_text(
        "Q_A^-1,I_abs\n0.01,34.2\n0.02,30.8\n0.05,26.8\n0.10,23.6\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        sys,
        "argv",
        ["saxsabs", "estimate-k", "--meas", str(meas), "--ref", str(ref)],
    )

    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 1
    assert "already absolute" in capsys.readouterr().err.lower()


def test_cli_estimate_k_refuses_unlabeled_intensity(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
):
    meas = tmp_path / "meas.csv"
    ref = tmp_path / "ref.csv"
    meas.write_text("q,i\n0.01,17.1\n0.02,15.4\n0.05,13.4\n0.10,11.8\n", encoding="utf-8")
    ref.write_text("q,i\n0.01,34.2\n0.02,30.8\n0.05,26.8\n0.10,23.6\n", encoding="utf-8")
    monkeypatch.setattr(
        sys,
        "argv",
        ["saxsabs", "estimate-k", "--meas", str(meas), "--ref", str(ref)],
    )

    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 1
    assert "ambiguous" in capsys.readouterr().err.lower()


def test_cli_estimate_k_thickness_cm_converts_to_per_cm(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
):
    meas = tmp_path / "meas.csv"
    ref = tmp_path / "ref.csv"
    meas.write_text(
        "q,i\n0.01,1.71\n0.02,1.54\n0.05,1.34\n0.10,1.18\n",
        encoding="utf-8",
    )
    ref.write_text("q,i\n0.01,34.2\n0.02,30.8\n0.05,26.8\n0.10,23.6\n", encoding="utf-8")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "saxsabs",
            "estimate-k",
            "--meas",
            str(meas),
            "--ref",
            str(ref),
            "--intensity-state",
            "relative",
            "--thickness-cm",
            "0.1",
        ],
    )
    main()
    out = json.loads(capsys.readouterr().out)
    assert out["k_factor"] == pytest.approx(2.0, rel=1e-6)


def _write_absolute_profile(path: Path, intensities: str) -> None:
    path.write_text(
        "# intensity_state: absolute_cm^-1\n"
        "# intensity_unit: 1/cm\n"
        '# corrections_applied: ["k","thickness"]\n'
        "q,i\n"
        f"{intensities}",
        encoding="utf-8",
    )


def test_cli_subtract_buffer(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
):
    sample = tmp_path / "sample.csv"
    buffer = tmp_path / "buffer.csv"
    _write_absolute_profile(sample, "0.01,12.0\n0.02,11.0\n0.20,6.0\n")
    _write_absolute_profile(buffer, "0.01,2.0\n0.02,2.0\n0.20,2.0\n")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "saxsabs",
            "subtract-buffer",
            "--sample",
            str(sample),
            "--buffer",
            str(buffer),
            "--alpha",
            "1.0",
        ],
    )
    main()
    out = json.loads(capsys.readouterr().out)
    assert out["points"] == 3
    assert out["alpha"] == pytest.approx(1.0)


def test_cli_subtract_buffer_refuses_unlabeled_profiles(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
):
    sample = tmp_path / "sample.csv"
    buffer = tmp_path / "buffer.csv"
    sample.write_text("q,i\n0.01,12.0\n0.02,11.0\n0.20,6.0\n", encoding="utf-8")
    buffer.write_text("q,i\n0.01,2.0\n0.02,2.0\n0.20,2.0\n", encoding="utf-8")
    monkeypatch.setattr(
        sys,
        "argv",
        ["saxsabs", "subtract-buffer", "--sample", str(sample), "--buffer", str(buffer)],
    )

    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 1
    assert "absolute" in capsys.readouterr().err.lower()


def test_cli_subtract_fluorescence(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
):
    sample = tmp_path / "sample.csv"
    _write_absolute_profile(sample, "0.01,12.0\n0.02,11.0\n0.20,6.0\n")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "saxsabs",
            "subtract-fluorescence",
            "--sample",
            str(sample),
            "--method",
            "constant",
            "--f0",
            "2.0",
            "--f0-uncertainty",
            "0.0",
            "--beta-uncertainty",
            "0.0",
        ],
    )
    main()
    out = json.loads(capsys.readouterr().out)
    assert out["points"] == 3
    assert out["method"] == "constant"
    assert out["f0"] == pytest.approx(2.0)
    assert out["negative_fraction"] == pytest.approx(0.0)


def test_cli_subtract_fluorescence_refuses_unlabeled_profiles(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
):
    sample = tmp_path / "sample.csv"
    sample.write_text("q,i\n0.01,12.0\n0.02,11.0\n0.20,6.0\n", encoding="utf-8")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "saxsabs",
            "subtract-fluorescence",
            "--sample",
            str(sample),
            "--method",
            "constant",
            "--f0",
            "2.0",
        ],
    )

    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 1
    assert "absolute" in capsys.readouterr().err.lower()


def test_cli_version(capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch):
    from saxsabs import __version__

    monkeypatch.setattr(sys, "argv", ["saxsabs", "--version"])
    with pytest.raises(SystemExit) as exc_info:
        main()
    assert exc_info.value.code == 0
    assert f"saxsabs {__version__}" in capsys.readouterr().out


def test_cli_bl19b2_abs2d_passes_pydidas_yaml_and_mask_to_workflow(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
):
    captured = {}

    def fake_run(config: bl19b2_abs2d.BL19B2Abs2DConfig) -> dict[str, str]:
        captured["config"] = config
        return {"status": "dry-run", "output_root": str(config.resolved_output_root())}

    input_root = tmp_path / "dat001"
    cali = tmp_path / "reference_saxs" / "Cali.yaml"
    mask = tmp_path / "reference_saxs" / "Mask.edf"
    output_root = tmp_path / "dat001_absolute_corrected_2D"
    monkeypatch.setattr(bl19b2_abs2d, "run_bl19b2_abs2d", fake_run)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "saxsabs",
            "bl19b2-abs2d",
            "--input-root",
            str(input_root),
            "--pydidas-cali-yaml",
            str(cali),
            "--mask",
            str(mask),
            "--output-root",
            str(output_root),
            "--mu",
            "20.2",
            "--monitor-mode",
            "rate",
            "--dry-run",
            "--no-preview",
        ],
    )

    main()

    out = json.loads(capsys.readouterr().out)
    config = captured["config"]
    assert out["status"] == "dry-run"
    assert config.input_root == input_root
    assert config.pydidas_cali_yaml == cali
    assert config.mask_path == mask
    assert config.poni_path is None
    assert config.output_root == output_root
    assert config.dry_run
    assert not config.write_preview


def test_cli_bl19b2_abs2d_passes_explicit_reference_paths(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
):
    captured = {}

    def fake_run(config: bl19b2_abs2d.BL19B2Abs2DConfig) -> dict[str, str]:
        captured["config"] = config
        return {"status": "dry-run", "output_root": str(config.resolved_output_root())}

    input_root = tmp_path / "dat001"
    poni = tmp_path / "geometry.poni"
    dark = tmp_path / "refs" / "dark_run42.tif"
    background = tmp_path / "refs" / "empty_run42.tif"
    standard = tmp_path / "refs" / "gc_run42.tif"
    direct = tmp_path / "refs" / "direct_run42.tif"
    monkeypatch.setattr(bl19b2_abs2d, "run_bl19b2_abs2d", fake_run)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "saxsabs",
            "bl19b2-abs2d",
            "--input-root",
            str(input_root),
            "--poni",
            str(poni),
            "--dark",
            str(dark),
            "--background",
            str(background),
            "--standard",
            str(standard),
            "--direct-beam",
            str(direct),
            "--mu",
            "20.2",
            "--monitor-mode",
            "rate",
            "--dry-run",
        ],
    )

    main()

    out = json.loads(capsys.readouterr().out)
    config = captured["config"]
    assert out["status"] == "dry-run"
    assert config.dark_path == dark
    assert config.background_path == background
    assert config.standard_path == standard
    assert config.direct_path == direct


def test_cli_bl19b2_abs2d_passes_monitor_and_fixed_thickness_modes(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
):
    captured = {}

    def fake_run(config: bl19b2_abs2d.BL19B2Abs2DConfig) -> dict[str, str]:
        captured["config"] = config
        return {"status": "dry-run", "output_root": str(config.resolved_output_root())}

    monkeypatch.setattr(bl19b2_abs2d, "run_bl19b2_abs2d", fake_run)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "saxsabs",
            "bl19b2-abs2d",
            "--input-root",
            str(tmp_path / "dat001"),
            "--poni",
            str(tmp_path / "geometry.poni"),
            "--monitor-mode",
            "integrated",
            "--sample-thickness-cm",
            "0.0123",
            "--monitor-relative-standard-uncertainty",
            "0.01",
            "--sample-thickness-relative-standard-uncertainty",
            "0.02",
            "--alpha-standard-uncertainty",
            "0.03",
            "--standard-thickness-relative-standard-uncertainty",
            "0.04",
            "--dry-run",
        ],
    )

    main()

    assert json.loads(capsys.readouterr().out)["status"] == "dry-run"
    assert captured["config"].monitor_mode == "integrated"
    assert captured["config"].sample_thickness_cm == 0.0123
    assert captured["config"].mu_cm_inv is None
    assert captured["config"].monitor_relative_standard_uncertainty == 0.01
    assert captured["config"].sample_thickness_relative_standard_uncertainty == 0.02
    assert captured["config"].alpha_standard_uncertainty == 0.03
    assert captured["config"].standard_thickness_relative_standard_uncertainty == 0.04


def test_cli_bl19b2_abs2d_passes_manifest_and_thickness_derivation_paths(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
):
    captured = {}

    def fake_run(config: bl19b2_abs2d.BL19B2Abs2DConfig) -> dict[str, str]:
        captured['config'] = config
        return {'status': 'dry-run'}

    monkeypatch.setattr(bl19b2_abs2d, 'run_bl19b2_abs2d', fake_run)
    manifest = tmp_path / 'include.csv'
    derivation = tmp_path / 'thickness.json'
    monkeypatch.setattr(
        sys,
        'argv',
        [
            'saxsabs',
            'bl19b2-abs2d',
            '--input-root',
            str(tmp_path / 'dat001'),
            '--poni',
            str(tmp_path / 'geometry.poni'),
            '--monitor-mode',
            'rate',
            '--sample-thickness-cm',
            '0.1',
            '--include-manifest',
            str(manifest),
            '--thickness-derivation-json',
            str(derivation),
        ],
    )

    main()

    assert json.loads(capsys.readouterr().out)['status'] == 'dry-run'
    assert captured['config'].include_manifest_path == manifest
    assert captured['config'].thickness_derivation_path == derivation


def test_cli_bl19b2_abs2d_passes_standard_side_and_system_coverage_uncertainties(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
):
    captured = {}

    def fake_run(config: bl19b2_abs2d.BL19B2Abs2DConfig) -> dict[str, str]:
        captured["config"] = config
        return {"status": "dry-run", "output_root": str(config.resolved_output_root())}

    monkeypatch.setattr(bl19b2_abs2d, "run_bl19b2_abs2d", fake_run)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "saxsabs", "bl19b2-abs2d",
            "--input-root", str(tmp_path / "dat001"),
            "--poni", str(tmp_path / "geometry.poni"),
            "--monitor-mode", "rate",
            "--sample-thickness-cm", "0.1",
            "--standard-transmission-abs-uncertainty", "0.01",
            "--standard-monitor-relative-standard-uncertainty", "0.02",
            "--calibration-background-monitor-relative-standard-uncertainty", "0.03",
            "--system-coverage-factor", "2.0",
            "--dry-run",
        ],
    )

    main()

    assert json.loads(capsys.readouterr().out)["status"] == "dry-run"
    config = captured["config"]
    assert config.standard_transmission_abs_uncertainty == pytest.approx(0.01)
    assert config.standard_monitor_relative_standard_uncertainty == pytest.approx(0.02)
    assert config.calibration_background_monitor_relative_standard_uncertainty == pytest.approx(0.03)
    assert config.system_coverage_factor == pytest.approx(2.0)

def test_cli_bl19b2_abs2d_passes_explicit_calibration_controls(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
):
    captured = {}

    def fake_run(config: bl19b2_abs2d.BL19B2Abs2DConfig) -> dict[str, str]:
        captured["config"] = config
        return {"status": "dry-run", "output_root": str(config.resolved_output_root())}

    monkeypatch.setattr(bl19b2_abs2d, "run_bl19b2_abs2d", fake_run)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "saxsabs",
            "bl19b2-abs2d",
            "--input-root",
            str(tmp_path / "dat001"),
            "--poni",
            str(tmp_path / "geometry.poni"),
            "--monitor-mode",
            "rate",
            "--mu",
            "20.2",
            "--standard-key",
            "CUSTOM_STANDARD",
            "--no-correct-solid-angle-for-k",
            "--polarization-factor",
            "0.95",
            "--dry-run",
        ],
    )

    main()

    assert json.loads(capsys.readouterr().out)["status"] == "dry-run"
    config = captured["config"]
    assert config.standard_key == "CUSTOM_STANDARD"
    assert config.correct_solid_angle_for_k is False
    assert config.polarization_factor == pytest.approx(0.95)


def test_cli_bl19b2_v1_legacy_requires_explicit_historical_assumptions(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
):
    captured = {}

    def fake_run(config: bl19b2_abs2d.BL19B2Abs2DConfig) -> dict[str, str]:
        captured["config"] = config
        return {"status": "dry-run", "output_root": str(config.resolved_output_root())}

    monkeypatch.setattr(bl19b2_abs2d, "run_bl19b2_abs2d", fake_run)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "saxsabs",
            "bl19b2-abs2d-v1-legacy",
            "--input-root",
            str(tmp_path / "dat001"),
            "--poni",
            str(tmp_path / "geometry.poni"),
            "--legacy-assume-monitor-rate",
            "--legacy-assume-mu-20-2",
            "--dry-run",
        ],
    )

    main()

    assert json.loads(capsys.readouterr().out)["status"] == "dry-run"
    assert captured["config"].monitor_mode == "rate"
    assert captured["config"].mu_cm_inv == pytest.approx(20.2)


@pytest.mark.parametrize(
    "safety_option",
    ["--legacy-assume-monitor-rate", "--legacy-assume-mu-20-2"],
)
def test_cli_bl19b2_v1_legacy_rejects_incomplete_historical_assumptions(
    safety_option: str,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "saxsabs",
            "bl19b2-abs2d-v1-legacy",
            "--input-root",
            str(tmp_path / "dat001"),
            "--poni",
            str(tmp_path / "geometry.poni"),
            safety_option,
        ],
    )

    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 2
    assert "explicit" in capsys.readouterr().err.lower()

@pytest.mark.parametrize("status", ["partial", "failed"])
def test_cli_bl19b2_abs2d_returns_nonzero_for_incomplete_scientific_run(
    status: str,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(
        bl19b2_abs2d,
        "run_bl19b2_abs2d",
        lambda config: {"status": status, "output_root": str(config.resolved_output_root())},
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "saxsabs",
            "bl19b2-abs2d",
            "--input-root",
            str(tmp_path / "dat001"),
            "--poni",
            str(tmp_path / "geometry.poni"),
            "--mu",
            "20.2",
            "--monitor-mode",
            "rate",
        ],
    )

    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 1
    assert json.loads(capsys.readouterr().out)["status"] == status


def test_cli_bl19b2_abs2d_rejects_two_geometry_sources(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "saxsabs",
            "bl19b2-abs2d",
            "--input-root",
            str(tmp_path / "dat001"),
            "--poni",
            str(tmp_path / "geometry.poni"),
            "--pydidas-cali-yaml",
            str(tmp_path / "Cali.yaml"),
        ],
    )

    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 2
