"""Verify the Tk workbench on an isolated Windows desktop without user input.

Run with ``py -3.13 scripts/check_workbench_ui.py``. Artifacts are synthetic
engineering evidence, not validation of experimental SAXS results.
"""

from __future__ import annotations

import argparse
import contextlib
import ctypes
from ctypes import wintypes
import hashlib
import json
import importlib.util
from pathlib import Path
import subprocess
import runpy
import sys
import time
import traceback
from types import SimpleNamespace
from unittest.mock import patch
import uuid

REPOSITORY = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = REPOSITORY / ".audit-work" / "ui"


def _windows_libraries():
    if sys.platform != "win32":
        raise RuntimeError("Isolated desktop verification requires Windows.")
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)
    user32.CreateDesktopW.argtypes = [
        wintypes.LPCWSTR, wintypes.LPCWSTR, ctypes.c_void_p,
        wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p,
    ]
    user32.CreateDesktopW.restype = wintypes.HANDLE
    user32.CloseDesktop.argtypes = [wintypes.HANDLE]
    user32.GetThreadDesktop.argtypes = [wintypes.DWORD]
    user32.GetThreadDesktop.restype = wintypes.HANDLE
    user32.GetUserObjectInformationW.argtypes = [
        wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
    ]
    user32.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
    user32.GetAncestor.restype = wintypes.HWND
    user32.GetClientRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    user32.PrintWindow.argtypes = [wintypes.HWND, wintypes.HDC, wintypes.UINT]
    gdi32.CreateCompatibleDC.argtypes = [wintypes.HDC]
    gdi32.CreateCompatibleDC.restype = wintypes.HDC
    gdi32.CreateDIBSection.argtypes = [
        wintypes.HDC, ctypes.c_void_p, wintypes.UINT,
        ctypes.POINTER(ctypes.c_void_p), wintypes.HANDLE, wintypes.DWORD,
    ]
    gdi32.CreateDIBSection.restype = wintypes.HBITMAP
    gdi32.SelectObject.argtypes = [wintypes.HDC, wintypes.HGDIOBJ]
    gdi32.SelectObject.restype = wintypes.HGDIOBJ
    gdi32.DeleteObject.argtypes = [wintypes.HGDIOBJ]
    gdi32.DeleteDC.argtypes = [wintypes.HDC]
    return user32, gdi32


def _desktop_name(user32):
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.GetCurrentThreadId.restype = wintypes.DWORD
    desktop = user32.GetThreadDesktop(kernel32.GetCurrentThreadId())
    name = ctypes.create_unicode_buffer(256)
    needed = wintypes.DWORD()
    if not user32.GetUserObjectInformationW(
        desktop, 2, name, ctypes.sizeof(name), ctypes.byref(needed)
    ):
        raise ctypes.WinError(ctypes.get_last_error())
    return name.value


def _capture_window(root, destination):
    """Print the application client window; never read the screen framebuffer."""
    from PIL import Image

    user32, gdi32 = _windows_libraries()
    hwnd = user32.GetAncestor(root.winfo_id(), 2)
    rect = wintypes.RECT()
    if not user32.GetClientRect(hwnd, ctypes.byref(rect)):
        raise ctypes.WinError(ctypes.get_last_error())
    width, height = rect.right, rect.bottom
    if width < 1 or height < 1:
        raise RuntimeError("Application window has no drawable client area.")

    class BitmapInfoHeader(ctypes.Structure):
        _fields_ = [
            ("size", wintypes.DWORD), ("width", wintypes.LONG),
            ("height", wintypes.LONG), ("planes", wintypes.WORD),
            ("bit_count", wintypes.WORD), ("compression", wintypes.DWORD),
            ("size_image", wintypes.DWORD), ("x_pixels", wintypes.LONG),
            ("y_pixels", wintypes.LONG), ("colors_used", wintypes.DWORD),
            ("colors_important", wintypes.DWORD),
        ]

    header = BitmapInfoHeader()
    header.size = ctypes.sizeof(header)
    header.width, header.height = width, -height
    header.planes, header.bit_count = 1, 32
    pixels = ctypes.c_void_p()
    dc = gdi32.CreateCompatibleDC(None)
    if not dc:
        raise ctypes.WinError(ctypes.get_last_error())
    bitmap = None
    previous = None
    try:
        bitmap = gdi32.CreateDIBSection(dc, ctypes.byref(header), 0, ctypes.byref(pixels), None, 0)
        if not bitmap or not pixels.value:
            raise ctypes.WinError(ctypes.get_last_error())
        previous = gdi32.SelectObject(dc, bitmap)
        if not user32.PrintWindow(hwnd, dc, 1):
            raise RuntimeError("PrintWindow could not render the isolated application window.")
        rendered = Image.frombytes(
            "RGB", (width, height), ctypes.string_at(pixels, width * height * 4),
            "raw", "BGRX",
        )
        if all(low == high for low, high in rendered.getextrema()):
            raise RuntimeError(
                f"PrintWindow returned a blank {width}x{height} image; "
                f"widget={root}, mapped={root.winfo_ismapped()}, geometry={root.winfo_geometry()}."
            )
        rendered.save(destination)
        return {"path": str(destination), "width": width, "height": height,
                "capture": "PrintWindow(application-client-only)"}
    finally:
        if previous:
            gdi32.SelectObject(dc, previous)
        if bitmap:
            gdi32.DeleteObject(bitmap)
        gdi32.DeleteDC(dc)


def _probe(output):
    import tkinter as tk

    root = tk.Tk()
    try:
        root.geometry("320x180+0+0")
        canvas = tk.Canvas(root, background="#ffffff")
        canvas.pack(fill="both", expand=True)
        canvas.create_rectangle(20, 20, 140, 140, fill="#1455bb")
        canvas.create_text(220, 70, text="Isolated Tk")
        root.update()
        return _capture_window(root, output / "probe.png")
    finally:
        root.destroy()


def _write_report(output, report):
    (output / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _load_app(source):
    sys.path.insert(0, str(REPOSITORY / "src"))
    sys.path.insert(0, str(REPOSITORY))
    spec = importlib.util.spec_from_file_location("workbench_ui_check", source)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _settle(root):
    # Process delayed responsive layout callbacks as well as idle Tk drawing.
    deadline = time.monotonic() + 0.12
    while time.monotonic() < deadline:
        root.update()
        time.sleep(0.01)


def _widget_rectangle(widget):
    x, y = widget.winfo_rootx(), widget.winfo_rooty()
    return x, y, x + widget.winfo_width(), y + widget.winfo_height()


def _rectangle_contains(outer, inner, tolerance=2):
    return (
        inner[0] >= outer[0] - tolerance and inner[1] >= outer[1] - tolerance
        and inner[2] <= outer[2] + tolerance and inner[3] <= outer[3] + tolerance
    )


def _require_visible(widget):
    assert widget.winfo_ismapped(), f"Unmapped control: {widget}"
    assert widget.winfo_width() > 1 and widget.winfo_height() > 1, str(widget)
    rectangle = _widget_rectangle(widget)
    parent = widget.master
    while parent is not None:
        assert _rectangle_contains(_widget_rectangle(parent), rectangle), (
            f"Clipped control {widget}: {rectangle}; ancestor {parent}: "
            f"{_widget_rectangle(parent)}"
        )
        parent = parent.master


def _i18n_widget(app, key):
    matches = [widget for widget, label in app._i18n_widgets if label == key]
    assert matches, f"Missing {key} control"
    # A fixed action dock and the queue may expose the same Preflight action.
    # The dock is constructed first and remains visible when settings scroll.
    return matches[0]


def _is_descendant(widget, ancestor):
    while widget is not None:
        if widget is ancestor:
            return True
        widget = widget.master
    return False


def _page_canvases(app, page):
    return [canvas for canvas in app._scroll_canvases if _is_descendant(canvas, page)]


def _check(report, name, action):
    try:
        action()
    except Exception:
        report["checks"].append({"name": name, "passed": False,
                                 "error": traceback.format_exc()})
    else:
        report["checks"].append({"name": name, "passed": True})


def _check_page_layout(app, page_name):
    _require_visible(app.btn_lang)
    _require_visible(app.btn_theme)
    _require_visible(app._status_bar)
    if page_name in {"tab2", "tab3"}:
        prefix = "t2" if page_name == "tab2" else "t3"
        # These actions must remain available without scrolling settings.
        for key in (f"{prefix}_check_btn", f"{prefix}_run_btn"):
            _require_visible(_i18n_widget(app, key))
        for child in getattr(app, f"{prefix}_run_button").master.winfo_children():
            _require_visible(child)
        _require_visible(app._workflow_status_labels[prefix])
        for key in (f"{prefix}_add_btn", f"{prefix}_clear_btn"):
            control = _i18n_widget(app, key)
            canvas = next(canvas for canvas in app._scroll_canvases
                          if _is_descendant(control, canvas))
            region = canvas.bbox("all")
            top = canvas.canvasy(0) + control.winfo_rooty() - canvas.winfo_rooty()
            canvas.yview_moveto(max(0, (top - canvas.winfo_height() / 2) / region[3]))
            app.root.update()
            _require_visible(control)
            canvas.yview_moveto(0)
            app.root.update()
    elif page_name == "tab1":
        exports = [widget for widget, key in app._i18n_widgets
                   if key == "plot_export_btn" and _is_descendant(widget, app.tab1)]
        assert exports, "Tab 1 figure export control is missing."
        for export in exports:
            for child in export.master.winfo_children():
                _require_visible(child)


def _check_wheel_scope(app, root):
    pages = (app.tab1, app.tab2, app.tab3)
    canvases = {page: _page_canvases(app, page) for page in pages}
    for page in pages:
        app.nb.select(page)
        _settle(root)
        active = canvases[page]
        assert active, f"No scrollable settings on {page}"
        for canvas in active:
            canvas.yview_moveto(0)
        root.update()
        previous = {canvas: canvas.yview() for group in canvases.values() for canvas in group}
        # Generate events on actual widgets; no OS pointer/keyboard injection.
        active[0].event_generate("<Enter>")
        active[0].event_generate("<MouseWheel>", delta=-120, x=5, y=5)
        root.update()
        if previous[active[0]][1] < 1:
            assert active[0].yview() != previous[active[0]], "Active settings did not scroll."
        for other_page, group in canvases.items():
            if other_page is not page:
                for canvas in group:
                    assert canvas.yview() == previous[canvas], "Hidden page scrolled."
        # Switching tabs without Leave must not retain a global wheel target.
        app.nb.select(app.tab_help)
        _settle(root)
        previous = {canvas: canvas.yview() for group in canvases.values() for canvas in group}
        app.tab_help.event_generate("<MouseWheel>", delta=-120, x=5, y=5)
        root.update()
        for canvas, position in previous.items():
            assert canvas.yview() == position, "Help-page wheel scrolled another page."


def _check_popdown_wheel(app, root):
    app.nb.select(app.tab1)
    _settle(root)
    combo = app.t1_std_combo
    original = combo.get()
    combo.tk.call("ttk::combobox::Post", str(combo))
    try:
        _settle(root)
        popup = combo.tk.call("ttk::combobox::PopdownWindow", str(combo))
        listbox = f"{popup}.f.l"
        positions = {canvas: canvas.yview() for canvas in app._scroll_canvases}
        # This private Tcl listbox has no Tkinter widget object. Tk callbacks
        # receive its path as a string and must preserve native wheel behavior.
        combo.tk.call("event", "generate", listbox, "<MouseWheel>", "-delta", -120)
        _settle(root)
        for canvas, position in positions.items():
            assert canvas.yview() == position, "Combobox popdown wheel scrolled form."
    finally:
        combo.tk.call("ttk::combobox::Unpost", str(combo))
        root.update()
    assert combo.get() == original, "Hover/wheel test changed the standard selection."


def _check_preflight_interactions(app, root):
    import sv_ttk

    messages = []
    # Route modal diagnostics to the report so a blocked fixture cannot hang.
    for method in ("show_info", "show_warning", "show_error"):
        setattr(app, method, lambda *args, **kwargs: messages.append((args, kwargs)))
    for tab, page in (("t2", app.tab2), ("t3", app.tab3)):
        app.nb.select(page)
        _settle(root)
        button = getattr(app, f"{tab}_run_button")
        assert str(button.cget("state")) == "disabled", f"Initial {tab} Run enabled."
        _i18n_widget(app, f"{tab}_check_btn").invoke()
        assert str(button.cget("state")) == "disabled", f"Empty {tab} check enabled Run."
        app._record_workbench_preflight(tab, SimpleNamespace(level="BLOCKED"))
        assert str(button.cget("state")) == "disabled", f"BLOCKED {tab} enabled Run."
        before = len(messages)
        button.invoke()
        assert len(messages) == before, "Disabled Run command executed."
        try:
            app._require_current_workbench_preflight(tab)
        except RuntimeError:
            pass
        else:
            raise AssertionError(f"Blocked {tab} gate accepted Run.")

    # Synthetic approvals test display state only: no scientific READY claim.
    approvals = {tab: app._record_workbench_preflight(tab, SimpleNamespace(level="READY"))
                 for tab in ("t2", "t3")}
    for tab in approvals:
        assert str(getattr(app, f"{tab}_run_button").cget("state")) == "normal"
    configurations = {tab: getattr(app, f"_{tab}_preflight_config")()
                      for tab in approvals}
    for _ in range(2):
        previous_language = app.language
        previous_theme = sv_ttk.get_theme()
        app.btn_lang.invoke()
        app.btn_theme.invoke()
        _settle(root)
        assert app.language != previous_language, "Language button did not change language."
        assert sv_ttk.get_theme() != previous_theme, "Theme button did not change theme."
        for tab, approval in approvals.items():
            assert getattr(app, f"{tab}_preflight_approval") is approval
            assert getattr(app, f"_{tab}_preflight_config")() == configurations[tab]
            assert str(getattr(app, f"{tab}_run_button").cget("state")) == "normal"
    for tab in approvals:
        variable = getattr(app, f"{tab}_fixed_thk")
        previous = variable.get()
        variable.set(float(previous) + 0.1)
        assert getattr(app, f"{tab}_preflight_approval") is None
        assert str(getattr(app, f"{tab}_run_button").cget("state")) == "disabled"
        variable.set(previous)
    return len(messages)


def _check_report_interactions(app, root, capture=None):
    app.nb.select(app.tab2)
    _settle(root)
    report_buttons = [widget for widget in app.t2_run_button.master.winfo_children()
                      if widget.winfo_class() == "TButton"
                      and str(widget.cget("text")) == app.tr("view_report")]
    assert len(report_buttons) == 1
    report_buttons[0].invoke()
    _settle(root)
    assert app.nb.select() == str(app.tab1)
    assert app.result_nb.select() == str(app.report_panel)
    text = app.txt_report
    _require_visible(text)
    assert str(text.cget("state")) == "disabled", "Activity report is editable."
    original = text.get("1.0", "end-1c")
    if not original.strip():
        app.result_nb.select(app.plot_panel)
        return {"read_only": True, "copy_checked": False, "reason": "empty initial report"}
    text.insert("1.0", "unexpected edit")
    text.delete("1.0", "1.1")
    assert text.get("1.0", "end-1c") == original, "Read-only report accepted edits."
    text.tag_add("sel", "1.0", "end-1c")
    assert text.get("sel.first", "sel.last") == original
    # Execute the real Tk Copy binding, replacing only its clipboard destination.
    # The Windows clipboard is shared across desktops and belongs to the user.
    saved_command = "_ui_saved_clipboard_" + uuid.uuid4().hex
    root.tk.call("rename", "clipboard", saved_command)
    try:
        root.tk.call("set", "::saxs_ui_copied_text", "")
        root.tk.call("proc", "clipboard", "args", (
            'if {[lindex $args 0] eq "append"} '
            '{set ::saxs_ui_copied_text [lindex $args end]}; return ""'
        ))
        text.event_generate("<<Copy>>")
        root.update()
        assert root.tk.getvar("::saxs_ui_copied_text") == original, "Copy binding lost report text."
    finally:
        root.tk.call("rename", "clipboard", "")
        root.tk.call("rename", saved_command, "clipboard")
        root.tk.call("unset", "::saxs_ui_copied_text")
        text.tag_remove("sel", "1.0", "end")
    if capture is not None:
        root.update()
        capture()
    app.result_nb.select(app.plot_panel)
    return {"read_only": True, "copy_checked": True, "copy_characters": len(original),
            "clipboard_scope": "in-process Tcl sink; user clipboard unchanged"}


def _check_synthetic_run(app, module, root, output, report):
    """Use real calibration loading, Dry Check, Run, and profile parsing."""
    import numpy as np

    workdir = output / ("synthetic-" + uuid.uuid4().hex)
    workdir.mkdir(parents=True)
    # Reuse the source-verified engineering fixture already used by science tests.
    fixture = runpy.run_path(str(REPOSITORY / "tests" / "test_workbench_scientific.py"))
    _, sources = fixture["_make_complete_custom_record"](module, workdir)
    with patch.object(module.filedialog, "askopenfilename", return_value=str(sources["record"])):
        app.btn_calibration_load.invoke()
    assert app.calibration_context is not None, "Calibration-load action failed."
    fingerprint = app.calibration_context.fingerprint()
    sample = workdir / "sample.dat"
    sample.write_text(
        f"# calibration_context_fingerprint: {fingerprint}\n"
        "# intensity_state: relative\n# intensity_unit: relative\n"
        '# corrections_applied: ["thickness"]\n# do_not_repeat: ["thickness"]\n'
        "# thickness_cm: 0.1\n# thickness_source: synthetic upstream cell record\n"
        "# q_A^-1 I_rel Error\n0.01 10 0.1\n0.02 9 0.1\n0.03 8 0.1\n",
        encoding="utf-8",
    )
    app.nb.select(app.tab3)
    app.t3_pipeline_mode.set("scaled")
    app.t3_corr_mode.set("k_only")
    app.t3_buffer_enabled.set(False)
    app.t3_fluo_enabled.set(False)
    app.t3_resume_enabled.set(False)
    app.t3_output_root.set(str(workdir / "output"))
    with patch.object(module.filedialog, "askopenfilenames", return_value=(str(sample),)):
        _i18n_widget(app, "t3_add_btn").invoke()
    assert app.t3_files == [str(sample)] and app.lb_ext1d.size() == 1
    _settle(root)
    report["screenshots"].append(_capture_window(root, output / "synthetic-loaded.png"))
    _i18n_widget(app, "t3_check_btn").invoke()
    level = app.t3_preflight_level
    assert level in {"READY", "CAUTION"}, f"Synthetic preflight was {level}."
    assert str(app.t3_run_button.cget("state")) == "normal"
    # Exercise the real gate a second time immediately before the button callback.
    assert app._require_current_workbench_preflight("t3") is app.t3_preflight_approval
    _settle(root)
    report["screenshots"].append(_capture_window(root, output / "synthetic-preflight.png"))
    app.t3_run_button.invoke()
    _settle(root)
    assert app.t3_job_status == "completed", f"Run state: {app.t3_job_status}"
    result_path = workdir / "output" / "processed_external_1d_abs" / "sample.dat"
    assert result_path.is_file(), f"Run did not produce {result_path}."
    result = app.read_external_1d_profile(result_path)
    provenance = result["operator_provenance"]
    assert provenance["intensity_state"] == "absolute_cm^-1"
    assert provenance["intensity_unit"] == "1/cm"
    assert provenance["calibration_context_fingerprint"] == fingerprint
    assert fingerprint == app.calibration_context.fingerprint()
    np.testing.assert_allclose(result["i_abs"], [25.0, 22.5, 20.0], rtol=1e-12)
    np.testing.assert_allclose(result["err_abs"], [0.25, 0.25, 0.25], rtol=1e-12)
    corrections = json.loads(provenance["corrections_applied"])
    assert set(corrections) == {"k", "thickness"}
    assert json.loads(provenance["do_not_repeat"]) == corrections
    report["synthetic_run"] = {
        "preflight_level": level, "output": str(result_path),
        "intensity_state": provenance["intensity_state"],
        "intensity_unit": provenance["intensity_unit"],
        "intensity": result["i_abs"].tolist(), "error": result["err_abs"].tolist(),
        "calibration_context_fingerprint": fingerprint, "corrections_applied": corrections,
        "validation_type": "synthetic_engineering_workflow",
    }
    report["screenshots"].append(_capture_window(root, output / "synthetic-completed.png"))


def _verify_app(args, report):
    import tkinter as tk
    import sv_ttk

    source_hash = hashlib.sha256(args.source.read_bytes()).hexdigest()
    report["source"] = str(args.source.resolve())
    report["source_sha256"] = source_hash
    report["python"] = sys.version
    module = _load_app(args.source)
    root = tk.Tk()
    callbacks = []
    root.report_callback_exception = lambda *exc: callbacks.append(
        "".join(traceback.format_exception(*exc))
    )
    try:
        app = module.SAXSAbsWorkbenchApp(root, language="en")
        report["screenshots"] = []
        report["checks"] = []
        if not args.baseline_only and not args.context_help_only:
            _check(report, "wheel_stays_on_selected_page", lambda: _check_wheel_scope(app, root))
            _check(report, "native_combobox_popdown_wheel", lambda: _check_popdown_wheel(app, root))
            _check(report, "preflight_and_display_interactions",
                   lambda: _check_preflight_interactions(app, root))
        if args.context_help:
            help_exercise = runpy.run_path(str(REPOSITORY / "tests" / "test_gui_help.py"))
            focus_trace = []

            def record_focus(event):
                focus_trace.append({"event": str(event.type), "widget": str(event.widget),
                                    "focus": str(root.tk.call("focus"))})
                del focus_trace[:-40]

            root.bind_all("<FocusIn>", record_focus, add="+")
            root.bind_all("<FocusOut>", record_focus, add="+")

            def capture_help(window, name):
                _settle(root)
                report["screenshots"].append(_capture_window(root, args.output / f"{name}-app.png"))
                report["screenshots"].append(_capture_window(window, args.output / f"{name}.png"))

            def exercise_help():
                before = app.t1_std_combo.get()
                try:
                    report["context_help"] = help_exercise["exercise_context_help"](app, capture_help)
                except Exception:
                    report["context_help_error_state"] = {
                        "standard_before": before, "standard_after": app.t1_std_combo.get(),
                        "active_tooltip": str(getattr(root, "_saxs_active_tooltip", None)),
                        "focus_trace": focus_trace,
                    }
                    raise
                report["context_help"]["focus_scope"] = "assigned isolated desktop only"

            _check(report, "hover_focus_keyboard_dropdown_and_calculator_help", exercise_help)
        sizes = () if args.context_help_only else (
            ("1280x800",) if args.baseline_only else args.sizes
        )
        languages = ("en",) if args.baseline_only else args.languages
        themes = ("light",) if args.baseline_only else args.themes
        pages = ("tab1", "tab2", "tab3") if args.baseline_only else (
            *args.pages,
        )
        for size in sizes:
            root.geometry(size + "+0+0")
            for language in languages:
                if app.language != language:
                    app.btn_lang.invoke()
                for theme in themes:
                    if sv_ttk.get_theme() != theme:
                        app.btn_theme.invoke()
                    for name in pages:
                        app.nb.select(getattr(app, name))
                        if name == "tab1" and hasattr(app, "result_nb"):
                            app.result_nb.select(app.plot_panel)
                        for canvas in _page_canvases(app, getattr(app, name)):
                            canvas.yview_moveto(0)
                        _settle(root)
                        key = f"{size}-{language}-{theme}-{name}"
                        if not args.baseline_only:
                            _check(report, key + "-layout", lambda: _check_page_layout(app, name))
                        assert (root.winfo_width(), root.winfo_height()) == tuple(
                            int(part) for part in size.split("x")
                        ), "Window did not adopt requested client dimensions."
                        if not args.checks_only:
                            report["screenshots"].append(_capture_window(
                                root, args.output / f"{key}.png"
                            ))
        if args.synthetic_run:
            _check(report, "source_verified_synthetic_tab3_run",
                   lambda: _check_synthetic_run(app, module, root, args.output, report))
        if not args.baseline_only and not args.context_help_only:
            def check_report():
                capture_report = None if args.checks_only else lambda: report["screenshots"].append(
                    _capture_window(root, args.output / "activity-report.png")
                )
                report["report_interaction"] = _check_report_interactions(app, root, capture_report)
                if args.synthetic_run:
                    assert report["report_interaction"]["copy_checked"]
            _check(report, "read_only_selectable_report_and_view_button", check_report)
        if callbacks:
            raise RuntimeError("Tk callback errors:\n" + "\n".join(callbacks))
        assert hashlib.sha256(args.source.read_bytes()).hexdigest() == source_hash, (
            "Workbench source changed during UI verification; rerun on stable contents."
        )
        failures = [check["name"] for check in report["checks"] if not check["passed"]]
        if failures:
            raise AssertionError("UI checks failed: " + ", ".join(failures))
    finally:
        root.destroy()


def _run_worker(args):
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    report = {"validation_type": "synthetic_ui_engineering", "passed": False}
    try:
        user32, _ = _windows_libraries()
        actual = _desktop_name(user32)
        if not args.desktop or actual != args.desktop:
            raise RuntimeError(f"Worker desktop {actual!r} is not the assigned isolated desktop.")
        report["desktop"] = actual
        report["interaction_scope"] = {
            "focus": "assigned isolated desktop only",
            "capture": "application/popup client windows only",
            "desktop_switch": False,
        }
        if args.probe:
            report["probe"] = _probe(output)
        else:
            _verify_app(args, report)
        report["passed"] = True
    except Exception:
        report["error"] = traceback.format_exc()
    _write_report(output, report)
    return 0 if report["passed"] else 1


def _run_isolated(args):
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    _write_report(output, {"passed": False, "status": "worker_starting"})
    user32, _ = _windows_libraries()
    desktop_name = "AbsSAXS_UI_" + uuid.uuid4().hex
    desktop = user32.CreateDesktopW(desktop_name, None, None, 0, 0x01FF, None)
    if not desktop:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        command = [sys.executable, str(Path(__file__).resolve()), "--worker",
                   "--desktop", desktop_name, "--output", str(output),
                   "--source", str(args.source.resolve())]
        if args.probe:
            command.append("--probe")
        if args.baseline_only:
            command.append("--baseline-only")
        if args.checks_only:
            command.append("--checks-only")
        if args.synthetic_run:
            command.append("--synthetic-run")
        if args.context_help:
            command.append("--context-help")
        if args.context_help_only:
            command.append("--context-help-only")
        for flag, values in (("--sizes", args.sizes), ("--languages", args.languages),
                             ("--themes", args.themes), ("--pages", args.pages)):
            command.extend([flag, *values])
        code = _create_isolated_process(command, desktop_name)
        print(f"UI verification exit={code}; report: {output / 'report.json'}")
        return code
    finally:
        user32.CloseDesktop(desktop)


def _create_isolated_process(command, desktop_name):
    # CPython's subprocess.STARTUPINFO exposes only a subset of STARTUPINFOW;
    # assigning lpDesktop to that object does not pass it to CreateProcessW.
    class StartupInfo(ctypes.Structure):
        _fields_ = [
            ("cb", wintypes.DWORD), ("reserved", wintypes.LPWSTR),
            ("desktop", wintypes.LPWSTR), ("title", wintypes.LPWSTR),
            ("x", wintypes.DWORD), ("y", wintypes.DWORD),
            ("x_size", wintypes.DWORD), ("y_size", wintypes.DWORD),
            ("x_count", wintypes.DWORD), ("y_count", wintypes.DWORD),
            ("fill", wintypes.DWORD), ("flags", wintypes.DWORD),
            ("show", wintypes.WORD), ("reserved_size", wintypes.WORD),
            ("reserved_bytes", ctypes.c_void_p), ("stdin", wintypes.HANDLE),
            ("stdout", wintypes.HANDLE), ("stderr", wintypes.HANDLE),
        ]

    class ProcessInformation(ctypes.Structure):
        _fields_ = [
            ("process", wintypes.HANDLE), ("thread", wintypes.HANDLE),
            ("process_id", wintypes.DWORD), ("thread_id", wintypes.DWORD),
        ]

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateProcessW.argtypes = [
        wintypes.LPCWSTR, wintypes.LPWSTR, ctypes.c_void_p, ctypes.c_void_p,
        wintypes.BOOL, wintypes.DWORD, ctypes.c_void_p, wintypes.LPCWSTR,
        ctypes.POINTER(StartupInfo), ctypes.POINTER(ProcessInformation),
    ]
    kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel32.WaitForSingleObject.restype = wintypes.DWORD
    kernel32.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
    kernel32.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    startup = StartupInfo()
    startup.cb = ctypes.sizeof(startup)
    startup.desktop = "winsta0\\" + desktop_name
    process = ProcessInformation()
    cmdline = ctypes.create_unicode_buffer(subprocess.list2cmdline(command))
    if not kernel32.CreateProcessW(
        None, cmdline, None, None, False, subprocess.CREATE_NO_WINDOW,
        None, str(REPOSITORY), ctypes.byref(startup), ctypes.byref(process),
    ):
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        wait = kernel32.WaitForSingleObject(process.process, 240_000)
        if wait != 0:
            kernel32.TerminateProcess(process.process, 1)
            kernel32.WaitForSingleObject(process.process, 5000)
            raise RuntimeError(f"Isolated UI worker failed to finish (wait={wait}).")
        code = wintypes.DWORD()
        if not kernel32.GetExitCodeProcess(process.process, ctypes.byref(code)):
            raise ctypes.WinError(ctypes.get_last_error())
        return code.value
    finally:
        kernel32.CloseHandle(process.thread)
        kernel32.CloseHandle(process.process)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--source", type=Path, default=REPOSITORY / "SASAbs.py")
    parser.add_argument("--baseline-only", action="store_true",
                        help="Capture the three 1280x800 English/light baseline pages")
    parser.add_argument("--checks-only", action="store_true", help="Skip matrix/report PNG capture")
    parser.add_argument("--synthetic-run", action="store_true",
                        help="Verify a source-verified synthetic Tab 3 load/check/run/output workflow")
    parser.add_argument("--context-help", action="store_true",
                        help="Exercise hover, focus, F1/Escape, dropdown, and calculator help")
    parser.add_argument("--context-help-only", action="store_true",
                        help="Repeat only context help checks and their popup screenshots")
    parser.add_argument("--sizes", nargs="+", choices=("900x600", "1280x800"),
                        default=("900x600", "1280x800"))
    parser.add_argument("--languages", nargs="+", choices=("en", "zh"), default=("en", "zh"))
    parser.add_argument("--themes", nargs="+", choices=("light", "dark"), default=("light", "dark"))
    parser.add_argument("--pages", nargs="+", choices=("tab1", "tab2", "tab3", "tab_help"),
                        default=("tab1", "tab2", "tab3", "tab_help"))
    parser.add_argument("--probe", action="store_true", help="Only test desktop isolation and capture")
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--desktop", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.context_help_only:
        args.context_help = True
    try:
        if args.worker:
            args.output.mkdir(parents=True, exist_ok=True)
            with (args.output / "worker.log").open("w", encoding="utf-8") as log:
                with contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
                    return _run_worker(args)
        return _run_isolated(args)
    except Exception:
        args.output.mkdir(parents=True, exist_ok=True)
        _write_report(args.output, {"passed": False, "error": traceback.format_exc()})
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
