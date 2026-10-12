from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import benchmark_bl19b2


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_archive_source_uses_its_revision_and_hashes_contents_not_parent_git(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    source_root = tmp_path / ".audit-work" / "performance" / "baseline_source"
    package = source_root / "src" / "saxsabs"
    package.mkdir(parents=True)
    source_a = package / "__init__.py"
    source_b = package / "workflow.py"
    source_a.write_text("VERSION = 'baseline'\n", encoding="utf-8")
    source_b.write_text("def run():\n    return 1\n", encoding="utf-8")
    archive_sha256 = "a" * 64
    (source_root / "SOURCE_REVISION.json").write_text(
        json.dumps({"commit": "archive-commit", "archive_sha256": archive_sha256}),
        encoding="utf-8",
    )

    git_calls: list[list[str]] = []

    def fake_git(command: list[str], **_kwargs: object) -> SimpleNamespace:
        git_calls.append(command)
        if command[-2:] == ["rev-parse", "--show-toplevel"]:
            return SimpleNamespace(returncode=0, stdout=str(tmp_path), stderr="")
        if command[-1] == "status":
            return SimpleNamespace(returncode=0, stdout="?? parent-private-data.tif\n", stderr="")
        raise AssertionError(f"unexpected Git query: {command}")

    monkeypatch.setattr(benchmark_bl19b2.subprocess, "run", fake_git)

    identity = benchmark_bl19b2._git_state(source_root)

    expected_files = {
        "src/saxsabs/__init__.py": _sha256(source_a),
        "src/saxsabs/workflow.py": _sha256(source_b),
    }
    assert identity["source_kind"] == "git_archive"
    assert identity["git_root_matches_source_root"] is False
    assert identity["commit"] == "archive-commit"
    assert identity["archive_sha256"] == archive_sha256
    assert identity["dirty"] is None
    assert identity["dirty_path_count"] is None
    assert identity["source_content"]["files_sha256"] == expected_files
    assert identity["source_content"]["aggregate_sha256"] == benchmark_bl19b2._canonical_sha256(
        expected_files
    )
    assert len(git_calls) == 1


def _build_integration_package(tmp_path: Path) -> tuple[Path, dict[str, object]]:
    output_root = tmp_path / "package"
    integration_root = output_root / "integration"
    profile = integration_root / "profiles" / "sample" / "frame_00001_abs1d_cm-1.csv"
    sidecar = integration_root / "metadata" / "sample" / "frame_00001_abs1d.json"
    manifest = integration_root / "manifests" / "integration_manifest.csv"
    checksum_path = integration_root / "manifests" / "checksums.sha256.csv"
    completion_path = integration_root / "config" / "completion.json"
    profile.parent.mkdir(parents=True)
    sidecar.parent.mkdir(parents=True)
    manifest.parent.mkdir(parents=True)
    completion_path.parent.mkdir(parents=True)
    profile.write_text("q_A^-1,I_abs_cm^-1\n0.1,2.0\n", encoding="utf-8")
    digest = _sha256(profile)
    sidecar.write_text(json.dumps({"profile_sha256": digest}), encoding="utf-8")
    with manifest.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=("relative_path", "status", "profile_csv", "profile_sha256"),
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerow(
            {
                "relative_path": "sample/frame_00001.tif",
                "status": "complete",
                "profile_csv": str(profile),
                "profile_sha256": digest,
            }
        )
    (integration_root / "README.md").write_text("complete\n", encoding="utf-8")

    indexed = sorted(
        path
        for path in integration_root.rglob("*")
        if path.is_file() and path not in {checksum_path, completion_path}
    )
    with checksum_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(benchmark_bl19b2.CHECKSUM_FIELDS)
        for path in indexed:
            writer.writerow(
                [
                    path.relative_to(integration_root).as_posix(),
                    _sha256(path),
                    path.stat().st_size,
                ]
            )
    checksum_data = checksum_path.read_bytes()
    result: dict[str, object] = {
        "status": "complete",
        "run_signature": "run-123",
        "frames": 1,
        "directories": 1,
    }
    completion_path.write_text(
        json.dumps(
            {
                "schema": benchmark_bl19b2.INTEGRATION_SCHEMA,
                "run_signature": result["run_signature"],
                "frames": result["frames"],
                "directories": result["directories"],
                "checksums_manifest": str(checksum_path),
                "checksums_manifest_sha256": hashlib.sha256(checksum_data).hexdigest(),
            }
        ),
        encoding="utf-8",
    )
    result["manifest"] = str(manifest)
    result["checksums"] = str(checksum_path)
    return output_root, result


def test_fresh_scenario_refuses_existing_output_root(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    source_root = tmp_path / "source"
    (source_root / "src" / "saxsabs").mkdir(parents=True)
    input_root = tmp_path / "raw"
    input_root.mkdir()
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({"input_root": str(input_root)}), encoding="utf-8")
    output_root = tmp_path / "existing-output"
    output_root.mkdir()
    marker = output_root / "keep.txt"
    marker.write_text("pre-existing", encoding="utf-8")
    evidence_dir = tmp_path / "evidence"

    return_code = benchmark_bl19b2.main(
        [
            "--source-root",
            str(source_root),
            "--config-json",
            str(config_path),
            "--output-root",
            str(output_root),
            "--evidence-dir",
            str(evidence_dir),
            "--scenario",
            "fresh",
        ]
    )

    assert return_code != 0
    assert "refuses an existing output-root" in capsys.readouterr().err
    assert marker.read_text(encoding="utf-8") == "pre-existing"
    assert not evidence_dir.exists()


def test_integration_validator_rejects_tampered_indexed_file(tmp_path: Path):
    output_root, result = _build_integration_package(tmp_path)

    verified = benchmark_bl19b2.validate_integration_package(output_root, result)
    assert verified == {"checksum_entries": 4, "frames": 1}

    profile = output_root / "integration" / "profiles" / "sample" / "frame_00001_abs1d_cm-1.csv"
    profile.write_text("q_A^-1,I_abs_cm^-1\n0.1,999.0\n", encoding="utf-8")
    with pytest.raises(ValueError, match="integration checksum mismatch"):
        benchmark_bl19b2.validate_integration_package(output_root, result)


def test_child_failure_produces_failed_evidence_and_nonzero_exit(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    source_root = tmp_path / "source"
    (source_root / "src" / "saxsabs").mkdir(parents=True)
    input_root = tmp_path / "raw"
    input_root.mkdir()
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({"input_root": str(input_root)}), encoding="utf-8")
    evidence_dir = tmp_path / "evidence"
    output_root = tmp_path / "new-output"

    return_code = benchmark_bl19b2.main(
        [
            "--source-root",
            str(source_root),
            "--config-json",
            str(config_path),
            "--output-root",
            str(output_root),
            "--evidence-dir",
            str(evidence_dir),
            "--scenario",
            "fresh",
        ]
    )

    assert return_code != 0
    response = json.loads(capsys.readouterr().out)
    report = json.loads(Path(response["report"]).read_text(encoding="utf-8"))
    assert report["status"] == "failed"
    assert report["child_return_code"] != 0
    assert report["child_result"]["status"] == "failed"
    assert "ModuleNotFoundError" in report["child_result"]["error"]
    assert Path(report["stderr_log"]).is_file()
