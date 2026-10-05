"""Check coherent single-read text profiles and CLI table reuse."""

import os
from pathlib import Path

import numpy as np
import pytest

from saxsabs import cli
from saxsabs.io import parsers


@pytest.mark.parametrize(
    ("header", "rows", "parses"),
    [
        ("Q (nm^-1),I,alternate,sigma", "0.1,10,5,nan\n0.2,20,6,nan\n0.3,30,7,nan", 3),
        ("# Q (nm^-1) I alternate sigma", "0.1 10 5 nan\n0.2 20 6 nan\n0.3 30 7 nan", 4),
        (
            "Q (nm^-1);I;alternate;sigma",
            "0,100000;10,000000;5,000000;nan\n"
            "0,200000;20,000000;6,000000;nan\n0,300000;30,000000;7,000000;nan",
            0,
        ),
    ],
)
def test_column_override_reads_once_and_reuses_table(tmp_path, monkeypatch, header, rows, parses):
    source = tmp_path / "profile.dat"
    source.write_text("\ufeff# operator: beamline_user\n" + header + "\n" + rows, encoding="utf-8")
    original_open = Path.open
    original_csv = parsers.pd.read_csv
    reads = 0
    table_parses = 0

    def counted_open(path, *args, **kwargs):
        nonlocal reads
        if path == source:
            reads += 1
        return original_open(path, *args, **kwargs)

    def counted_csv(*args, **kwargs):
        nonlocal table_parses
        table_parses += 1
        return original_csv(*args, **kwargs)

    monkeypatch.setattr(Path, "open", counted_open)
    monkeypatch.setattr(parsers.pd, "read_csv", counted_csv)
    profile = cli._read_profile_for_estimate(
        source, q_col=None, i_col="alternate", profile_label="sample"
    )
    np.testing.assert_allclose(profile["x"], [0.1, 0.2, 0.3])
    np.testing.assert_allclose(parsers.profile_intensity(profile), [5, 6, 7])
    assert np.isnan(parsers.profile_uncertainty(profile)).all()
    assert profile["x_unit"] == "nm^-1"
    assert reads == 1
    assert table_parses == parses


def test_text_snapshot_is_coherent_and_next_call_observes_change(tmp_path, monkeypatch):
    source = tmp_path / "profile.csv"
    first = "# calibration_context_fingerprint: Alice\nQ,I\n0.1,10\n0.2,20\n0.3,30\n"
    second = first.replace("Alice", "Carol").replace("10", "40")
    source.write_text(first, encoding="utf-8")
    stamp = source.stat()
    original_csv = parsers.pd.read_csv

    def replace_during_parse(*args, **kwargs):
        source.write_text(second, encoding="utf-8")
        os.utime(source, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
        return original_csv(*args, **kwargs)

    monkeypatch.setattr(parsers.pd, "read_csv", replace_during_parse)
    profile = parsers.read_external_1d_profile(source)
    np.testing.assert_array_equal(parsers.profile_intensity(profile), [10, 20, 30])
    assert profile["operator_provenance"] == {"calibration_context_fingerprint": "Alice"}
    updated = parsers.read_external_1d_profile(source)
    np.testing.assert_array_equal(parsers.profile_intensity(updated), [40, 20, 30])
    assert updated["operator_provenance"] == {"calibration_context_fingerprint": "Carol"}


def test_non_text_overrides_require_existing_columns(tmp_path):
    source = tmp_path / "profile.xml"
    source.write_text(
        '<SASroot xmlns="urn:cansas1d:1.1"><SASentry><SASdata>'
        + "".join(
            f'<Idata><Q unit="1/nm">{q}</Q><I unit="1/cm">{i}</I></Idata>'
            for q, i in [(0.1, 10), (0.2, 20), (0.3, 30)]
        )
        + "</SASdata></SASentry></SASroot>",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="text table"):
        cli._read_profile_for_estimate(source, q_col=None, i_col="missing", profile_label="sample")
