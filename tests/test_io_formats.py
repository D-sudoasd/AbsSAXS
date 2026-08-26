"""Tests for canSAS XML and NXcanSAS HDF5 I/O round-trip."""

import xml.etree.ElementTree as ET

import numpy as np
import pytest

from saxsabs.io.writers import write_cansas1d_xml, write_nxcansas_h5
from saxsabs.io.parsers import read_cansas1d_xml, read_external_1d_profile


ABS_META = {
    "intensity_state": "absolute_cm^-1",
    "intensity_unit": "1/cm",
}


def _meta(**extra):
    return {**ABS_META, **extra}


# ---------------------------------------------------------------------------
# canSAS 1D XML round-trip
# ---------------------------------------------------------------------------
class TestCanSAS1DXML:
    def _make_data(self, n=50):
        q = np.linspace(0.01, 0.30, n)
        i_abs = 100.0 / q
        err = np.full(n, 0.5)
        return q, i_abs, err

    def test_write_read_roundtrip(self, tmp_path):
        q, i_abs, err = self._make_data()
        xml_path = tmp_path / "test.xml"
        write_cansas1d_xml(xml_path, q, i_abs, err, metadata=_meta(title="round-trip test"))
        assert xml_path.exists()

        result = read_cansas1d_xml(xml_path)
        assert "i_abs" in result
        assert "i_rel" not in result
        assert result["intensity_state"] == "absolute_cm^-1"
        assert result["x_unit"] == "A^-1"
        np.testing.assert_allclose(result["x"], q, rtol=1e-6)
        np.testing.assert_allclose(result["i_abs"], i_abs, rtol=1e-6)
        np.testing.assert_allclose(result["err_abs"], err, rtol=1e-6)

    def test_write_no_error(self, tmp_path):
        q, i_abs, _ = self._make_data()
        xml_path = tmp_path / "no_err.xml"
        write_cansas1d_xml(xml_path, q, i_abs, metadata=ABS_META)
        result = read_cansas1d_xml(xml_path)
        np.testing.assert_allclose(result["x"], q, rtol=1e-6)

    def test_reader_rejects_inconsistent_q_units(self, tmp_path):
        q, i_abs, err = self._make_data(4)
        xml_path = tmp_path / "inconsistent-q-units.xml"
        write_cansas1d_xml(xml_path, q, i_abs, err, metadata=ABS_META)

        tree = ET.parse(xml_path)
        namespace = "{urn:cansas1d:1.1}"
        q_elements = tree.getroot().iter(f"{namespace}Q")
        next(q_elements)
        second = next(q_elements)
        second.set("unit", "1/nm")
        tree.write(xml_path, encoding="utf-8", xml_declaration=True)

        with pytest.raises(ValueError, match="inconsistent Q units"):
            read_cansas1d_xml(xml_path)

    def test_auto_detect_xml_extension(self, tmp_path):
        """read_external_1d_profile should auto-detect .xml files."""
        q, i_abs, err = self._make_data()
        xml_path = tmp_path / "auto.xml"
        write_cansas1d_xml(xml_path, q, i_abs, err, metadata=ABS_META)
        result = read_external_1d_profile(str(xml_path))
        np.testing.assert_allclose(result["x"], q, rtol=1e-6)
        assert "i_abs" in result
        assert "i_rel" not in result

    def test_metadata_preserved(self, tmp_path):
        q, i_abs, err = self._make_data(10)
        xml_path = tmp_path / "meta.xml"
        meta = {
            "title": "SAXS test",
            "run": "run42",
            "wavelength_A": 1.5406,
            "sdd_m": 2.0,
            "sample_name": "glass",
        }
        out = write_cansas1d_xml(xml_path, q, i_abs, err, metadata=_meta(**meta))
        assert out == xml_path

    def test_write_includes_schema_required_notes(self, tmp_path):
        q, i_abs, err = self._make_data(3)
        xml_path = tmp_path / "schema-required-notes.xml"

        write_cansas1d_xml(xml_path, q, i_abs, err, metadata=ABS_META)

        namespace = {"cansas": "urn:cansas1d:1.1"}
        root = ET.parse(xml_path).getroot()
        entry = root.find("cansas:SASentry", namespace)
        assert entry is not None
        process = entry.find("cansas:SASprocess", namespace)
        assert process is not None
        assert process.find("cansas:SASprocessnote", namespace) is not None
        assert entry.find("cansas:SASnote", namespace) is not None

    def test_inherited_thickness_provenance_roundtrip(self, tmp_path):
        q, i_abs, err = self._make_data(10)
        xml_path = tmp_path / "thickness.xml"
        write_cansas1d_xml(
            xml_path,
            q,
            i_abs,
            err,
            metadata=_meta(
                thickness_cm="0.1",
                thickness_source="upstream sample cell record",
            ),
        )
        provenance = read_cansas1d_xml(xml_path)["operator_provenance"]
        assert provenance["thickness_cm"] == "0.1"
        assert provenance["thickness_source"] == "upstream sample cell record"

    def test_write_refuses_unlabeled_intensity(self, tmp_path):
        q, i_abs, err = self._make_data(3)
        with pytest.raises(ValueError, match="intensity_state=absolute_cm\\^-1"):
            write_cansas1d_xml(tmp_path / "unlabeled.xml", q, i_abs, err)

    def test_write_refuses_unitless_absolute_label(self, tmp_path):
        q, i_abs, err = self._make_data(3)
        with pytest.raises(ValueError, match="absolute_cm\\^-1|cm\\^-1 intensity_unit"):
            write_cansas1d_xml(
                tmp_path / "unitless.xml",
                q,
                i_abs,
                err,
                metadata={"intensity_state": "absolute"},
            )

    def test_write_shape_mismatch_raises(self, tmp_path):
        xml_path = tmp_path / "bad.xml"
        try:
            write_cansas1d_xml(
                xml_path,
                np.array([0.1, 0.2, 0.3]),
                np.array([10.0, 9.0]),
                metadata=ABS_META,
            )
        except ValueError as exc:
            assert "same shape" in str(exc)
        else:
            raise AssertionError("Expected ValueError for mismatched q/i shapes")

    @pytest.mark.parametrize("bad_value", [np.nan, np.inf, -np.inf])
    def test_write_rejects_nonfinite_q(self, tmp_path, bad_value):
        with pytest.raises(ValueError, match="q must contain only finite values"):
            write_cansas1d_xml(
                tmp_path / "bad-q.xml",
                np.array([0.1, bad_value]),
                np.array([10.0, 9.0]),
                metadata=ABS_META,
            )

    @pytest.mark.parametrize("bad_value", [np.nan, np.inf, -np.inf])
    def test_write_rejects_nonfinite_intensity(self, tmp_path, bad_value):
        with pytest.raises(ValueError, match="intensity must contain only finite values"):
            write_cansas1d_xml(
                tmp_path / "bad-i.xml",
                np.array([0.1, 0.2]),
                np.array([10.0, bad_value]),
                metadata=ABS_META,
            )

    @pytest.mark.parametrize(
        "q,i,err",
        [
            (np.array([[0.1, 0.2]]), np.array([[10.0, 9.0]]), None),
            (np.array([]), np.array([]), None),
            (np.array([0.1, 0.2]), np.array([10.0, 9.0]), np.array([1.0, -1.0])),
            (np.array([0.1, 0.2]), np.array([10.0, 9.0]), np.array([1.0, np.inf])),
        ],
    )
    def test_write_rejects_invalid_1d_or_uncertainty_inputs(self, tmp_path, q, i, err):
        with pytest.raises(ValueError):
            write_cansas1d_xml(tmp_path / "invalid-input.xml", q, i, err, metadata=ABS_META)

    def test_reader_tracks_profile_without_i_dev(self, tmp_path):
        q, i_abs, _ = self._make_data(4)
        result = read_cansas1d_xml(
            write_cansas1d_xml(tmp_path / "no-idev.xml", q, i_abs, metadata=ABS_META)
        )

        assert result["err_col"] == ""
        assert np.all(np.isnan(result["uncertainty"]))

    def test_reader_accepts_equivalent_i_units_but_rejects_missing_or_conflicting_units(
        self, tmp_path
    ):
        q, i_abs, err = self._make_data(4)
        xml_path = tmp_path / "units.xml"
        write_cansas1d_xml(xml_path, q, i_abs, err, metadata=ABS_META)
        tree = ET.parse(xml_path)
        namespace = "{urn:cansas1d:1.1}"
        i_elements = list(tree.getroot().iter(f"{namespace}I"))
        i_elements[1].set("unit", "cm^-1")
        tree.write(xml_path, encoding="utf-8", xml_declaration=True)
        assert read_cansas1d_xml(xml_path)["intensity_unit"] == "1/cm"

        tree = ET.parse(xml_path)
        list(tree.getroot().iter(f"{namespace}I"))[1].attrib.pop("unit")
        tree.write(xml_path, encoding="utf-8", xml_declaration=True)
        with pytest.raises(ValueError, match="mixed/missing I units"):
            read_cansas1d_xml(xml_path)

        write_cansas1d_xml(xml_path, q, i_abs, err, metadata=ABS_META)
        tree = ET.parse(xml_path)
        next(tree.getroot().iter(f"{namespace}Idev")).set("unit", "1/nm")
        tree.write(xml_path, encoding="utf-8", xml_declaration=True)
        with pytest.raises(ValueError, match="Idev units"):
            read_cansas1d_xml(xml_path)

        write_cansas1d_xml(xml_path, q, i_abs, err, metadata=ABS_META)
        tree = ET.parse(xml_path)
        for element in tree.getroot().iter(f"{namespace}Idev"):
            element.attrib.pop("unit")
        tree.write(xml_path, encoding="utf-8", xml_declaration=True)
        with pytest.raises(ValueError, match="Idev units are missing"):
            read_cansas1d_xml(xml_path)

    @pytest.mark.parametrize("bad_value", ["nan", "inf", "-inf"])
    def test_reader_rejects_nonfinite_xml_q_or_i(self, tmp_path, bad_value):
        q, i_abs, _ = self._make_data(3)
        xml_path = tmp_path / "bad-xml.xml"
        write_cansas1d_xml(xml_path, q, i_abs, metadata=ABS_META)
        tree = ET.parse(xml_path)
        first_q = next(tree.getroot().iter("{urn:cansas1d:1.1}Q"))
        first_q.text = bad_value
        tree.write(xml_path, encoding="utf-8", xml_declaration=True)
        with pytest.raises(ValueError, match="finite"):
            read_cansas1d_xml(xml_path)

    @pytest.mark.parametrize("bad_value", ["inf", "-inf", "-0.1"])
    def test_reader_rejects_invalid_xml_i_dev(self, tmp_path, bad_value):
        q, i_abs, err = self._make_data(3)
        xml_path = tmp_path / "bad-idev.xml"
        write_cansas1d_xml(xml_path, q, i_abs, err, metadata=ABS_META)
        tree = ET.parse(xml_path)
        next(tree.getroot().iter("{urn:cansas1d:1.1}Idev")).text = bad_value
        tree.write(xml_path, encoding="utf-8", xml_declaration=True)
        with pytest.raises(ValueError, match="Idev"):
            read_cansas1d_xml(xml_path)


# ---------------------------------------------------------------------------
# NXcanSAS HDF5 round-trip (skip only these tests if h5py is unavailable)
# ---------------------------------------------------------------------------
try:
    import h5py
except ImportError:  # pragma: no cover - exercised in minimal installations
    h5py = None
from saxsabs.io.parsers import read_nxcansas_h5  # noqa: E402


class TestNXcanSASHDF5:
    @pytest.fixture(autouse=True)
    def _require_h5py(self):
        pytest.importorskip("h5py")

    def _make_data(self, n=50):
        q = np.linspace(0.01, 0.30, n)
        i_abs = 100.0 / q
        err = np.full(n, 0.5)
        return q, i_abs, err

    def test_write_read_roundtrip(self, tmp_path):
        q, i_abs, err = self._make_data()
        h5_path = tmp_path / "test.h5"
        write_nxcansas_h5(h5_path, q, i_abs, err, metadata=_meta(title="h5 round-trip"))
        assert h5_path.exists()

        result = read_nxcansas_h5(h5_path)
        assert "i_abs" in result
        assert "i_rel" not in result
        assert result["x_unit"] == "A^-1"
        np.testing.assert_allclose(result["x"], q, rtol=1e-10)
        np.testing.assert_allclose(result["i_abs"], i_abs, rtol=1e-10)
        np.testing.assert_allclose(result["err_abs"], err, rtol=1e-10)

    def test_auto_detect_h5_extension(self, tmp_path):
        """read_external_1d_profile should auto-detect .h5 files."""
        q, i_abs, err = self._make_data()
        h5_path = tmp_path / "auto.h5"
        write_nxcansas_h5(h5_path, q, i_abs, err, metadata=ABS_META)
        result = read_external_1d_profile(str(h5_path))
        np.testing.assert_allclose(result["x"], q, rtol=1e-10)
        assert "i_abs" in result

    def test_inherited_thickness_provenance_roundtrip(self, tmp_path):
        q, i_abs, err = self._make_data(10)
        h5_path = tmp_path / "thickness.h5"
        write_nxcansas_h5(
            h5_path,
            q,
            i_abs,
            err,
            metadata=_meta(
                thickness_cm="0.1",
                thickness_source="upstream sample cell record",
            ),
        )
        provenance = read_nxcansas_h5(h5_path)["operator_provenance"]
        assert provenance["thickness_cm"] == "0.1"
        assert provenance["thickness_source"] == "upstream sample cell record"

    @pytest.mark.parametrize("bad_value", [np.nan, np.inf, -np.inf])
    def test_write_rejects_nonfinite_q(self, tmp_path, bad_value):
        with pytest.raises(ValueError, match="q must contain only finite values"):
            write_nxcansas_h5(
                tmp_path / "bad-q.h5",
                np.array([0.1, bad_value]),
                np.array([10.0, 9.0]),
                metadata=ABS_META,
            )

    @pytest.mark.parametrize("bad_value", [np.nan, np.inf, -np.inf])
    def test_write_rejects_nonfinite_intensity(self, tmp_path, bad_value):
        with pytest.raises(ValueError, match="intensity must contain only finite values"):
            write_nxcansas_h5(
                tmp_path / "bad-i.h5",
                np.array([0.1, 0.2]),
                np.array([10.0, bad_value]),
                metadata=ABS_META,
            )

    def test_no_error_dataset(self, tmp_path):
        q, i_abs, _ = self._make_data()
        h5_path = tmp_path / "no_err.h5"
        write_nxcansas_h5(h5_path, q, i_abs, metadata=ABS_META)
        result = read_nxcansas_h5(h5_path)
        np.testing.assert_allclose(result["x"], q, rtol=1e-10)
        assert np.all(np.isnan(result["err_abs"]))

    def test_reader_preserves_nm_inverse_q_units_without_conversion(self, tmp_path):
        h5_path = tmp_path / "nm-q.h5"
        q = np.array([0.1, 0.2, 0.3])
        intensity = np.array([10.0, 9.0, 8.0])
        with h5py.File(h5_path, "w") as f:
            entry = f.create_group("sasentry01")
            data = entry.create_group("sasdata01")
            data.attrs["canSAS_class"] = "SASdata"
            q_ds = data.create_dataset("Q", data=q)
            q_ds.attrs["units"] = "1/nm"
            i_ds = data.create_dataset("I", data=intensity)
            i_ds.attrs["units"] = "1/cm"

        result = read_nxcansas_h5(h5_path)
        assert result["x_unit"] == "nm^-1"
        np.testing.assert_allclose(result["x"], q)

    def test_write_shape_mismatch_raises(self, tmp_path):
        h5_path = tmp_path / "bad.h5"
        try:
            write_nxcansas_h5(
                h5_path,
                np.array([0.1, 0.2, 0.3]),
                np.array([10.0, 9.0]),
                metadata=ABS_META,
            )
        except ValueError as exc:
            assert "same shape" in str(exc)
        else:
            raise AssertionError("Expected ValueError for mismatched q/i shapes")

    def test_write_refuses_unlabeled_intensity(self, tmp_path):
        q, i_abs, err = self._make_data(3)
        with pytest.raises(ValueError, match="intensity_state=absolute_cm\\^-1"):
            write_nxcansas_h5(tmp_path / "unlabeled.h5", q, i_abs, err)

    def test_reader_rejects_malformed_dataset_lengths(self, tmp_path):
        h5_path = tmp_path / "malformed.h5"
        with h5py.File(h5_path, "w") as f:
            entry = f.create_group("sasentry01")
            data = entry.create_group("sasdata01")
            data.attrs["canSAS_class"] = "SASdata"
            data.create_dataset("Q", data=np.array([0.1, 0.2, 0.3]))
            data.create_dataset("I", data=np.array([10.0, 9.0]))

        try:
            read_nxcansas_h5(h5_path)
        except ValueError as exc:
            assert "length mismatch" in str(exc)
        else:
            raise AssertionError("Expected ValueError for malformed NXcanSAS file")

    @pytest.mark.parametrize(
        "q,i,err",
        [
            (np.array([[0.1, 0.2]]), np.array([[10.0, 9.0]]), None),
            (np.array([]), np.array([]), None),
            (np.array([0.1, 0.2]), np.array([10.0, 9.0]), np.array([1.0, -1.0])),
            (np.array([0.1, 0.2]), np.array([10.0, 9.0]), np.array([1.0, np.inf])),
        ],
    )
    def test_write_rejects_invalid_1d_or_uncertainty_inputs(self, tmp_path, q, i, err):
        with pytest.raises(ValueError):
            write_nxcansas_h5(tmp_path / "invalid-input.h5", q, i, err, metadata=ABS_META)

    def test_writer_is_atomic_when_metadata_assignment_fails(self, tmp_path):
        q, i_abs, err = self._make_data(4)
        target = tmp_path / "atomic.h5"
        write_nxcansas_h5(target, q, i_abs, err, metadata=ABS_META)
        original = target.read_bytes()

        with pytest.raises((TypeError, ValueError)):
            write_nxcansas_h5(
                target,
                q,
                i_abs,
                err,
                metadata=_meta(title=None),
            )

        assert target.read_bytes() == original
        assert not list(tmp_path.glob(f".{target.name}.*.tmp"))

    @pytest.mark.parametrize("bad_value", [np.nan, np.inf, -np.inf])
    def test_reader_rejects_nonfinite_hdf_q_or_i(self, tmp_path, bad_value):
        path = tmp_path / "bad-values.h5"
        with h5py.File(path, "w") as f:
            data = f.create_group("sasdata01")
            data.attrs["canSAS_class"] = "SASdata"
            data.create_dataset("Q", data=np.array([0.1, bad_value, 0.3]))
            data.create_dataset("I", data=np.array([10.0, 9.0, 8.0]))
        with pytest.raises(ValueError, match="finite"):
            read_nxcansas_h5(path)

    def test_reader_rejects_non_1d_hdf_datasets(self, tmp_path):
        path = tmp_path / "two-dimensional.h5"
        with h5py.File(path, "w") as f:
            data = f.create_group("sasdata01")
            data.attrs["canSAS_class"] = "SASdata"
            data.create_dataset("Q", data=np.ones((2, 2)))
            data.create_dataset("I", data=np.ones((2, 2)))
        with pytest.raises(ValueError, match="1-D"):
            read_nxcansas_h5(path)

    @pytest.mark.parametrize("bad_value", [np.inf, -1.0])
    def test_reader_rejects_invalid_hdf_i_dev(self, tmp_path, bad_value):
        path = tmp_path / "bad-idev.h5"
        with h5py.File(path, "w") as f:
            data = f.create_group("sasdata01")
            data.attrs["canSAS_class"] = "SASdata"
            data.create_dataset("Q", data=np.array([0.1, 0.2, 0.3]))
            data.create_dataset("I", data=np.array([10.0, 9.0, 8.0]))
            data.create_dataset("Idev", data=np.array([0.1, bad_value, 0.1]))
        with pytest.raises(ValueError, match="Idev"):
            read_nxcansas_h5(path)
