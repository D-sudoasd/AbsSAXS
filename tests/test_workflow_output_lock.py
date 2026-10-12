import os
from pathlib import Path
import subprocess
import sys
import time

import pytest

from saxsabs.workflows._output_lock import output_lock


_ATTEMPT_LOCK = """
from pathlib import Path
import sys
from saxsabs.workflows._output_lock import output_lock

try:
    with output_lock(Path(sys.argv[1])):
        print("ACQUIRED", flush=True)
except FileExistsError:
    print("LOCKED", flush=True)
    raise SystemExit(7)
"""

_HOLD_LOCK = """
from pathlib import Path
import sys
from saxsabs.workflows._output_lock import output_lock

with output_lock(Path(sys.argv[1])):
    Path(sys.argv[2]).write_text("ready", encoding="utf-8")
    sys.stdin.read()
"""


def _subprocess_env() -> dict[str, str]:
    env = os.environ.copy()
    src = str(Path(__file__).resolve().parents[1] / "src")
    current = env.get("PYTHONPATH")
    env["PYTHONPATH"] = src if not current else os.pathsep.join((src, current))
    return env


def _attempt_lock(root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-c", _ATTEMPT_LOCK, str(root)],
        capture_output=True,
        check=False,
        cwd=Path(__file__).resolve().parents[1],
        env=_subprocess_env(),
        text=True,
        timeout=10,
    )


def _wait_for_ready(process: subprocess.Popen[str], ready_file: Path) -> None:
    deadline = time.monotonic() + 10
    while not ready_file.exists():
        if process.poll() is not None:
            stdout, stderr = process.communicate(timeout=5)
            pytest.fail(f"lock holder exited early ({process.returncode}): {stdout}\n{stderr}")
        if time.monotonic() >= deadline:
            process.kill()
            process.wait(timeout=5)
            pytest.fail("lock holder did not acquire its output lock")
        time.sleep(0.01)


def test_output_lock_refuses_other_process_and_releases_after_context(tmp_path):
    lock_file = tmp_path / ".saxsabs.lock"

    with output_lock(tmp_path):
        assert lock_file.exists()
        assert lock_file.stat().st_size >= 1
        blocked = _attempt_lock(tmp_path)
        assert blocked.returncode == 7
        assert blocked.stdout.strip() == "LOCKED"

    acquired = _attempt_lock(tmp_path)
    assert acquired.returncode == 0
    assert acquired.stdout.strip() == "ACQUIRED"
    assert lock_file.exists()


def test_nested_same_process_lock_does_not_release_outer_lock(tmp_path):
    with output_lock(tmp_path):
        with pytest.raises(FileExistsError, match="already locked in this process"):
            with output_lock(tmp_path):
                pytest.fail("nested output lock unexpectedly acquired")

        blocked = _attempt_lock(tmp_path)
        assert blocked.returncode == 7
        assert blocked.stdout.strip() == "LOCKED"

    acquired = _attempt_lock(tmp_path)
    assert acquired.returncode == 0
    assert acquired.stdout.strip() == "ACQUIRED"


def test_killed_process_releases_lock_and_persistent_file_is_reusable(tmp_path):
    ready_file = tmp_path / "holder-ready"
    process = subprocess.Popen(
        [sys.executable, "-c", _HOLD_LOCK, str(tmp_path), str(ready_file)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=Path(__file__).resolve().parents[1],
        env=_subprocess_env(),
        text=True,
    )

    try:
        _wait_for_ready(process, ready_file)
        lock_file = tmp_path / ".saxsabs.lock"
        assert lock_file.exists()
        assert lock_file.stat().st_size >= 1

        process.kill()
        process.wait(timeout=5)

        with output_lock(tmp_path):
            assert lock_file.exists()
            assert lock_file.stat().st_size >= 1
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)
        for stream in (process.stdin, process.stdout, process.stderr):
            if stream is not None:
                stream.close()

    reusable = _attempt_lock(tmp_path)
    assert reusable.returncode == 0
    assert reusable.stdout.strip() == "ACQUIRED"
