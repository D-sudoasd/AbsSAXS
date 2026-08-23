from pathlib import Path

import numpy as np
import pytest

from saxsabs.io.parsers import (
    canonicalize_q_unit,
    extract_float,
    infer_q_unit_from_column,
    normalize_transmission,
    parse_header_values,
    read_external_1d_profile,
)


@pytest.mark.parametrize(
    "raw_unit",
    [
        "nm",
        "angstrom",
        "A",
        "nm1",
        "a1",
        "angstrom1",
        "Q (nm)",
        "Q (angstrom)",
        "Q [nm^-1)",
    ],
)
def test_q_unit_canonicalization_rejects_bare_or_signless_lengths(raw_unit):
    assert canonicalize_q_unit(raw_unit) is None


@pytest.mark.parametrize(
    ("raw_unit", "expected"),
    [
        ("1/A", "A^-1"),
        ("1/angstrom", "A^-1"),
        ("A^-1", "A^-1"),
        ("Å⁻¹", "A^-1"),
        ("nm^-1", "nm^-1"),
        ("1/nm", "nm^-1"),
        ("inverse angstrom", "A^-1"),
        ("inv nm", "nm^-1"),
        ("invangstrom", "A^-1"),
        ("invnm", "nm^-1"),
    ],
)
def test_q_unit_canonicalization_requires_and_accepts_reciprocal_marker(raw_unit, expected):
    assert canonicalize_q_unit(raw_unit) == expected


def test_infer_q_unit_from_column_leaves_bare_q_length_unknown():
    assert infer_q_unit_from_column("Q (nm)") is None
    assert infer_q_unit_from_column("Q (angstrom)") is None


def test_extract_float_accepts_thousands_and_decimal_commas():
    assert np.isclose(extract_float("1,200,000"), 1200000.0)
    assert np.isclose(extract_float("0,85"), 0.85)


def test_parse_header_values_ms_and_percent():
    exp, mon, trans = parse_header_values(
        {
            "ExposureTime": "200 ms",
            "I0": "1.2e6",
            "Transmission": "85%",
        }
    )
    assert np.isclose(exp, 0.2)
    assert np.isclose(mon, 1.2e6)
    assert np.isclose(trans, 0.85)


def test_parse_header_values_us_and_plain_percent_number():
    exp, mon, trans = parse_header_values(
        {
            "acq_time": "500 us",
            "monitor": "10000",
            "sample_transmission": "72",
        }
    )
    assert np.isclose(exp, 0.0005)
    assert np.isclose(mon, 10000.0)
    assert np.isclose(trans, 0.72)


def test_normalize_transmission_treats_plain_two_as_percent_value():
    assert np.isclose(normalize_transmission(2.0, raw="2", key="Transmission"), 0.02)
    assert np.isclose(normalize_transmission(0.85, raw="0.85", key="Transmission"), 0.85)


def test_normalize_transmission_rejects_unhinted_near_one_ratio():
    assert normalize_transmission(1.2, raw="1.2", key="Transmission") is None


def test_parse_header_values_invalid_transmission_returns_none():
    exp, mon, trans = parse_header_values(
        {
            "ExposureTime": "1 s",
            "I0": "1000",
            "Transmission": "105%",
        }
    )
    assert np.isclose(exp, 1.0)
    assert np.isclose(mon, 1000.0)
    assert trans is None


def test_read_external_1d_profile_csv(tmp_path: Path):
    f = tmp_path / "profile.csv"
    f.write_text(
        "q,intensity,error\n"
        "0.10,100,5\n"
        "0.20,90,4\n"
        "0.30,80,4\n",
        encoding="utf-8",
    )

    out = read_external_1d_profile(f)
    assert out["x"].size == 3
    assert out["x_col"].lower() == "q"
    assert out["i_col"].lower() == "intensity"
    assert np.isclose(out["intensity"][0], 100.0)
    assert "i_rel" not in out


def test_read_external_1d_profile_space_delimited(tmp_path: Path):
    f = tmp_path / "profile.dat"
    f.write_text(
        "# q i sigma\n"
        "0.10 10 1\n"
        "0.20 20 2\n"
        "0.30 30 3\n",
        encoding="utf-8",
    )

    out = read_external_1d_profile(f)
    assert out["x"].size == 3
    assert np.isfinite(out["uncertainty"]).all()
    assert out["err_col"].lower() == "sigma"


def test_read_external_1d_profile_uses_real_comment_header_after_description(tmp_path: Path):
    f = tmp_path / "profile_with_description.dat"
    f.write_text(
        "# Integrated SAXS profile\n"
        "# q I sigma\n"
        "0.10 10 1\n"
        "0.20 20 2\n"
        "0.30 30 3\n",
        encoding="utf-8",
    )

    out = read_external_1d_profile(f)
    assert out["x_col"] == "q"
    assert out["i_col"] == "I"
    assert out["err_col"] == "sigma"


def test_read_external_1d_profile_prefers_q_over_index_column(tmp_path: Path):
    f = tmp_path / "profile_with_index.csv"
    f.write_text(
        "index,q,intensity,error\n"
        "0,0.10,100,5\n"
        "1,0.20,90,4\n"
        "2,0.30,80,4\n",
        encoding="utf-8",
    )

    out = read_external_1d_profile(f)
    assert out["x_col"].lower() == "q"
    assert out["i_col"].lower() == "intensity"
    np.testing.assert_allclose(out["x"], [0.10, 0.20, 0.30])


def test_read_external_1d_profile_prefers_intensity_over_id_column(tmp_path: Path):
    f = tmp_path / "profile_with_id.csv"
    f.write_text(
        "q,id,intensity,error\n"
        "0.10,101,100,5\n"
        "0.20,102,90,4\n"
        "0.30,103,80,4\n",
        encoding="utf-8",
    )

    out = read_external_1d_profile(f)
    assert out["x_col"].lower() == "q"
    assert out["i_col"].lower() == "intensity"
    np.testing.assert_allclose(out["intensity"], [100.0, 90.0, 80.0])
    assert "i_rel" not in out


def test_read_external_1d_profile_unnamed_third_column_not_treated_as_error(tmp_path: Path):
    f = tmp_path / "profile_three_cols.dat"
    f.write_text(
        "0.10 10 100\n"
        "0.20 20 200\n"
        "0.30 30 300\n",
        encoding="utf-8",
    )

    out = read_external_1d_profile(f)
    assert out["x"].size == 3
    assert out["err_col"] == ""
    assert np.all(np.isnan(out["uncertainty"]))


def test_read_external_1d_profile_prefers_combined_over_earlier_statistical_column(
    tmp_path: Path,
):
    f = tmp_path / "profile_uncertainties.csv"
    f.write_text(
        "q,intensity,Error_Statistical_cm^-1,Error_CombinedStandard_cm^-1\n"
        "0.10,100,1.0,1.5\n"
        "0.20,90,2.0,2.5\n"
        "0.30,80,3.0,3.5\n",
        encoding="utf-8",
    )

    out = read_external_1d_profile(f)

    assert out["err_col"] == "Error_CombinedStandard_cm^-1"
    np.testing.assert_allclose(out["uncertainty"], [1.5, 2.5, 3.5])


def test_read_external_1d_profile_recognizes_unicode_q_intensity_and_sigma_units(
    tmp_path: Path,
):
    f = tmp_path / "unicode_units.csv"
    f.write_text(
        "Q (Å⁻¹),I (cm⁻¹),σ (cm⁻¹)\n"
        "0.10,100,5\n"
        "0.20,90,4\n"
        "0.30,80,4\n",
        encoding="utf-8",
    )

    out = read_external_1d_profile(f)

    assert out["x_unit"] == "A^-1"
    assert out["i_col"] == "I (cm⁻¹)"
    assert out["err_col"] == "σ (cm⁻¹)"
    np.testing.assert_allclose(out["x"], [0.10, 0.20, 0.30])
    np.testing.assert_allclose(out["uncertainty"], [5.0, 4.0, 4.0])


def test_read_external_1d_profile_recognizes_unicode_nm_q_unit(tmp_path: Path):
    f = tmp_path / "unicode_nm.csv"
    f.write_text(
        "Q (nm⁻¹),I\n"
        "0.10,100\n"
        "0.20,90\n"
        "0.30,80\n",
        encoding="utf-8",
    )

    out = read_external_1d_profile(f)

    assert out["x_unit"] == "nm^-1"
    np.testing.assert_allclose(out["x"], [0.10, 0.20, 0.30])


def test_read_external_1d_profile_recognizes_angstrom_sign_variant(tmp_path: Path):
    f = tmp_path / "angstrom_sign.csv"
    f.write_text(
        "Q (Å⁻¹),I\n"
        "0.10,100\n"
        "0.20,90\n"
        "0.30,80\n",
        encoding="utf-8",
    )

    out = read_external_1d_profile(f)

    assert out["x_unit"] == "A^-1"


@pytest.mark.parametrize("q_header", ["Q (nm)", "Q (angstrom)"])
def test_read_external_1d_profile_keeps_bare_q_length_unknown(
    tmp_path: Path, q_header: str
):
    f = tmp_path / "bare_length.csv"
    f.write_text(
        f"{q_header},I\n"
        "0.10,100\n"
        "0.20,90\n"
        "0.30,80\n",
        encoding="utf-8",
    )

    out = read_external_1d_profile(f)

    assert out["x_unit"] is None
    assert out["x_unit_raw"] in {"nm", "angstrom"}


def test_read_external_1d_profile_rejoins_parenthesized_comment_header_units(
    tmp_path: Path,
):
    f = tmp_path / "comment_units.dat"
    f.write_text(
        "# Q (nm^-1) I (cm^-1) sigma (cm^-1)\n"
        "0.10 100 5\n"
        "0.20 90 4\n"
        "0.30 80 4\n",
        encoding="utf-8",
    )

    out = read_external_1d_profile(f)

    assert out["x_col"] == "Q (nm^-1)"
    assert out["x_unit"] == "nm^-1"
    assert out["i_col"] == "I (cm^-1)"
    assert out["err_col"] == "sigma (cm^-1)"
    np.testing.assert_allclose(out["intensity"], [100.0, 90.0, 80.0])
    np.testing.assert_allclose(out["uncertainty"], [5.0, 4.0, 4.0])


@pytest.mark.parametrize(
    ("header", "expected_unit"),
    [("Q (nm^-1) I", "nm^-1"), ("Q (Å⁻¹) I", "A^-1")],
)
def test_read_external_1d_profile_rejoins_plain_parenthesized_header_units(
    tmp_path: Path, header: str, expected_unit: str
):
    f = tmp_path / "plain_header_units.dat"
    f.write_text(
        f"{header}\n"
        "0.10 100 5\n"
        "0.20 90 4\n"
        "0.30 80 4\n",
        encoding="utf-8",
    )

    out = read_external_1d_profile(f)

    assert out["x_col"] == header.rsplit(" I", 1)[0]
    assert out["x_unit"] == expected_unit
    assert out["i_col"] == "I"
    assert out["err_col"] == ""
    np.testing.assert_allclose(out["intensity"], [100.0, 90.0, 80.0])
    assert np.all(np.isnan(out["uncertainty"]))


@pytest.mark.parametrize(
    ("header", "expected_unit"),
    [
        ("# Q [nm^-1] I", "nm^-1"),
        ("Q [nm^-1] I", "nm^-1"),
        ("# Q {Å⁻¹} I", "A^-1"),
        ("Q {Å⁻¹} I", "A^-1"),
    ],
)
def test_read_external_1d_profile_rejoins_square_and_braced_unit_headers(
    tmp_path: Path, header: str, expected_unit: str
):
    f = tmp_path / "delimited_header_units.dat"
    f.write_text(
        f"{header}\n"
        "0.10 100 5\n"
        "0.20 90 4\n"
        "0.30 80 4\n",
        encoding="utf-8",
    )

    out = read_external_1d_profile(f)
    header_without_comment = header.removeprefix("# ")

    assert out["x_col"] == header_without_comment.rsplit(" I", 1)[0]
    assert out["x_unit"] == expected_unit
    assert out["i_col"] == "I"
    assert out["err_col"] == ""
    np.testing.assert_allclose(out["intensity"], [100.0, 90.0, 80.0])


@pytest.mark.parametrize("header", ["# Q [nm^-1) I", "Q {Å⁻¹] I"])
def test_read_external_1d_profile_rejects_mismatched_unit_delimiters(
    tmp_path: Path, header: str
):
    f = tmp_path / "malformed_delimiter_header.dat"
    f.write_text(
        f"{header}\n"
        "0.10 100 5\n"
        "0.20 90 4\n"
        "0.30 80 4\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Q-unit delimiter"):
        read_external_1d_profile(f)
