from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from saxsabs.workflows import bl19b2_abs2d as workflow


def _paths(tmp_path):
    return workflow.OutputPaths(
        h5=tmp_path / "images_h5" / "frame.h5",
        edf=tmp_path / "images_edf" / "frame.edf",
        metadata=tmp_path / "metadata" / "frame.json",
        preview=tmp_path / "previews" / "frame.png",
    )


@pytest.mark.parametrize("status", ["partial", "failed", "complete"])
def test_only_complete_run_clears_incomplete_publication_marker(tmp_path, monkeypatch, status):
    output = tmp_path / "output"
    config = workflow.BL19B2Abs2DConfig(input_root=tmp_path / "raw", output_root=output)
    monkeypatch.setattr(workflow, "validate_config", lambda config: None)
    monkeypatch.setattr(workflow, "_load_run_control_inputs", lambda config: SimpleNamespace(
        include_manifest=None
    ))
    refs = workflow.ReferencePaths(dark=Path("dark"), background=Path("bg"), standard=Path("std"))
    monkeypatch.setattr(workflow, "find_reference_paths", lambda *args, **kwargs: refs)
    monkeypatch.setattr(workflow, "scan_inputs", lambda *args, **kwargs: ([], []))
    monkeypatch.setattr(workflow, "validate_output_collisions", lambda *args, **kwargs: None)
    monkeypatch.setattr(workflow, "capture_detector_source", lambda path: None)
    monkeypatch.setattr(workflow, "_run_bl19b2_abs2d_locked", lambda *args: {"status": status})
    assert workflow.run_bl19b2_abs2d(config)["status"] == status
    assert (output / ".saxsabs-incomplete").exists() is (status != "complete")


def _prepare(tmp_path, monkeypatch):
    paths = _paths(tmp_path)
    source = tmp_path / "source.tif"
    source.write_bytes(b"immutable raw source")
    identity = {"sha256": hashlib.sha256(source.read_bytes()).hexdigest()}
    monkeypatch.setattr(workflow, "_source_identity", lambda _source: identity)
    members = workflow._frame_members(paths, True)
    digests = {}
    for name, target in members.items():
        target.parent.mkdir(parents=True, exist_ok=True)
        content = (
            json.dumps({"source_identity": identity}).encode()
            if name == "metadata" else f"complete {name}".encode()
        )
        workflow._staged_frame_path(target).write_bytes(content)
        digests[name] = hashlib.sha256(content).hexdigest()
    journal = {"processing_signature": "signature", "write_preview": True,
               "state": "prepared", "sha256": digests}
    workflow._write_json(workflow._frame_journal_path(paths), journal)
    return paths, source, identity, digests


def test_interrupted_commit_finishes_all_members_and_metadata_last(tmp_path, monkeypatch):
    paths, source, _identity, digests = _prepare(tmp_path, monkeypatch)
    workflow._staged_frame_path(paths.h5).replace(paths.h5)
    published = []
    replace = Path.replace

    def record_replace(path, target):
        published.append(target)
        return replace(path, target)

    monkeypatch.setattr(Path, "replace", record_replace)
    workflow._recover_frame_publication(paths, source=source, processing_signature="signature")
    assert published[-1] == paths.metadata
    for name, target in workflow._frame_members(paths, True).items():
        assert workflow._file_sha256(target) == digests[name]
        assert not workflow._staged_frame_path(target).exists()
    assert not workflow._frame_journal_path(paths).exists()


@pytest.mark.parametrize("changed_source", [False, True])
def test_recovery_rejects_invalid_prepared_set_before_publication(
    tmp_path, monkeypatch, changed_source
):
    paths, source, identity, _digests = _prepare(tmp_path, monkeypatch)
    if changed_source:
        identity["sha256"] = "changed source"
    else:
        workflow._staged_frame_path(paths.preview).write_bytes(b"truncated PNG")
    with pytest.raises(ValueError, match="identity mismatch|checksum mismatch"):
        workflow._recover_frame_publication(paths, source=source, processing_signature="signature")
    assert not any(path.exists() for path in workflow._frame_members(paths, True).values())
    assert workflow._frame_journal_path(paths).exists()


def test_interrupted_writing_discards_only_owned_staging_preserving_valid_outputs(tmp_path):
    paths = _paths(tmp_path)
    paths.metadata.parent.mkdir(parents=True)
    paths.h5.parent.mkdir(parents=True)
    paths.h5.write_bytes(b"previous valid output")
    workflow._staged_frame_path(paths.h5).write_bytes(b"partial new output")
    workflow._write_json(workflow._frame_journal_path(paths), {
        "processing_signature": "signature", "write_preview": False, "state": "writing"
    })
    workflow._recover_frame_publication(
        paths, source=tmp_path / "source.tif", processing_signature="signature"
    )
    assert paths.h5.read_bytes() == b"previous valid output"
    assert not workflow._staged_frame_path(paths.h5).exists()
    assert not workflow._frame_journal_path(paths).exists()


@pytest.mark.parametrize("preview_state", ["missing", "corrupt", "wrong_checksum", "unbound"])
def test_resume_repairs_required_preview_from_already_verified_image(
    tmp_path, monkeypatch, preview_state
):
    Image = pytest.importorskip("PIL.Image")
    paths = _paths(tmp_path)
    paths.metadata.parent.mkdir(parents=True)
    paths.preview.parent.mkdir(parents=True)
    mask = np.zeros((2, 2), dtype=np.uint8)
    np.save(tmp_path / "mask.npy", mask)
    identity = {"sha256": "raw content hash", "size_bytes": 6, "header": {}}
    metadata = {
        "schema": workflow.SCHEMA_VERSION, "formula_version": workflow.FORMULA_VERSION,
        "processing_signature": "signature", "source_identity": identity,
        "frame_signature": workflow._frame_signature("signature", identity),
        "uncertainty": {"status": "partial"}, "mask": {"npy": "mask.npy"},
        "qc": {"p01": 1.0, "p995": 4.0},
        "outputs": {"preview": "previews/frame.png"},
        "provenance": {"creation_commit": "original-code"},
    }
    if preview_state == "corrupt":
        paths.preview.write_bytes(b"truncated png")
    elif preview_state in {"wrong_checksum", "unbound"}:
        Image.new("RGB", (1, 1)).save(paths.preview)
        if preview_state == "wrong_checksum":
            metadata["outputs"]["preview_sha256"] = "wrong hash"
    workflow._write_json(paths.metadata, metadata)
    verified_image = np.arange(4).reshape(2, 2)
    validated = []

    def validate(*args):
        validated.append(args)
        return verified_image

    def preview(path, image, *, detector_mask, intensity_limits):
        assert image is verified_image
        np.testing.assert_array_equal(detector_mask, mask)
        assert intensity_limits == (1.0, 4.0)
        Image.new("RGB", (2, 2)).save(path)
        return True

    monkeypatch.setattr(workflow, "_source_identity", lambda path: identity)
    monkeypatch.setattr(workflow, "_validate_metadata_processing_signature", lambda metadata: None)
    monkeypatch.setattr(workflow, "_validate_existing_outputs", validate)
    monkeypatch.setattr(workflow, "write_preview_png", preview)
    row = workflow._frame_qc_row_from_metadata(
        source=tmp_path / "raw.tif", rel=Path("raw.tif"), paths=paths,
        expected_signature="signature", require_preview=True,
    )
    assert row["status"] == "success_existing"
    assert len(validated) == 1
    updated = json.loads(paths.metadata.read_text(encoding="utf-8"))
    assert updated["provenance"] == metadata["provenance"]
    assert updated["outputs"]["preview_sha256"] == workflow._file_sha256(paths.preview)
