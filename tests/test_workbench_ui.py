"""Safety and assertion regressions for the isolated-desktop UI harness."""

import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest


@pytest.fixture
def harness():
    source = Path(__file__).resolve().parents[1] / "scripts" / "check_workbench_ui.py"
    spec = importlib.util.spec_from_file_location("workbench_ui_harness_test", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    ("outer", "inner", "expected"),
    [
        ((0, 0, 900, 600), (10, 20, 880, 590), True),
        ((0, 0, 900, 600), (10, 20, 910, 590), False),
        ((0, 0, 900, 600), (10, -5, 880, 590), False),
        ((0, 0, 900, 600), (10, 20, 880, 610), False),
    ],
)
def test_control_bounds_detect_clipped_buttons(harness, outer, inner, expected):
    assert harness._rectangle_contains(outer, inner) is expected


def test_worker_refuses_default_desktop_before_creating_any_window(harness, tmp_path, monkeypatch):
    monkeypatch.setattr(harness, "_windows_libraries", lambda: (object(), object()))
    monkeypatch.setattr(harness, "_desktop_name", lambda _: "Default")
    created = []
    monkeypatch.setattr(harness, "_probe", lambda _: created.append("Tk"))
    monkeypatch.setattr(harness, "_verify_app", lambda *_: created.append("app"))
    args = SimpleNamespace(output=tmp_path, desktop="AbsSAXS_UI_test", probe=True)

    assert harness._run_worker(args) == 1
    assert created == []
    report = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))
    assert report["passed"] is False
    assert "not the assigned isolated desktop" in report["error"]


def test_failed_layout_assertion_is_preserved_in_report(harness):
    report = {"checks": []}

    def clipped_button():
        raise AssertionError("Clipped Run button")

    harness._check(report, "900x600-actions", clipped_button)
    harness._check(report, "unrelated-check", lambda: None)

    assert report["checks"][0]["passed"] is False
    assert "Clipped Run button" in report["checks"][0]["error"]
    assert report["checks"][1]["passed"] is True


@pytest.mark.skipif(sys.platform != "win32", reason="Win32 process structures")
@pytest.mark.parametrize("timeout", [False, True])
def test_native_process_receives_desktop_and_closes_handles(harness, monkeypatch, timeout):
    calls = []

    class Function:
        def __init__(self, callback):
            self.callback = callback

        def __call__(self, *args):
            return self.callback(*args)

    def create(*args):
        calls.append(("desktop", args[8]._obj.desktop))
        args[9]._obj.process = 42
        args[9]._obj.thread = 43
        return True

    waits = iter([258, 0] if timeout else [0])

    def exit_code(_handle, pointer):
        pointer._obj.value = 9
        return True

    library = SimpleNamespace(
        CreateProcessW=Function(create),
        WaitForSingleObject=Function(lambda *_: next(waits)),
        GetExitCodeProcess=Function(exit_code),
        TerminateProcess=Function(lambda handle, code: calls.append(("terminate", handle, code))),
        CloseHandle=Function(lambda handle: calls.append(("close", handle))),
    )
    monkeypatch.setattr(harness.ctypes, "WinDLL", lambda *_args, **_kwargs: library)

    if timeout:
        with pytest.raises(RuntimeError, match="failed to finish"):
            harness._create_isolated_process([sys.executable, "worker.py"], "AbsSAXS_UI_test")
        assert ("terminate", 42, 1) in calls
    else:
        assert harness._create_isolated_process(
            [sys.executable, "worker.py"], "AbsSAXS_UI_test"
        ) == 9
    assert ("desktop", "winsta0\\AbsSAXS_UI_test") in calls
    assert calls[-2:] == [("close", 43), ("close", 42)]
