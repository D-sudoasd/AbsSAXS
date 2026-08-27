from pathlib import Path

import numpy as np
import pytest

from saxsabs.io.parsers import (
    canonicalize_q_unit,
    extract_float,
    infer_q_unit_from_column,
    normalize_transmission,
    parse_header_values,
    q_axis_kind,
    read_external_1d_profile,
    _try_parse_datetime,
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
        ("A-1", "A^-1"),
        ("angstrom-1", "A^-1"),
        ("Å⁻¹", "A^-1"),
        ("nm^-1", "nm^-1"),
        ("nm-1", "nm^-1"),
        ("nm - 1", "nm^-1"),
        ("1/nm", "nm^-1"),
        ("1/m", "m^-1"),
        ("m^-1", "m^-1"),
        ("m - 1", "m^-1"),
        ("inverse m", "m^-1"),
        ("inverse angstrom", "A^-1"),
        ("inv nm", "nm^-1"),
        ("invangstrom", "A^-1"),
        ("invnm", "nm^-1"),
    ],
)
def test_q_unit_canonicalization_requires_and_accepts_reciprocal_marker(raw_unit, expected):
    assert canonicalize_q_unit(raw_unit) == expected


@pytest.mark.parametrize(
    "raw_unit",
    [
        "nm^-10",
        "nm^-12",
        "A^-10",
        "1/nm2",
        "nm-10",
        "q_nm^-10",
        "inverse nm2",
        "invnm2",
        "1/nm/s",
        "nm^-1foo",
        "Q_nonsense_nm^-1",
        "1/nm A^-1",
        "nm^-1 A^-1",
        "1/nm/angstrom",
        "Q (nm^-1) [A^-1]",
    ],
)
def test_q_unit_canonicalization_rejects_conflicting_or_partial_tokens(raw_unit):
    assert canonicalize_q_unit(raw_unit) is None


@pytest.mark.parametrize(
    ("raw_unit", "expected"),
    [
        ("Q_A^-1", "A^-1"),
        ("q_nm^-1", "nm^-1"),
        ("Q (nm^-1)", "nm^-1"),
        ("Q [nm^-1]", "nm^-1"),
        ("Q {Å⁻¹}", "A^-1"),
    ],
)
def test_q_unit_canonicalization_accepts_leading_q_and_bracket_forms(raw_unit, expected):
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


def test_read_external_1d_profile_supports_unambiguous_semicolon_decimal_comma(
    tmp_path: Path,
):
    profile = tmp_path / "decimal-comma.dat"
    profile.write_text(
        "Q;I\n"
        "0,10;100,0\n"
        "0,20;90,0\n"
        "0,30;80,0\n",
        encoding="utf-8",
    )

    result = read_external_1d_profile(profile)

    np.testing.assert_allclose(result["x"], [0.10, 0.20, 0.30])
    np.testing.assert_allclose(result["intensity"], [100.0, 90.0, 80.0])


def test_decimal_comma_zero_leading_three_digit_fraction_is_not_thousands_grouping(
    tmp_path: Path,
):
    profile = tmp_path / "decimal-comma-zero-leading.dat"
    profile.write_text(
        "Q;I\n"
        "0,100;-0,100\n"
        "0,200;0,200\n"
        "0,300;0,300\n",
        encoding="utf-8",
    )

    result = read_external_1d_profile(profile)

    np.testing.assert_allclose(result["x"], [0.1, 0.2, 0.3])
    np.testing.assert_allclose(result["intensity"], [-0.1, 0.2, 0.3])


def test_read_external_1d_profile_supports_comment_semicolon_decimal_comma_header(
    tmp_path: Path,
):
    profile = tmp_path / "comment-decimal-comma.dat"
    profile.write_text(
        "# Q;I\n"
        "0,10;100,0\n"
        "0,20;90,0\n"
        "0,30;80,0\n",
        encoding="utf-8",
    )

    result = read_external_1d_profile(profile)

    assert result["x_col"] == "Q"
    assert result["i_col"] == "I"


@pytest.mark.parametrize("column", ["I/cm", "I (1/cm)", "I (cm^-1)", "I_abs (cm^-1)"])
def test_explicit_absolute_intensity_headers_expose_i_abs(tmp_path: Path, column: str):
    profile = tmp_path / "absolute-header.csv"
    profile.write_text(
        f"Q,{column}\n0.1,100\n0.2,90\n0.3,80\n",
        encoding="utf-8",
    )

    result = read_external_1d_profile(profile)

    assert result["intensity_state"] == "absolute_cm^-1"
    np.testing.assert_allclose(result["i_abs"], [100.0, 90.0, 80.0])


@pytest.mark.parametrize("column", ["I_ref", "I_meas"])
def test_external_profile_accepts_exact_reference_or_measured_intensity_header(
    tmp_path: Path, column: str
):
    profile = tmp_path / "semantic-intensity-header.csv"
    profile.write_text(
        f"q_ref,{column}\n0.1,100\n0.2,90\n0.3,80\n",
        encoding="utf-8",
    )

    result = read_external_1d_profile(profile)

    assert result["i_col"] == column
    np.testing.assert_allclose(result["intensity"], [100.0, 90.0, 80.0])


@pytest.mark.parametrize(
    "column",
    ["imagecm1", "indexcm1", "I_absorbance", "iabsorption", "iabsent"],
)
def test_external_profile_rejects_unrelated_i_prefixed_header(tmp_path: Path, column: str):
    profile = tmp_path / "false-intensity-header.csv"
    profile.write_text(
        f"Q,{column}\n0.1,100\n0.2,90\n0.3,80\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="numeric columns"):
        read_external_1d_profile(profile)


def test_read_external_1d_profile_rejects_ambiguous_semicolon_comma_values(
    tmp_path: Path,
):
    profile = tmp_path / "ambiguous-comma.dat"
    profile.write_text(
        "Q;I\n"
        "1,234;5,678\n"
        "2,345;6,789\n"
        "3,456;7,890\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="ambiguous decimal-comma"):
        read_external_1d_profile(profile)


def test_read_external_1d_profile_keeps_nan_uncertainty_in_decimal_comma_table(
    tmp_path: Path,
):
    profile = tmp_path / "decimal-comma-error.dat"
    profile.write_text(
        "Q;I;Error\n"
        "0,10;100,0;1,0\n"
        "0,20;90,0;NaN\n"
        "0,30;80,0;1,0\n",
        encoding="utf-8",
    )

    result = read_external_1d_profile(profile)

    assert np.isnan(result["uncertainty"][1])


@pytest.mark.parametrize("name", ["quality", "query", "qwerty"])
def test_q_axis_kind_does_not_classify_q_prefixed_words_as_q(name):
    assert q_axis_kind(name) == "unknown"


@pytest.mark.parametrize("name", ["machine", "mychi", "not2theta"])
def test_q_axis_kind_requires_chi_and_two_theta_token_boundaries(name):
    assert q_axis_kind(name) == "unknown"


@pytest.mark.parametrize("name", ["q", "q_ref", "Q_A^-1", "Q(nm^-1)", "q1"])
def test_q_axis_kind_accepts_unambiguous_q_forms(name):
    assert q_axis_kind(name) == "q"


def test_q_axis_kind_accepts_compact_angstrom_inverse_header():
    assert q_axis_kind("qA^-1") == "q"
    assert infer_q_unit_from_column("qA^-1") == "A^-1"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (1_700_000_000, 1_700_000_000.0),
        (1_700_000_000_000, 1_700_000_000.0),
        (1_700_000_000_000_000, 1_700_000_000.0),
        ("1700000000000000000", 1_700_000_000.0),
    ],
)
def test_try_parse_datetime_distinguishes_epoch_units(value, expected):
    assert _try_parse_datetime(value) == pytest.approx(expected)


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


def test_read_external_1d_profile_ignores_index_before_unit_bearing_intensity(tmp_path: Path):
    f = tmp_path / "profile_with_index_and_unit_intensity.csv"
    f.write_text(
        "index,Q (nm^-1),I_abs (cm^-1)\n"
        "0,0.10,100\n"
        "1,0.20,90\n"
        "2,0.30,80\n",
        encoding="utf-8",
    )

    out = read_external_1d_profile(f)

    assert out["x_col"] == "Q (nm^-1)"
    assert out["i_col"] == "I_abs (cm^-1)"
    assert out["intensity_state"] == "absolute_cm^-1"
    np.testing.assert_allclose(out["x"], [0.10, 0.20, 0.30])
    np.testing.assert_allclose(out["intensity"], [100.0, 90.0, 80.0])


def test_read_external_1d_profile_ignores_id_before_standalone_unit_bearing_i(
    tmp_path: Path,
):
    f = tmp_path / "profile_with_id_and_unit_intensity.csv"
    f.write_text(
        "Q,id,I (cm^-1),sigma\n"
        "0.10,101,100,5\n"
        "0.20,102,90,4\n"
        "0.30,103,80,4\n",
        encoding="utf-8",
    )

    out = read_external_1d_profile(f)

    assert out["x_col"] == "Q"
    assert out["i_col"] == "I (cm^-1)"
    assert out["intensity_state"] == "absolute_cm^-1"
    np.testing.assert_allclose(out["intensity"], [100.0, 90.0, 80.0])
    np.testing.assert_allclose(out["uncertainty"], [5.0, 4.0, 4.0])


def test_read_external_1d_profile_accepts_underscore_unit_intensity_after_id(
    tmp_path: Path,
):
    f = tmp_path / "profile_with_id_and_underscore_unit_intensity.csv"
    f.write_text(
        "Q,id,I_cm^-1,sigma\n"
        "0.10,101,100,5\n"
        "0.20,102,90,4\n"
        "0.30,103,80,4\n",
        encoding="utf-8",
    )

    out = read_external_1d_profile(f)

    assert out["i_col"] == "I_cm^-1"
    assert out["intensity_state"] == "absolute_cm^-1"
    np.testing.assert_allclose(out["intensity"], [100.0, 90.0, 80.0])


def test_read_external_1d_profile_selects_slash_unit_intensity_over_id(
    tmp_path: Path,
):
    f = tmp_path / "profile_with_id_and_slash_unit_intensity.csv"
    f.write_text(
        "Q,id,I/cm,sigma\n"
        "0.10,101,100,5\n"
        "0.20,102,90,4\n"
        "0.30,103,80,4\n",
        encoding="utf-8",
    )

    out = read_external_1d_profile(f)

    assert out["i_col"] == "I/cm"
    np.testing.assert_allclose(out["intensity"], [100.0, 90.0, 80.0])


def test_read_external_1d_profile_rejects_text_header_without_supported_intensity(
    tmp_path: Path,
):
    f = tmp_path / "profile_without_supported_intensity.csv"
    f.write_text(
        "Q,id,foo\n"
        "0.01,101,10\n"
        "0.02,102,9\n"
        "0.03,103,8\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="numeric columns"):
        read_external_1d_profile(f)


@pytest.mark.parametrize(
    ("header", "expected_unit"),
    [
        ("Q 1/nm I", "nm^-1"),
        ("# Q 1/nm I", "nm^-1"),
        ("Q inverse nm I", "nm^-1"),
        ("Q nm -1 I", "nm^-1"),
    ],
)
def test_read_external_1d_profile_rejoins_space_separated_q_unit_header(
    tmp_path: Path,
    header: str,
    expected_unit: str,
):
    f = tmp_path / "space_q_unit.dat"
    f.write_text(
        f"{header}\n"
        "0.10 100 5\n"
        "0.20 90 4\n"
        "0.30 80 4\n",
        encoding="utf-8",
    )

    out = read_external_1d_profile(f)

    assert out["x_col"] in {
        "Q 1/nm",
        "Q inverse nm",
        "Q nm -1",
    }
    assert out["x_unit"] == expected_unit
    np.testing.assert_allclose(out["x"], [0.10, 0.20, 0.30])
    np.testing.assert_allclose(out["intensity"], [100.0, 90.0, 80.0])


@pytest.mark.parametrize("unit_phrase", ["nm - 1", "A - 1", "angstrom - 1"])
@pytest.mark.parametrize("comment_header", [False, True])
def test_read_external_1d_profile_rejoins_q_unit_and_keeps_slash_intensity(
    tmp_path: Path,
    unit_phrase: str,
    comment_header: bool,
):
    f = tmp_path / "space_q_unit_intensity.dat"
    prefix = "# " if comment_header else ""
    f.write_text(
        f"{prefix}Q {unit_phrase} I/cm sigma\n"
        "0.10 100 5\n"
        "0.20 90 4\n"
        "0.30 80 4\n",
        encoding="utf-8",
    )

    out = read_external_1d_profile(f)

    assert out["x_unit"] == ("nm^-1" if unit_phrase.startswith("nm") else "A^-1")
    assert out["i_col"] == "I/cm"
    assert out["err_col"] == "sigma"
    np.testing.assert_allclose(out["intensity"], [100.0, 90.0, 80.0])


@pytest.mark.parametrize(
    ("header", "separator", "comment_header"),
    [
        ('"Q 1/nm",I', ",", False),
        ('"Q 1/nm",I', ",", True),
        ('"Q 1/nm";"I/cm";sigma', ";", False),
        ('"Q 1/nm" "I/cm" sigma', " ", False),
    ],
)
def test_read_external_1d_profile_tokenizes_quoted_headers_without_losing_units(
    tmp_path: Path,
    header: str,
    separator: str,
    comment_header: bool,
):
    f = tmp_path / "quoted_header.dat"
    prefix = "# " if comment_header else ""
    values = (
        ["1.0", "100"]
        if header.endswith(",I")
        else ["1.0", "100", "5"]
    )
    if len(values) == 2:
        rows = [
            separator.join(["1.0", "100"]),
            separator.join(["2.0", "90"]),
            separator.join(["3.0", "80"]),
        ]
    else:
        rows = [
            separator.join(["1.0", "100", "5"]),
            separator.join(["2.0", "90", "4"]),
            separator.join(["3.0", "80", "4"]),
        ]
    f.write_text(f"{prefix}{header}\n" + "\n".join(rows) + "\n", encoding="utf-8")

    out = read_external_1d_profile(f)

    assert out["x_unit"] == "nm^-1"
    assert out["i_col"] in {"I", "I/cm"}
    np.testing.assert_allclose(out["x"], [1.0, 2.0, 3.0])


def test_read_external_1d_profile_tokenizes_quoted_parenthesized_columns(
    tmp_path: Path,
):
    f = tmp_path / "quoted_parenthesized_header.csv"
    f.write_text(
        '"Q (nm^-1)","I/cm",sigma\n'
        "1.0,100,5\n2.0,90,4\n3.0,80,4\n",
        encoding="utf-8",
    )
    out = read_external_1d_profile(f)
    assert out["x_unit"] == "nm^-1"
    assert out["i_col"] == "I/cm"
    assert out["err_col"] == "sigma"
    np.testing.assert_allclose(out["uncertainty"], [5.0, 4.0, 4.0])


@pytest.mark.parametrize(
    ("header", "separator", "comment_header"),
    [
        ("Q 1/nm I Error_CombinedStandard", " ", False),
        ("Q 1/nm I Error_CombinedStandard", " ", True),
        ("Q 1/nm,I,Error_CombinedStandard", ",", False),
        ('"Q 1/nm";"I/cm";Error_CombinedStandard', ";", False),
        ('"Q 1/nm" "I/cm" Error_CombinedStandard', " ", False),
    ],
)
def test_read_external_1d_profile_counts_explicit_nan_physical_fields(
    tmp_path: Path,
    header: str,
    separator: str,
    comment_header: bool,
):
    f = tmp_path / "explicit_nan_uncertainty.dat"
    prefix = "# " if comment_header else ""
    f.write_text(
        f"{prefix}{header}\n"
        f"1.0{separator}100{separator}NaN\n"
        f"2.0{separator}90{separator}NaN\n"
        f"3.0{separator}80{separator}NaN\n",
        encoding="utf-8",
    )

    out = read_external_1d_profile(f)

    assert out["x_unit"] == "nm^-1"
    assert out["i_col"] in {"I", "I/cm"}
    assert out["err_col"] == "Error_CombinedStandard"
    np.testing.assert_allclose(out["intensity"], [100.0, 90.0, 80.0])
    assert np.all(np.isnan(out["uncertainty"]))


def test_read_external_1d_profile_keeps_mixed_nan_uncertainty_aligned(tmp_path: Path):
    f = tmp_path / "mixed_nan_uncertainty.csv"
    f.write_text(
        "Q 1/nm,I,Error_CombinedStandard\n"
        "1.0,100,5\n2.0,90,NaN\n3.0,80,4\n",
        encoding="utf-8",
    )

    out = read_external_1d_profile(f)

    np.testing.assert_allclose(out["uncertainty"][::2], [5.0, 4.0])
    assert np.isnan(out["uncertainty"][1])


@pytest.mark.parametrize(
    ("header", "separator", "comment_header"),
    [
        ("Q 1/nm I", " ", False),
        ("Q 1/nm I", " ", True),
        ('"Q 1/nm",I', ",", False),
        ('"Q 1/nm";I', ";", False),
    ],
)
def test_read_external_1d_profile_ignores_unquoted_inline_comments_in_width_scan(
    tmp_path: Path,
    header: str,
    separator: str,
    comment_header: bool,
):
    f = tmp_path / "inline_comment_width.dat"
    prefix = "# " if comment_header else ""
    f.write_text(
        f"{prefix}{header}\n"
        f"0.1{separator}100 # frame one\n"
        f"0.2{separator}90\n"
        f"0.3{separator}80 # frame three\n",
        encoding="utf-8",
    )

    out = read_external_1d_profile(f)

    assert out["x_unit"] == "nm^-1"
    np.testing.assert_allclose(out["x"], [0.1, 0.2, 0.3])
    np.testing.assert_allclose(out["intensity"], [100.0, 90.0, 80.0])


def test_read_external_1d_profile_keeps_hash_inside_quoted_data_field(
    tmp_path: Path,
):
    f = tmp_path / "quoted_hash_width.dat"
    f.write_text(
        'Q 1/nm I tag\n'
        '0.1 100 "frame # one"\n'
        '0.2 90 "frame # two"\n'
        '0.3 80 "frame # three"\n',
        encoding="utf-8",
    )

    out = read_external_1d_profile(f)

    assert out["x_unit"] == "nm^-1"
    np.testing.assert_allclose(out["intensity"], [100.0, 90.0, 80.0])


def test_read_external_1d_profile_rejects_quoted_conflicting_q_header(tmp_path: Path):
    f = tmp_path / "quoted_conflicting_q_header.csv"
    f.write_text(
        '"Q (nm^-1) [A^-1]",I\n'
        "1.0,100\n2.0,90\n3.0,80\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError):
        read_external_1d_profile(f)


def test_read_external_1d_profile_uses_data_width_to_keep_custom_column(
    tmp_path: Path,
):
    valid = tmp_path / "custom_column_valid.dat"
    valid.write_text(
        "Q 1/nm A I/cm sigma\n"
        "0.10 1 100 5\n"
        "0.20 2 90 4\n"
        "0.30 3 80 4\n",
        encoding="utf-8",
    )
    out = read_external_1d_profile(valid)
    assert out["x_col"] == "Q 1/nm"
    assert out["i_col"] == "I/cm"
    np.testing.assert_allclose(out["intensity"], [100.0, 90.0, 80.0])

    ambiguous = tmp_path / "custom_column_ambiguous.dat"
    ambiguous.write_text(
        "Q 1/nm A I/cm sigma\n"
        "0.10 1 100\n"
        "0.20 2 90\n"
        "0.30 3 80\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="Malformed Q-unit delimiter"):
        read_external_1d_profile(ambiguous)


@pytest.mark.parametrize(
    "header",
    [
        "Q nm-10 I Error",
        "Q nm1 I Error",
        "Q Q (nm^-1) I Error",
        "Q invnm2 I Error",
        "# Q nm-10 I Error",
        "# Q nm1 I Error",
        "# Q Q (nm^-1) I Error",
        "# Q invnm2 I Error",
    ],
)
def test_read_external_1d_profile_rejects_malformed_q_adjacency(
    tmp_path: Path,
    header: str,
):
    f = tmp_path / "malformed_q_adjacency.dat"
    f.write_text(
        f"{header}\n"
        "0.10 100 5\n"
        "0.20 90 4\n"
        "0.30 80 4\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError):
        read_external_1d_profile(f)


@pytest.mark.parametrize("header", ["Q (nm^-1) [A^-1] I", "Q nm^-10 I"])
def test_read_external_1d_profile_preserves_invalid_q_unit_header(
    tmp_path: Path,
    header: str,
):
    f = tmp_path / "invalid_q_unit_header.dat"
    f.write_text(
        f"{header}\n"
        "0.10 100 5\n"
        "0.20 90 4\n"
        "0.30 80 4\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Unsupported or malformed Q-unit header"):
        read_external_1d_profile(f)


@pytest.mark.parametrize("n_columns", [2, 3])
def test_read_external_1d_profile_keeps_numeric_data_after_description_comment(
    tmp_path: Path,
    n_columns: int,
):
    f = tmp_path / "description_without_header.dat"
    rows = [
        "0.10 100" + (" 5" if n_columns == 3 else ""),
        "0.20 90" + (" 4" if n_columns == 3 else ""),
        "0.30 80" + (" 4" if n_columns == 3 else ""),
    ]
    f.write_text("# Integrated SAXS profile\n" + "\n".join(rows) + "\n", encoding="utf-8")

    out = read_external_1d_profile(f)

    np.testing.assert_allclose(out["x"], [0.10, 0.20, 0.30])
    np.testing.assert_allclose(out["intensity"], [100.0, 90.0, 80.0])


def test_read_external_1d_profile_keeps_position_fallback_for_numeric_file(
    tmp_path: Path,
):
    f = tmp_path / "headerless_numeric.dat"
    f.write_text(
        "0.01 10 1\n"
        "0.02 9 1\n"
        "0.03 8 1\n",
        encoding="utf-8",
    )

    out = read_external_1d_profile(f)

    np.testing.assert_allclose(out["x"], [0.01, 0.02, 0.03])
    np.testing.assert_allclose(out["intensity"], [10.0, 9.0, 8.0])


@pytest.mark.parametrize("nonfinite_token", ["NaN", "Inf"])
def test_read_external_1d_profile_accepts_nonfinite_token_in_headerless_first_row(
    tmp_path: Path,
    nonfinite_token: str,
):
    f = tmp_path / "headerless_nonfinite_third_column.dat"
    f.write_text(
        f"0.10 10 {nonfinite_token}\n"
        "0.20 20 200\n"
        "0.30 30 300\n",
        encoding="utf-8",
    )

    out = read_external_1d_profile(f)

    np.testing.assert_allclose(out["x"], [0.10, 0.20, 0.30])
    np.testing.assert_allclose(out["intensity"], [10.0, 20.0, 30.0])
    assert out["err_col"] == ""
    assert np.all(np.isnan(out["uncertainty"]))


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
