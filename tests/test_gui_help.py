"""Help acceptance: wording coverage, geometry, keyboard and menu behavior."""

import ast
from pathlib import Path
import time
from types import SimpleNamespace

import pytest

from saxs_gui_help import (
    ATTRIBUTE_HELP,
    CONTROL_HELP,
    TOOLBAR_HELP,
    VARIABLE_HELP,
    ContextToolTip,
    apply_help_text,
    option_help,
    place_help,
)
from saxsabs.workbench_help_text import HELP_TEXT, OPTION_HELP


def test_bilingual_copy_covers_existing_and_registered_help():
    source = Path(__file__).resolve().parents[1] / "SASAbs.py"
    tree = ast.parse(source.read_text(encoding="utf-8-sig"))
    used = {
        node.value for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
        and ((node.value.startswith(("tip_", "hint_")) and len(node.value) > 5)
             or node.value == "help_copy_tooltip")
    }
    used.update(VARIABLE_HELP.values())
    used.update(CONTROL_HELP.values())
    used.update(ATTRIBUTE_HELP.values())
    used.update(TOOLBAR_HELP.values())
    assert set(HELP_TEXT["en"]) == set(HELP_TEXT["zh"])
    assert set(OPTION_HELP["en"]) == set(OPTION_HELP["zh"])
    for language in ("en", "zh"):
        assert used <= HELP_TEXT[language].keys(), used - HELP_TEXT[language].keys()
        assert all(text.strip() for text in HELP_TEXT[language].values())


def test_help_copy_update_preserves_unrelated_labels():
    packs = {"en": {"app_title": "Workbench", "tip_t1_std_t": "T"}, "zh": {}}
    apply_help_text(packs)
    assert packs["en"]["app_title"] == "Workbench"
    assert packs["en"]["tip_t1_std_t"] == HELP_TEXT["en"]["tip_t1_std_t"]


@pytest.mark.parametrize(
    ("anchor", "beside"),
    [((870, 550, 25, 30), False), ((5, 5, 20, 25), False),
     ((820, 200, 60, 18), True), ((5, 580, 60, 18), True)],
)
def test_help_fits_compact_window_edges(anchor, beside):
    x, y = place_help(anchor, (330, 95), (0, 0, 900, 600), beside=beside)
    assert 0 <= x <= 900 - 330
    assert 0 <= y <= 600 - 95
    if anchor[1] == 550:
        assert y + 95 < anchor[1]


def test_escape_without_visible_help_preserves_normal_widget_behavior():
    tip = object.__new__(ContextToolTip)
    tip._tw = None
    hidden = []
    tip._hide = lambda: hidden.append(True)
    assert tip._dismiss() is None
    tip._tw = object()
    assert tip._dismiss() == "break"
    assert hidden == [True, True]


def test_new_help_request_cancels_older_hover_delay():
    root = SimpleNamespace()
    callbacks = {}

    class Widget:
        def _root(self):
            return root

        def bind(self, *_args, **_kwargs):
            pass

        def after(self, delay, callback):
            token = str(len(callbacks) + 1)
            callbacks[token] = callback
            return token

        def after_cancel(self, token):
            callbacks.pop(token, None)

    earlier = ContextToolTip(Widget(), "Earlier hovered control")
    current = ContextToolTip(Widget(), "Current focused control")
    earlier._schedule()
    current._schedule()
    assert earlier._id_after is None
    assert root._saxs_pending_tooltips == {current}
    assert list(callbacks.values()) == [current._show]


def test_localized_option_help_preserves_the_processing_value():
    app = SimpleNamespace(language="zh", tr=lambda key: {"opt_fmt_csv": "逗号分隔表格"}.get(key, key))
    assert option_help(None, "逗号分隔表格", app) == OPTION_HELP["zh"]["fmt_csv"]
    assert option_help(None, "rate", app) == OPTION_HELP["zh"]["rate"]
    assert option_help(None, "unknown_option", app) == ""
    assert app.language == "zh"


def test_material_option_explains_symbols_using_the_actual_preset():
    widget = SimpleNamespace(_saxs_context_tooltip=SimpleNamespace(help_key="tip_mu_preset"))
    app = SimpleNamespace(language="zh", tr=lambda key: key)
    text = option_help(widget, "Ti-6Al-4V (Grade 5)", app)
    assert "钛 90%" in text and "铝 6%" in text and "钒 4%" in text
    assert "4.43 g/cm³" in text


@pytest.mark.parametrize("format_name", ["png", "tif", "tiff", "pdf", "svg", "eps"])
def test_all_figure_export_format_options_have_help(format_name):
    widget = SimpleNamespace(_saxs_context_tooltip=SimpleNamespace(help_key="tip_plot_format"))
    assert option_help(widget, format_name, SimpleNamespace(language="zh", tr=lambda key: key))


def exercise_context_help(app, capture=None):
    """Run only inside the existing isolated-desktop UI harness.

    This helper creates no windows by itself. The harness owns the desktop,
    application and screenshots, so pytest never touches the user's desktop.
    """
    import tkinter as tk
    from tkinter import ttk

    root = app.root
    controller = root._saxs_help_controller
    errors = []
    original_error = root.report_callback_exception
    root.report_callback_exception = lambda *args: errors.append(args)

    def settle(seconds=0.035):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            root.update()
            time.sleep(0.005)

    def popup_text(tip):
        assert tip._tw is not None
        return str(tip._tw.winfo_children()[0].cget("text"))

    def wait_for_focus_help(widget, tip):
        deadline = time.monotonic() + 1
        while time.monotonic() < deadline:
            root.update()
            if root.focus_get() == widget and tip._tw is not None:
                return
            time.sleep(0.005)
        assert root.focus_get() == widget, "Native focus did not reach the requested control."
        assert tip._tw is not None, "Native FocusIn did not show contextual help."

    try:
        root.geometry("900x600+0+0")
        app.nb.select(app.tab1)
        settle()
        controller.refresh()
        main = controller.audit()
        assert not main["missing"], main["missing"]
        for control in _walk(root):
            if isinstance(control, ttk.Combobox):
                assert all(option_help(control, value, app) for value in control.cget("values")), (
                    str(control), control.cget("values")
                )

        # Hover and keyboard focus show the same help without changing the field.
        combo = app.t1_std_combo
        tip = combo._saxs_context_tooltip
        value = combo.get()
        delay = tip.delay_ms
        tip.delay_ms = 1
        combo.event_generate("<Enter>")
        settle()
        assert popup_text(tip)
        combo.event_generate("<Leave>")
        assert tip._tw is None
        combo.focus_force()
        wait_for_focus_help(combo, tip)
        assert popup_text(tip)
        combo.event_generate("<Escape>")
        settle()
        assert tip._tw is None
        combo.event_generate("<F1>")
        settle()
        assert popup_text(tip)
        assert root.focus_get() == combo, "The help window took focus from the input."
        if capture is not None:
            capture(tip._tw, "help-keyboard")
        combo.event_generate("<Escape>")
        settle()
        assert tip._tw is None and combo.get() == value
        tip.delay_ms = delay

        # Refresh the language while an existing tooltip object stays alive.
        initial_language = app.language
        app.toggle_language()
        combo.event_generate("<F1>")
        settle()
        assert HELP_TEXT[app.language][tip.help_key] in popup_text(tip)
        tip._hide()
        app.toggle_language()
        assert app.language == initial_language

        # Private Tcl menu rows receive specific hover explanations.
        combo.tk.call("ttk::combobox::Post", str(combo))
        settle()
        popdown = combo.tk.call("ttk::combobox::PopdownWindow", str(combo))
        listbox = f"{popdown}.f.l"
        bbox = combo.tk.call(listbox, "bbox", 0)
        tip.delay_ms = 1
        combo.tk.call("event", "generate", listbox, "<Motion>", "-x", 5,
                      "-y", int(bbox[1]) + 2)
        settle()
        first = str(combo.tk.call(listbox, "get", 0))
        assert first in popup_text(tip)
        assert option_help(combo, first, app) in popup_text(tip)
        if capture is not None:
            capture(tip._tw, "help-dropdown-option")
        combo.tk.call("ttk::combobox::Unpost", str(combo))
        settle()
        assert tip._tw is None, "Closing the dropdown left its help popup visible."
        assert combo.get() == value, "Viewing dropdown help changed the selected value."
        tip.delay_ms = delay

        # Disabled controls still explain the concrete reason they cannot run.
        app.nb.select(app.tab2)
        settle()
        disabled = [
            w for w in _walk(root)
            if isinstance(w, (ttk.Radiobutton, ttk.Checkbutton)) and w.instate(["disabled"])
            and w.winfo_viewable()
        ]
        assert disabled
        disabled_tip = disabled[0]._saxs_context_tooltip
        disabled_tip._show_now()
        assert popup_text(disabled_tip)
        if capture is not None:
            capture(disabled_tip._tw, "help-disabled")
        disabled_tip._hide()

        # Fields built from local dialog variables are discovered on Map.
        app.open_mu_tool()
        settle()
        controller.refresh()
        all_controls = controller.audit()
        assert not all_controls["missing"], all_controls["missing"]
        dialogs = [w for w in root.winfo_children() if isinstance(w, tk.Toplevel)]
        assert dialogs
        dialog = dialogs[-1]
        entries = [w for w in _walk(dialog) if isinstance(w, ttk.Entry)]
        assert len(entries) >= 4
        assert all(w._saxs_context_tooltip._get_text() for w in entries)
        for control in _walk(dialog):
            if isinstance(control, ttk.Combobox):
                assert all(option_help(control, value, app) for value in control.cget("values")), (
                    str(control), control.cget("values")
                )
        entries[0]._saxs_context_tooltip._show_now()
        if capture is not None:
            capture(entries[0]._saxs_context_tooltip._tw, "help-calculator")
        dialog.destroy()
        settle()
        assert not errors, errors
        return {"main_controls": len(main["covered"]),
                "controls_with_calculator": len(all_controls["covered"])}
    finally:
        active = getattr(root, "_saxs_active_tooltip", None)
        if active is not None:
            active._hide()
        root.report_callback_exception = original_error


def _walk(parent):
    for child in parent.winfo_children():
        if getattr(child, "_saxs_help_popup", False):
            continue
        yield child
        yield from _walk(child)
