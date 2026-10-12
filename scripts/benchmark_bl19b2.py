"""Measure a complete BL19B2 2D-to-1D package run in an isolated Python child."""

from __future__ import annotations

import argparse
import cProfile
import csv
from dataclasses import fields
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import platform
import subprocess
import sys
import threading
import time
import traceback
import uuid
from typing import Any


THREAD_ENVIRONMENT = (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
    "VECLIB_MAXIMUM_THREADS",
)
CHECKSUM_FIELDS = ("relative_path", "sha256", "size_bytes")
INTEGRATION_SCHEMA = "saxsabs.bl19b2_integrate1d.v1"
PATH_FIELDS = {
    "input_root",
    "poni_path",
    "pydidas_cali_yaml",
    "mask_path",
    "dark_path",
    "background_path",
    "standard_path",
    "direct_path",
    "include_manifest_path",
    "thickness_derivation_path",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_sha256(value: Any) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _resolve_within(root: Path, raw_path: str, label: str) -> Path:
    """Resolve a package pointer and reject absolute traversal or symlink escapes."""
    if not raw_path or "\\" in raw_path:
        raise ValueError(f"{label} must be a non-empty POSIX relative path")
    relative = PurePosixPath(raw_path)
    if relative.is_absolute() or PureWindowsPath(raw_path).drive or ".." in relative.parts:
        raise ValueError(f"unsafe {label} path: {raw_path!r}")
    candidate = root.joinpath(*relative.parts)
    if candidate.is_symlink():
        raise ValueError(f"{label} must not be a symlink: {candidate}")
    resolved = candidate.resolve(strict=True)
    try:
        resolved.relative_to(root.resolve(strict=True))
    except ValueError as exc:
        raise ValueError(f"{label} escapes its package root: {raw_path!r}") from exc
    if not resolved.is_file():
        raise ValueError(f"{label} is not a file: {resolved}")
    return resolved


def _resolve_reported_file(raw_path: str, root: Path, label: str) -> Path:
    path = Path(raw_path)
    candidate = path if path.is_absolute() else root / path
    if candidate.is_symlink():
        raise ValueError(f"{label} must not be a symlink: {candidate}")
    resolved = candidate.resolve(strict=True)
    try:
        resolved.relative_to(root.resolve(strict=True))
    except ValueError as exc:
        raise ValueError(f"{label} escapes its package root: {raw_path!r}") from exc
    if not resolved.is_file():
        raise ValueError(f"{label} is not a file: {resolved}")
    return resolved


def validate_integration_package(
    output_root: Path,
    result: dict[str, Any],
) -> dict[str, int]:
    """Verify the complete integration checksum index, completion record and frame outputs."""
    integration_root = output_root.resolve(strict=True) / "integration"
    checksum_path = integration_root / "manifests" / "checksums.sha256.csv"
    completion_path = integration_root / "config" / "completion.json"
    manifest_path = integration_root / "manifests" / "integration_manifest.csv"
    for path, label in (
        (checksum_path, "integration checksum manifest"),
        (completion_path, "integration completion manifest"),
        (manifest_path, "integration frame manifest"),
    ):
        if not path.is_file():
            raise ValueError(f"missing {label}: {path}")

    checksum_data = checksum_path.read_bytes()
    try:
        completion = json.loads(completion_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("integration completion manifest is unreadable") from exc
    if completion.get("schema") != INTEGRATION_SCHEMA:
        raise ValueError("integration completion schema mismatch")
    if completion.get("run_signature") != result.get("run_signature"):
        raise ValueError("integration completion run signature mismatch")
    if completion.get("frames") != result.get("frames"):
        raise ValueError("integration completion frame count mismatch")
    if completion.get("directories") != result.get("directories"):
        raise ValueError("integration completion directory count mismatch")
    if completion.get("checksums_manifest_sha256") != hashlib.sha256(checksum_data).hexdigest():
        raise ValueError("integration checksum manifest digest mismatch")
    if Path(str(result.get("checksums", ""))).resolve() != checksum_path.resolve():
        raise ValueError("integration API checksum path mismatch")
    if Path(str(result.get("manifest", ""))).resolve() != manifest_path.resolve():
        raise ValueError("integration API frame manifest path mismatch")
    completion_checksum = Path(str(completion.get("checksums_manifest", "")))
    expected_checksum = checksum_path.resolve()
    if not completion_checksum.is_absolute():
        completion_checksum = integration_root / completion_checksum
    if completion_checksum.resolve() != expected_checksum:
        raise ValueError("integration completion checksum path mismatch")

    try:
        with checksum_path.open("r", encoding="utf-8", newline="") as stream:
            reader = csv.DictReader(stream)
            if tuple(reader.fieldnames or ()) != CHECKSUM_FIELDS:
                raise ValueError("integration checksum manifest columns mismatch")
            entries: dict[str, tuple[str, int]] = {}
            for row in reader:
                relative = row["relative_path"]
                if relative in entries:
                    raise ValueError(f"duplicate integration checksum path: {relative}")
                digest = row["sha256"]
                if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
                    raise ValueError(f"invalid SHA-256 digest for {relative}")
                size = int(row["size_bytes"])
                if size < 0:
                    raise ValueError(f"invalid file size for {relative}")
                entries[relative] = (digest, size)
    except (OSError, csv.Error, KeyError, TypeError, ValueError) as exc:
        if isinstance(exc, ValueError) and str(exc).startswith(("integration ", "duplicate ", "invalid ")):
            raise
        raise ValueError("integration checksum manifest is malformed") from exc

    excluded = {
        "manifests/checksums.sha256.csv",
        "config/completion.json",
    }
    actual_files: set[str] = set()
    for path in integration_root.rglob("*"):
        if path.is_symlink():
            raise ValueError(f"integration package contains a symlink: {path}")
        if path.is_file():
            actual_files.add(path.relative_to(integration_root).as_posix())
    expected_files = actual_files - excluded
    if set(entries) != expected_files:
        missing = sorted(expected_files - set(entries))
        extra = sorted(set(entries) - expected_files)
        raise ValueError(
            f"integration checksum file set mismatch; unindexed={missing[:3]}, stale={extra[:3]}"
        )
    verified_digests: dict[str, str] = {}
    for relative, (expected_digest, expected_size) in entries.items():
        path = _resolve_within(integration_root, relative, "integration checksum entry")
        actual_digest = _sha256(path)
        if path.stat().st_size != expected_size or actual_digest != expected_digest:
            raise ValueError(f"integration checksum mismatch: {relative}")
        verified_digests[relative] = actual_digest

    frame_rows: list[dict[str, str]] = []
    with manifest_path.open("r", encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames or "relative_path" not in reader.fieldnames:
            raise ValueError("integration frame manifest has no relative_path column")
        frame_rows.extend(reader)
    if len(frame_rows) != int(result["frames"]):
        raise ValueError("integration frame manifest count mismatch")
    seen_frames: set[str] = set()
    for row in frame_rows:
        relative_text = row.get("relative_path", "")
        relative = PurePosixPath(relative_text)
        if (
            not relative_text
            or relative.is_absolute()
            or PureWindowsPath(relative_text).drive
            or ".." in relative.parts
            or relative_text in seen_frames
        ):
            raise ValueError(f"invalid or duplicate integration frame path: {relative_text!r}")
        seen_frames.add(relative_text)
        if row.get("status") != "complete":
            raise ValueError(f"incomplete integration frame: {relative_text}")
        frame_file = Path(*relative.parts)
        expected_profile = (
            integration_root
            / "profiles"
            / frame_file.parent
            / f"{frame_file.stem}_abs1d_cm-1.csv"
        )
        expected_sidecar = (
            integration_root
            / "metadata"
            / frame_file.parent
            / f"{frame_file.stem}_abs1d.json"
        )
        profile = _resolve_reported_file(row.get("profile_csv", ""), integration_root, "profile")
        if profile != expected_profile.resolve(strict=True):
            raise ValueError(f"integration profile path mismatch: {relative_text}")
        if not expected_sidecar.is_file():
            raise ValueError(f"missing integration profile metadata: {expected_sidecar}")
        sidecar = json.loads(expected_sidecar.read_text(encoding="utf-8"))
        if sidecar.get("profile_sha256") != row.get("profile_sha256"):
            raise ValueError(f"integration profile metadata digest mismatch: {relative_text}")
        profile_relative = profile.relative_to(integration_root).as_posix()
        if sidecar.get("profile_sha256") != verified_digests.get(profile_relative):
            raise ValueError(f"integration profile digest mismatch: {relative_text}")

    return {"checksum_entries": len(entries), "frames": len(frame_rows)}


def _config_payload(config_path: Path) -> tuple[dict[str, Any], str]:
    def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate config key: {key}")
            result[key] = value
        return result

    raw = config_path.read_bytes()
    try:
        payload = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=unique_object,
            parse_constant=lambda value: (_ for _ in ()).throw(
                ValueError(f"invalid JSON number: {value}")
            ),
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise ValueError(f"config JSON must be valid UTF-8 JSON: {config_path}") from exc
    if not isinstance(payload, dict):
        raise ValueError("config JSON must contain an object")
    if "output_root" in payload:
        raise ValueError("config JSON must omit output_root; pass --output-root separately")
    return payload, hashlib.sha256(raw).hexdigest()


def _build_config(
    payload: dict[str, Any],
    *,
    config_path: Path,
    output_root: Path,
    workflow: Any,
) -> Any:
    allowed = {field.name for field in fields(workflow.BL19B2Abs2DConfig)} - {"output_root"}
    unknown = sorted(set(payload) - allowed)
    if unknown:
        raise ValueError(f"unknown BL19B2 config fields: {', '.join(unknown)}")
    values = dict(payload)
    if "input_root" not in values:
        raise ValueError("config JSON must include input_root")
    for name in PATH_FIELDS:
        value = values.get(name)
        if value is not None:
            path = Path(value)
            if not path.is_absolute():
                path = config_path.parent / path
            values[name] = path.resolve()
    if "q_window" in values:
        values["q_window"] = tuple(values["q_window"])
    values["output_root"] = output_root
    config = workflow.BL19B2Abs2DConfig(**values)
    if config.dry_run:
        raise ValueError("dry_run must be false for a full delivery benchmark")
    if config.overwrite:
        raise ValueError("overwrite must be false for safe fresh and resume scenarios")
    input_root = Path(config.input_root).resolve(strict=True)
    output_root = output_root.resolve()
    try:
        output_root.relative_to(input_root)
    except ValueError:
        pass
    else:
        raise ValueError("output_root must not be inside input_root")
    return config


def _validate_2d_outputs(
    output_root: Path,
    config: Any,
    result: dict[str, Any],
    workflow: Any,
) -> dict[str, int | float]:
    manifest = Path(str(result.get("processing_manifest", ""))).resolve(strict=True)
    expected_manifest = (output_root / "manifests" / "processing_manifest.csv").resolve()
    if manifest != expected_manifest:
        raise ValueError("2D processing manifest path mismatch")
    with manifest.open("r", encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    if not rows:
        raise ValueError("2D processing manifest has no delivered frames")
    if len(rows) != int(result.get("successful_outputs", len(rows))):
        raise ValueError("2D processing manifest output count mismatch")

    explicit_validation_seconds = 0.0
    explicit_validation_count = 0
    resume_validated_count = 0
    for row in rows:
        if row.get("status") not in {"success", "skipped_existing"}:
            raise ValueError(f"2D manifest contains a non-success row: {row.get('status')}")
        hdf5 = _resolve_within(output_root, row.get("hdf5", ""), "2D HDF5 output")
        edf = _resolve_within(output_root, row.get("edf", ""), "2D EDF output")
        metadata_path = _resolve_within(
            output_root, row.get("metadata", ""), "2D metadata output"
        )
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        if metadata.get("processing_signature") != row.get("processing_signature"):
            raise ValueError(f"2D metadata processing signature mismatch: {row.get('relative_path')}")
        if metadata.get("outputs", {}).get("hdf5_sha256") is None:
            raise ValueError(f"2D metadata lacks HDF5 checksum: {row.get('relative_path')}")
        if metadata.get("outputs", {}).get("edf_sha256") is None:
            raise ValueError(f"2D metadata lacks EDF checksum: {row.get('relative_path')}")
        if config.write_preview:
            preview = _resolve_within(output_root, row.get("preview", ""), "2D preview")
            with preview.open("rb") as stream:
                png_signature = stream.read(8)
            if png_signature != b"\x89PNG\r\n\x1a\n":
                raise ValueError(f"2D preview is not a PNG: {preview}")
        if row["status"] == "success":
            paths = workflow.OutputPaths(
                h5=hdf5,
                edf=edf,
                metadata=metadata_path,
                preview=(output_root / row.get("preview", "")) if row.get("preview") else output_root / "previews" / "missing.png",
            )
            started = time.perf_counter()
            workflow._validate_existing_outputs(paths, metadata)
            explicit_validation_seconds += time.perf_counter() - started
            explicit_validation_count += 1
        else:
            # The 2D workflow runs the same full validator while handling skipped resume outputs.
            resume_validated_count += 1
    return {
        "frames": len(rows),
        "explicit_existing_validator_frames": explicit_validation_count,
        "workflow_resume_validator_frames": resume_validated_count,
        "explicit_existing_validator_seconds": explicit_validation_seconds,
    }


def _git_state(source_root: Path) -> dict[str, Any]:
    source_root = source_root.resolve(strict=True)

    def git(*args: str) -> str | None:
        completed = subprocess.run(
            ["git", "-C", str(source_root), *args],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        return completed.stdout.strip() if completed.returncode == 0 else None

    git_root_text = git("rev-parse", "--show-toplevel")
    git_root = Path(git_root_text).resolve() if git_root_text else None
    root_matches = git_root == source_root if git_root is not None else None
    commit: str | None = None
    dirty: bool | None = None
    dirty_path_count: int | None = None
    archive_sha256: str | None = None
    source_kind = "directory"
    if root_matches:
        source_kind = "git_checkout"
        commit = git("rev-parse", "HEAD")
        status = git("status", "--porcelain", "--untracked-files=normal")
        dirty = None if status is None else bool(status)
        dirty_path_count = len(status.splitlines()) if status is not None else None
    else:
        revision_path = source_root / "SOURCE_REVISION.json"
        if revision_path.is_file():
            try:
                revision = json.loads(revision_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise ValueError(f"archive revision manifest is unreadable: {revision_path}") from exc
            commit_value = revision.get("commit")
            archive_value = revision.get("archive_sha256")
            if not isinstance(commit_value, str) or not commit_value.strip():
                raise ValueError("archive revision manifest requires a non-empty commit")
            if (
                not isinstance(archive_value, str)
                or len(archive_value) != 64
                or any(char not in "0123456789abcdefABCDEF" for char in archive_value)
            ):
                raise ValueError("archive revision manifest requires a SHA-256 archive_sha256")
            source_kind = "git_archive"
            commit = commit_value.strip()
            archive_sha256 = archive_value.lower()

    source_files = {
        path.relative_to(source_root).as_posix(): _sha256(path)
        for path in sorted((source_root / "src" / "saxsabs").rglob("*.py"))
        if path.is_file()
    }
    return {
        "source_kind": source_kind,
        "git_root_matches_source_root": root_matches,
        "commit": commit,
        "dirty": dirty,
        "dirty_path_count": dirty_path_count,
        "archive_sha256": archive_sha256,
        "source_content": {
            "aggregate_sha256": _canonical_sha256(source_files),
            "files_sha256": source_files,
        },
    }


def _software_versions(saxsabs: Any) -> dict[str, str | None]:
    versions: dict[str, str | None] = {"saxsabs": getattr(saxsabs, "__version__", None)}
    for distribution in ("pyFAI", "numpy", "h5py", "fabio", "matplotlib", "Pillow", "tifffile"):
        try:
            versions[distribution] = importlib.metadata.version(distribution)
        except importlib.metadata.PackageNotFoundError:
            versions[distribution] = None
    return versions


def _thread_environment() -> dict[str, str | None]:
    return {name: os.environ.get(name) for name in THREAD_ENVIRONMENT}


def _pipeline(
    *,
    source_root: Path,
    config_path: Path,
    output_root: Path,
    scenario: str,
    expected_config_sha256: str,
    progress: dict[str, Any],
) -> dict[str, Any]:
    config_payload, raw_config_sha256 = _config_payload(config_path)
    if raw_config_sha256 != expected_config_sha256:
        raise ValueError("config JSON changed after the parent started the benchmark")
    canonical_config_sha256 = _canonical_sha256(config_payload)
    progress["config_sha256"] = canonical_config_sha256
    progress["config_file_sha256"] = raw_config_sha256
    progress["timings_seconds"] = {}
    import_started = time.perf_counter()
    import saxsabs
    from saxsabs.workflows import bl19b2_abs2d, bl19b2_integrate1d

    import_seconds = time.perf_counter() - import_started
    progress["imported_package_path"] = str(Path(saxsabs.__file__).resolve())
    progress["versions"] = _software_versions(saxsabs)
    progress["thread_environment"] = _thread_environment()
    progress["timings_seconds"]["target_package_import"] = import_seconds
    config = _build_config(
        config_payload,
        config_path=config_path,
        output_root=output_root,
        workflow=bl19b2_abs2d,
    )
    if scenario == "resume" and not output_root.is_dir():
        raise FileNotFoundError(f"resume output_root does not exist: {output_root}")
    if scenario == "resume" and not (output_root / "config" / "processing_config.yml").is_file():
        raise FileNotFoundError(
            "resume scenario requires the existing 2D processing configuration: "
            f"{output_root / 'config' / 'processing_config.yml'}"
        )

    stage_started = time.perf_counter()
    try:
        result_2d = bl19b2_abs2d.run_bl19b2_abs2d(config)
    finally:
        seconds_2d = time.perf_counter() - stage_started
        progress["timings_seconds"]["2d_api"] = seconds_2d
    progress["2d"] = result_2d
    if result_2d.get("status") != "complete":
        raise ValueError(f"2D workflow returned {result_2d.get('status')!r}, expected 'complete'")

    stage_started = time.perf_counter()
    try:
        validation_2d = _validate_2d_outputs(output_root, config, result_2d, bl19b2_abs2d)
    finally:
        seconds_2d_validation = time.perf_counter() - stage_started
        progress["timings_seconds"]["2d_output_validation"] = seconds_2d_validation
    progress["validation"] = {"2d": validation_2d}

    integration_config = bl19b2_integrate1d.Integrate1DConfig(
        package_root=output_root,
        resume=(scenario == "resume"),
    )
    stage_started = time.perf_counter()
    try:
        result_1d = bl19b2_integrate1d.run_bl19b2_integrate1d(integration_config)
    finally:
        seconds_1d = time.perf_counter() - stage_started
        progress["timings_seconds"]["1d_api"] = seconds_1d
    progress["1d"] = result_1d
    if result_1d.get("status") != "complete":
        raise ValueError(f"1D workflow returned {result_1d.get('status')!r}, expected 'complete'")

    stage_started = time.perf_counter()
    try:
        integration_validation = validate_integration_package(output_root, result_1d)
    finally:
        seconds_integration_validation = time.perf_counter() - stage_started
        progress["timings_seconds"]["integration_complete_validation"] = (
            seconds_integration_validation
        )
    progress["validation"]["integration"] = integration_validation
    return {
        "status": "complete",
        "config_sha256": canonical_config_sha256,
        "config_file_sha256": raw_config_sha256,
        "source_root": str(source_root),
        "imported_package_path": progress["imported_package_path"],
        "versions": progress["versions"],
        "source_git": progress["source_git"],
        "thread_environment": progress["thread_environment"],
        "2d": result_2d,
        "1d": result_1d,
        "validation": {
            "2d": validation_2d,
            "integration": integration_validation,
        },
        "timings_seconds": {
            "target_package_import": import_seconds,
            "2d_api": seconds_2d,
            "2d_output_validation": seconds_2d_validation,
            "1d_api": seconds_1d,
            "integration_complete_validation": seconds_integration_validation,
        },
    }


def _write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def _worker(args: argparse.Namespace) -> int:
    child_result_path = Path(args.child_result)
    record: dict[str, Any] = {
        "scenario": args.scenario,
        "status": "failed",
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "python": sys.version,
        "platform": platform.platform(),
        "thread_environment": _thread_environment(),
        "config_file_sha256": args.expected_config_sha256,
    }
    started = time.perf_counter()
    profiler: cProfile.Profile | None = cProfile.Profile() if args.profile_output else None
    try:
        record["source_git"] = _git_state(Path(args.source_root).resolve())
        def call() -> dict[str, Any]:
            return _pipeline(
                source_root=Path(args.source_root).resolve(strict=True),
                config_path=Path(args.config_json).resolve(strict=True),
                output_root=Path(args.output_root).resolve(),
                scenario=args.scenario,
                expected_config_sha256=args.expected_config_sha256,
                progress=record,
            )
        payload = profiler.runcall(call) if profiler is not None else call()
        if profiler is not None:
            profiler.dump_stats(args.profile_output)
        record.update(payload)
        record["status"] = "complete"
        if args.profile_output:
            record["profile_path"] = args.profile_output
    except Exception as exc:
        record.update(
            {
                "error": f"{type(exc).__name__}: {exc}",
                "traceback": traceback.format_exc(),
            }
        )
        if profiler is not None:
            try:
                profiler.dump_stats(args.profile_output)
                record["profile_path"] = args.profile_output
            except OSError:
                pass
    record["child_wall_seconds"] = time.perf_counter() - started
    try:
        _write_json(child_result_path, record)
    except OSError as exc:
        print(f"Could not write child evidence: {exc}", file=sys.stderr)
        return 1
    return 0 if record["status"] == "complete" else 1


class _ProcessSampler:
    def __init__(self, pid: int, interval: float = 0.05) -> None:
        import psutil

        self._psutil = psutil
        self._process = psutil.Process(pid)
        self._interval = interval
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._sample_loop, daemon=True)
        self._values: dict[str, Any] = {
            "sample_interval_seconds": interval,
            "scope": "direct child process only",
            "cpu_user_seconds": None,
            "cpu_system_seconds": None,
            "peak_rss_bytes": None,
            "peak_private_bytes": None,
            "io_read_count": None,
            "io_write_count": None,
            "io_read_bytes": None,
            "io_write_bytes": None,
            "io_counter_semantics": "logical process I/O counters; not physical disk I/O",
            "private_memory_source": "psutil memory_full_info().uss when available",
        }

    def start(self) -> None:
        self._sample()
        self._thread.start()

    def stop(self) -> dict[str, Any]:
        self._stop.set()
        self._thread.join()
        self._sample()
        return dict(self._values)

    def _sample(self) -> None:
        try:
            cpu = self._process.cpu_times()
            self._values["cpu_user_seconds"] = max(
                self._values["cpu_user_seconds"] or 0.0, cpu.user
            )
            self._values["cpu_system_seconds"] = max(
                self._values["cpu_system_seconds"] or 0.0, cpu.system
            )
            memory = self._process.memory_info()
            self._values["peak_rss_bytes"] = max(
                self._values["peak_rss_bytes"] or 0, memory.rss
            )
            try:
                full_memory = self._process.memory_full_info()
                private = getattr(full_memory, "uss", None)
                if private is not None:
                    self._values["peak_private_bytes"] = max(
                        self._values["peak_private_bytes"] or 0, private
                    )
            except (self._psutil.AccessDenied, self._psutil.NoSuchProcess, OSError):
                pass
            try:
                counters = self._process.io_counters()
                for name in ("read_count", "write_count", "read_bytes", "write_bytes"):
                    self._values[f"io_{name}"] = getattr(counters, name, None)
            except (AttributeError, self._psutil.AccessDenied, self._psutil.NoSuchProcess, OSError):
                pass
        except (self._psutil.AccessDenied, self._psutil.NoSuchProcess, OSError):
            return

    def _sample_loop(self) -> None:
        while not self._stop.wait(self._interval):
            self._sample()


def _run_parent(args: argparse.Namespace) -> int:
    source_root = Path(args.source_root).resolve(strict=True)
    config_path = Path(args.config_json).resolve(strict=True)
    requested_output_root = Path(args.output_root).absolute()
    if args.scenario == "fresh" and (
        requested_output_root.exists() or requested_output_root.is_symlink()
    ):
        raise FileExistsError(
            f"fresh scenario refuses an existing output-root: {requested_output_root}"
        )
    output_root = requested_output_root.resolve()
    evidence_dir = Path(args.evidence_dir).resolve()
    if not (source_root / "src").is_dir():
        raise ValueError(f"source-root must contain src/: {source_root}")
    if not (source_root / "src" / "saxsabs").is_dir():
        raise ValueError(f"source-root/src must contain saxsabs/: {source_root / 'src'}")
    if output_root == evidence_dir or output_root in evidence_dir.parents or evidence_dir in output_root.parents:
        raise ValueError("evidence-dir and output-root must not overlap")
    config_payload, _config_digest = _config_payload(config_path)
    input_value = config_payload.get("input_root")
    if not isinstance(input_value, str) or not input_value:
        raise ValueError("config JSON must include input_root as a path string")
    input_root = Path(input_value)
    if not input_root.is_absolute():
        input_root = config_path.parent / input_root
    input_root = input_root.resolve(strict=True)
    if not input_root.is_dir():
        raise NotADirectoryError(f"input_root is not a directory: {input_root}")
    if output_root == input_root or input_root in output_root.parents:
        raise ValueError("output_root must not be inside input_root")
    if evidence_dir == input_root or input_root in evidence_dir.parents:
        raise ValueError("evidence-dir must not be inside input_root")
    if args.scenario == "fresh":
        if output_root.exists() or output_root.is_symlink():
            raise FileExistsError(f"fresh scenario refuses an existing output-root: {output_root}")
    elif not output_root.is_dir():
        raise FileNotFoundError(f"resume scenario requires an existing output-root: {output_root}")

    raw_config = config_path.read_bytes()
    config_file_sha256 = hashlib.sha256(raw_config).hexdigest()
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ") + "_" + uuid.uuid4().hex[:8]
    prefix = evidence_dir / f"benchmark_bl19b2_{run_id}"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    child_json = Path(f"{prefix}.child.json")
    stdout_path = Path(f"{prefix}.stdout.log")
    stderr_path = Path(f"{prefix}.stderr.log")
    report_path = Path(f"{prefix}.json")
    profile_path = Path(f"{prefix}.prof") if args.profile else None

    command = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--_worker",
        "--source-root",
        str(source_root),
        "--config-json",
        str(config_path),
        "--output-root",
        str(output_root),
        "--evidence-dir",
        str(evidence_dir),
        "--scenario",
        args.scenario,
        "--child-result",
        str(child_json),
        "--expected-config-sha256",
        config_file_sha256,
    ]
    if profile_path is not None:
        command.extend(("--profile-output", str(profile_path)))
    child_env = os.environ.copy()
    child_env["PYTHONPATH"] = str(source_root / "src")
    inherited_thread_environment = _thread_environment()
    started_at = datetime.now(timezone.utc).isoformat()
    wall_started = time.perf_counter()
    sampler: _ProcessSampler | None = None
    with stdout_path.open("w", encoding="utf-8", errors="replace") as stdout, stderr_path.open(
        "w", encoding="utf-8", errors="replace"
    ) as stderr:
        process = subprocess.Popen(
            command,
            cwd=source_root,
            env=child_env,
            stdout=stdout,
            stderr=stderr,
        )
        try:
            sampler = _ProcessSampler(process.pid)
            sampler.start()
        except ImportError as exc:
            process.terminate()
            process.wait()
            raise RuntimeError("psutil is required for child resource sampling") from exc
        return_code = process.wait()
    parent_wall_seconds = time.perf_counter() - wall_started
    resource_usage = sampler.stop() if sampler else {}
    child_result: dict[str, Any] = {}
    if child_json.is_file():
        try:
            child_result = json.loads(child_json.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            child_result = {"status": "failed", "error": f"invalid child result JSON: {exc}"}
    status = "complete" if return_code == 0 and child_result.get("status") == "complete" else "failed"
    report = {
        "schema": "saxsabs.bl19b2_benchmark.v1",
        "status": status,
        "scenario": args.scenario,
        "started_at_utc": started_at,
        "source_root": str(source_root),
        "output_root": str(output_root),
        "config_json": str(config_path),
        "config_file_sha256": config_file_sha256,
        "profile_requested": bool(args.profile),
        "profile_comparability": (
            "diagnostic only; do not compare this profiled run with ordinary timing"
            if args.profile
            else "ordinary timing"
        ),
        "thread_environment_inherited": inherited_thread_environment,
        "python_executable": sys.executable,
        "child_command": command,
        "child_return_code": return_code,
        "parent_child_wall_seconds": parent_wall_seconds,
        "measurement_includes": [
            "child process startup and target package import",
            "BL19B2 2D API run and output validation",
            "BL19B2 1D API run including integration checksum generation",
            "complete integration checksum and completion-manifest verification",
        ],
        "resource_usage": resource_usage,
        "child_result": child_result,
        "thread_environment_matches_parent": (
            child_result.get("thread_environment") == inherited_thread_environment
        ),
        "stdout_log": str(stdout_path),
        "stderr_log": str(stderr_path),
        "profile_path": str(profile_path) if profile_path else None,
    }
    if not report["thread_environment_matches_parent"]:
        status = report["status"] = "failed"
    _write_json(report_path, report)
    print(json.dumps({"status": status, "report": str(report_path)}, ensure_ascii=False))
    return 0 if status == "complete" else 1


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", required=True, help="checkout root containing src/saxsabs")
    parser.add_argument(
        "--config-json",
        required=True,
        help="JSON object of BL19B2Abs2DConfig fields; relative paths use its directory",
    )
    parser.add_argument("--output-root", required=True, help="2D package root used by both workflow stages")
    parser.add_argument("--evidence-dir", required=True, help="directory for benchmark reports and logs")
    parser.add_argument("--scenario", choices=("fresh", "resume"), required=True)
    parser.add_argument("--profile", action="store_true", help="save cProfile diagnostics; timing is not comparable")
    parser.add_argument("--_worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--child-result", help=argparse.SUPPRESS)
    parser.add_argument("--expected-config-sha256", help=argparse.SUPPRESS)
    parser.add_argument("--profile-output", help=argparse.SUPPRESS)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args._worker:
        if not args.child_result or not args.expected_config_sha256:
            print("worker arguments are incomplete", file=sys.stderr)
            return 2
        return _worker(args)
    try:
        return _run_parent(args)
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"benchmark refused or failed before launch: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
