"""Context help for the Tk workbench, without changing scientific state."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from saxsabs.workbench_help_text import HELP_TEXT, OPTION_HELP


def apply_help_text(language_packs):
    """Replace help copy before the workbench builds its visible hints."""
    for language, messages in HELP_TEXT.items():
        language_packs.setdefault(language, {}).update(messages)


VARIABLE_HELP = {
    "t1_water_temp": "tip_t1_water_temp",
    "t1_std_ref_path": "tip_t1_std_ref_file",
    "t2_alpha_enabled": "tip_t2_buffer_enable",
    "t2_alpha": "tip_t2_alpha",
    "t2_fluo_enabled": "tip_fluo_enable",
    "t2_fluo_status": "tip_fluo_status",
    "t3_wavelength_a": "tip_t3_wavelength",
    "t3_sample_exp": "tip_t3_sample_exp",
    "t3_sample_i0": "tip_t3_sample_i0",
    "t3_sample_t": "tip_t3_sample_t",
    "t3_bg_exp": "tip_t3_bg_exp",
    "t3_bg_i0": "tip_t3_bg_i0",
    "t3_bg_t": "tip_t3_bg_t",
    "t3_buffer_enabled": "tip_t3_buffer_enable",
    "t3_buffer_path": "tip_t3_buffer_file",
    "t3_alpha": "tip_t3_alpha",
    "t3_alpha_uncertainty": "tip_t3_alpha_uncertainty",
    "t3_buffer_status": "tip_t3_buffer_status",
    "t3_fluo_enabled": "tip_fluo_enable",
    "t3_fluo_status": "tip_fluo_status",
}

CONTROL_HELP = {
    "calibration_load": "tip_calibration_load",
    "view_report": "tip_activity_report",
    "show_details": "tip_details",
    "hide_details": "tip_details",
    "theme_toggle": "tip_theme",
    "lang_toggle_to_zh": "tip_language",
    "lang_toggle_to_en": "tip_language",
    "lbl_t1_std_type": "tip_t1_std_type",
    "lbl_t1_water_temp": "tip_t1_water_temp",
    "lbl_t1_std_ref_file": "tip_t1_std_ref_file",
    "cb_t2_buffer_enable": "tip_t2_buffer_enable",
    "lbl_t2_alpha": "tip_t2_alpha",
    "cb_t2_fluo_enable": "tip_fluo_enable",
    "cb_t3_fluo_enable": "tip_fluo_enable",
    "cb_t3_buffer_enable": "tip_t3_buffer_enable",
    "lbl_t3_buffer_file": "tip_t3_buffer_file",
    "lbl_t3_alpha": "tip_t3_alpha",
    "lbl_t3_alpha_uncertainty": "tip_t3_alpha_uncertainty",
    "lbl_mu_data_source": "tip_mu_source",
    "lbl_mu_energy_or_wl": "tip_mu_wavelength",
    "lbl_mu_preset": "tip_mu_preset",
    "lbl_mu_density": "tip_mu_density",
    "cb_mu_porosity_risk": "tip_mu_porosity",
    "lbl_mu_custom_comp": "tip_mu_composition",
    "lbl_mu_contrib": "tip_mu_result",
    "btn_mu_apply": "tip_mu_calculate",
    "btn_mu_export_json": "tip_mu_export",
}

ATTRIBUTE_HELP = {
    "btn_theme": "tip_theme",
    "btn_lang": "tip_language",
    "btn_calibration_load": "tip_calibration_load",
    "t1_std_combo": "tip_t1_std_type",
    "help_text_widget": "tip_help_text",
}

TOOLBAR_HELP = {
    "Home": "tip_plot_home",
    "Back": "tip_plot_back",
    "Forward": "tip_plot_forward",
    "Pan": "tip_plot_pan",
    "Zoom": "tip_plot_zoom",
    "Subplots": "tip_plot_subplots",
    "Save": "tip_plot_save",
}

INTERACTIVE_CLASSES = {
    "TButton", "Button", "TEntry", "Entry", "TCombobox", "TCheckbutton",
    "Checkbutton", "TRadiobutton", "Radiobutton", "TSpinbox", "Spinbox",
    "TScale", "Scale", "TScrollbar", "Scrollbar", "Listbox", "Text",
    "Canvas", "TNotebook", "Treeview", "TProgressbar", "TPanedwindow",
}


def place_help(anchor, size, bounds, *, beside=False):
    """Keep the help box inside the usable bounds, including near bottom edges."""
    left, top, width, height = anchor
    box_width, box_height = size
    min_x, min_y, max_x, max_y = bounds
    if beside:
        x = left + width + 8
        if x + box_width > max_x:
            x = left - box_width - 8
        y = top
    else:
        x, y = left, top + height + 6
        if y + box_height > max_y:
            y = top - box_height - 6
    x = max(min_x, min(x, max_x - box_width))
    y = max(min_y, min(y, max_y - box_height))
    return int(x), int(y)


class ContextToolTip:
    """A single non-focus-taking popup, available by hover, focus, or F1."""

    DEFAULT_DELAY_MS = 450

    def __init__(self, widget, text, delay_ms=None):
        self.widget = widget
        self.text = text
        self.help_key = None
        self.detail_resolver = None
        self.delay_ms = self.DEFAULT_DELAY_MS if delay_ms is None else delay_ms
        self._tw = None
        self._id_after = None
        self._anchor = None
        self._option = None
        self._beside = False
        widget._saxs_context_tooltip = self
        for sequence in ("<Enter>", "<FocusIn>"):
            widget.bind(sequence, self._schedule, add="+")
        for sequence in ("<Leave>", "<FocusOut>", "<ButtonPress>", "<Unmap>", "<Destroy>"):
            widget.bind(sequence, self._hide, add="+")
        widget.bind("<F1>", self._show_now, add="+")
        widget.bind("<Escape>", self._dismiss, add="+")
        widget.bind("<KeyPress>", self._on_key, add="+")

    def _root(self):
        return self.widget._root()

    def _get_text(self):
        app = getattr(self._root(), "_app_ref", None)
        language = getattr(app, "language", "en")
        pack = HELP_TEXT.get(language, HELP_TEXT["en"])
        if self.detail_resolver is not None:
            return self.detail_resolver()
        if self.help_key is not None:
            text = pack.get(self.help_key, self.text)
        else:
            text = self.text() if callable(self.text) else self.text
        if self.help_key == "tip_theme" and self.widget.instate(["disabled"]):
            return pack.get("tip_theme_unavailable", text)
        if isinstance(self.widget, ttk.Combobox):
            option = self._option if self._option is not None else self.widget.get()
            detail = option_help(self.widget, option, app)
            if detail:
                return f"{text}\n{option}: {detail}"
        return text

    def _schedule(self, event=None):
        self._hide()
        root = self._root()
        pending = getattr(root, "_saxs_pending_tooltips", None)
        if pending is None:
            pending = root._saxs_pending_tooltips = set()
        for other in tuple(pending):
            other._hide()
        pending.add(self)
        self._id_after = self.widget.after(self.delay_ms, self._show)

    def _show_now(self, event=None):
        self._hide()
        self._show()
        return "break"

    def _dismiss(self, event=None):
        visible = self._tw is not None
        self._hide()
        return "break" if visible else None

    def _on_key(self, event):
        if event.keysym not in {"F1", "Escape"}:
            self._hide()

    def _show(self):
        self._id_after = None
        root = self._root()
        pending = getattr(root, "_saxs_pending_tooltips", set())
        pending.discard(self)
        if not self.widget.winfo_exists() or not self.widget.winfo_viewable():
            return
        text = self._get_text()
        if not text:
            return
        # An earlier hover delay must not replace newly requested focus/F1
        # help. New hover events may still request another control normally.
        for other in tuple(pending):
            other._hide()
        previous = getattr(root, "_saxs_active_tooltip", None)
        if previous is not None and previous is not self:
            previous._hide()
        if self._tw is not None:
            self._hide()
        root._saxs_active_tooltip = self
        window = self.widget.winfo_toplevel()
        screen_width, screen_height = root.winfo_screenwidth(), root.winfo_screenheight()
        wrap = min(380, max(160, window.winfo_width() - 36), screen_width - 36)
        style = ttk.Style(self.widget)
        background = style.lookup("TFrame", "background") or "#ffffff"
        foreground = style.lookup("TLabel", "foreground") or "#1a1a1a"
        self._tw = tk.Toplevel(self.widget)
        self._tw._saxs_help_popup = True
        self._tw.withdraw()
        self._tw.overrideredirect(True)
        tk.Label(
            self._tw, text=text, justify="left", background=background,
            foreground=foreground, relief="solid", borderwidth=1,
            font="TkDefaultFont", wraplength=wrap, padx=9, pady=7,
        ).pack()
        self._tw.update_idletasks()
        anchor = self._anchor or (
            self.widget.winfo_rootx(), self.widget.winfo_rooty(),
            self.widget.winfo_width(), self.widget.winfo_height(),
        )
        bounds = (4, 4, screen_width - 4, screen_height - 4)
        if not self._beside:
            bounds = (
                max(4, window.winfo_rootx()), max(4, window.winfo_rooty()),
                min(screen_width - 4, window.winfo_rootx() + window.winfo_width()),
                min(screen_height - 4, window.winfo_rooty() + window.winfo_height()),
            )
        x, y = place_help(
            anchor, (self._tw.winfo_reqwidth(), self._tw.winfo_reqheight()),
            bounds, beside=self._beside,
        )
        self._tw.geometry(f"+{x}+{y}")
        self._tw.deiconify()
        self._tw.lift()

    def _hide(self, event=None):
        if self._id_after is not None:
            try:
                self.widget.after_cancel(self._id_after)
            except tk.TclError:
                pass
            self._id_after = None
        if self._tw is not None:
            popup, self._tw = self._tw, None
            try:
                popup.destroy()
            except tk.TclError:
                pass
        root = self._root()
        getattr(root, "_saxs_pending_tooltips", set()).discard(self)
        if getattr(root, "_saxs_active_tooltip", None) is self:
            root._saxs_active_tooltip = None


def option_help(widget, value, app):
    """Explain actual menu values without replacing processing tokens."""
    language = getattr(app, "language", "en")
    options = OPTION_HELP.get(language, OPTION_HELP["en"])
    token = str(value)
    if app is not None:
        for key in ("nist", "elam"):
            if token == app.tr(f"opt_mu_source_{key}"):
                token = f"mu_source_{key}"
                break
        for key in ("srm3600", "water", "lupolen", "custom"):
            if token == app.tr(f"opt_std_{key}"):
                token = f"std_{key}"
                break
        for key in ("tsv", "csv", "cansas_xml", "nxcansas_h5", "dat", "xml", "h5"):
            if token == app.tr(f"opt_fmt_{key}"):
                format_key = {"cansas_xml": "xml", "nxcansas_h5": "h5"}.get(key, key)
                token = f"fmt_{format_key}"
                break
    # Figure export formats have different meanings from curve table formats.
    if getattr(getattr(widget, "_saxs_context_tooltip", None), "help_key", None) == (
        "tip_plot_format"
    ):
        image_format = token.lower()
        token = f"plot_{'tiff' if image_format == 'tif' else image_format}"
    if getattr(getattr(widget, "_saxs_context_tooltip", None), "help_key", None) == (
        "tip_mu_preset"
    ):
        return _material_option_help(token, language, options)
    return options.get(token, "")


def _material_option_help(value, language, options):
    from saxsabs.core.material_attenuation import NOMINAL_MATERIALS
    from saxsabs.core.mu_calculator import MATERIAL_PRESETS

    names = {
        "Al": ("aluminium", "铝"), "C": ("carbon", "碳"), "Cr": ("chromium", "铬"),
        "Cu": ("copper", "铜"), "Fe": ("iron", "铁"), "H": ("hydrogen", "氢"),
        "Mg": ("magnesium", "镁"), "Mn": ("manganese", "锰"), "Mo": ("molybdenum", "钼"),
        "N": ("nitrogen", "氮"), "Nb": ("niobium", "铌"), "Ni": ("nickel", "镍"),
        "O": ("oxygen", "氧"), "Si": ("silicon", "硅"), "Sn": ("tin", "锡"),
        "Ti": ("titanium", "钛"), "V": ("vanadium", "钒"), "Zn": ("zinc", "锌"),
        "Zr": ("zirconium", "锆"),
    }
    composition, density = None, None
    for spec in NOMINAL_MATERIALS.values():
        if value == f"{spec.display_name} [NIST nominal]":
            composition = spec.composition_dict()
            break
    if composition is None:
        for label, fractions, preset_density in MATERIAL_PRESETS.values():
            if value == label:
                composition, density = fractions, preset_density
                break
    if composition is None:
        return ""
    elements = ", ".join(
        f"{names.get(symbol, (symbol, symbol))[language == 'zh']} {fraction * 100:g}%"
        for symbol, fraction in composition.items()
    )
    text = options["material"].format(composition=elements)
    if density is not None:
        text += options["material_density"].format(density=f"{density:g}")
    return text


def _descendants(parent):
    for child in parent.winfo_children():
        if getattr(child, "_saxs_help_popup", False):
            continue
        yield child
        yield from _descendants(child)


class HelpController:
    """Fill explicit help gaps and watch newly opened workbench windows."""

    def __init__(self, root):
        self.root = root
        self.app = root._app_ref
        self._pending = None
        self._dropdown_callbacks = {}
        self.root.bind_all("<Map>", self._on_map, add="+")
        self.refresh()

    def _on_map(self, event):
        widget = event.widget
        if not isinstance(widget, tk.Misc) or widget._root() is not self.root:
            return
        top = widget.winfo_toplevel()
        if getattr(top, "_saxs_help_popup", False):
            return
        if self._pending is None:
            self._pending = self.root.after_idle(self.refresh)

    def _key_for_text(self, text):
        if text == "E (keV):":
            return "tip_mu_energy"
        if text == "2θ wavelength (Å):":
            return "tip_t3_wavelength"
        for label_key, help_key in CONTROL_HELP.items():
            if str(text) == self.app.tr(label_key):
                return help_key
        return None

    def _key_for_widget(self, widget, registered, variables):
        for attr, key in ATTRIBUTE_HELP.items():
            if widget is getattr(self.app, attr, None):
                return key
        if widget in registered and registered[widget] in CONTROL_HELP:
            return CONTROL_HELP[registered[widget]]
        for option in ("textvariable", "variable"):
            if option in widget.keys():
                key = variables.get(str(widget.cget(option)))
                if key:
                    return key
        if "text" in widget.keys():
            key = self._key_for_text(widget.cget("text"))
            if key:
                return key
        if isinstance(widget, (ttk.Entry, ttk.Combobox, ttk.Spinbox, tk.Entry)):
            # Local calculator variables live in the dialog closure. Match the
            # actual field label or its enclosing group, never a guessed name.
            siblings = widget.master.winfo_children()
            index = siblings.index(widget)
            if widget.winfo_manager() == "pack" and index:
                previous = siblings[index - 1]
                if isinstance(previous, (ttk.Label, tk.Label)):
                    key = self._key_for_text(previous.cget("text"))
                    if key:
                        return key
            if isinstance(widget.master, ttk.LabelFrame):
                return self._key_for_text(widget.master.cget("text"))
        if isinstance(widget, tk.Text):
            if isinstance(widget.master, ttk.LabelFrame):
                key = self._key_for_text(widget.master.cget("text"))
                if key:
                    return key
            return "tip_result_text"
        if isinstance(widget, (ttk.Scrollbar, tk.Scrollbar)):
            return "tip_scrollbar"
        if isinstance(widget, tk.Canvas):
            return "tip_scrollarea" if widget.winfo_children() else "tip_plot_canvas"
        if isinstance(widget, ttk.Notebook):
            return "tip_notebook" if widget is getattr(self.app, "nb", None) else (
                "tip_results_notebook"
            )
        if isinstance(widget, ttk.Panedwindow):
            return "tip_panedwindow"
        return None

    def _attach(self, widget, key):
        tip = getattr(widget, "_saxs_context_tooltip", None)
        if tip is None:
            tip = ContextToolTip(widget, "")
        tip.help_key = key
        if isinstance(widget, ttk.Combobox):
            self._configure_dropdown(widget, tip)
        return tip

    def refresh(self):
        self._pending = None
        self._dropdown_callbacks = {
            path: commands for path, commands in self._dropdown_callbacks.items()
            if int(self.root.tk.call("winfo", "exists", path))
        }
        registered = dict(getattr(self.app, "_i18n_widgets", []))
        variables = {
            str(getattr(self.app, attr)): key
            for attr, key in VARIABLE_HELP.items() if hasattr(self.app, attr)
        }
        for tooltip, key in getattr(self.app, "_i18n_tooltips", []):
            tooltip.help_key = key
        for widget in _descendants(self.root):
            # Matplotlib installs its own English-only help. Replace only those
            # known toolbar tooltip bindings, preserving toolbar commands.
            buttons = getattr(widget, "_buttons", None)
            if isinstance(buttons, dict) and not getattr(widget, "_saxs_toolbar_help", False):
                for name, button in buttons.items():
                    key = TOOLBAR_HELP.get(name)
                    if key:
                        button.unbind("<Enter>")
                        button.unbind("<Leave>")
                        self._attach(button, key)
                widget._saxs_toolbar_help = True
            tip = getattr(widget, "_saxs_context_tooltip", None)
            if tip is not None and tip.help_key not in {"tip_browse_file", "tip_browse_dir"}:
                if isinstance(widget, ttk.Combobox):
                    self._configure_dropdown(widget, tip)
                continue
            key = self._key_for_widget(widget, registered, variables)
            if key:
                self._attach(widget, key)
        # Browse controls share the field's purpose, so an ellipsis is never
        # explained only as "choose a file" with no hint about which file.
        for widget in _descendants(self.root):
            tip = getattr(widget, "_saxs_context_tooltip", None)
            if tip is not None and tip.help_key in {"tip_browse_file", "tip_browse_dir"}:
                entries = [w for w in widget.master.winfo_children() if isinstance(w, ttk.Entry)]
                if entries:
                    target = getattr(entries[0], "_saxs_context_tooltip", None)
                    if target is not None:
                        tip.detail_resolver = lambda tip=tip, target=target: (
                            HELP_TEXT[self.app.language][tip.help_key] + "\n" + target._get_text()
                        )
        self._configure_notebook()

    def _configure_notebook(self):
        notebook = getattr(self.app, "nb", None)
        if notebook is None or getattr(notebook, "_saxs_tab_help", False):
            return
        tip = getattr(notebook, "_saxs_context_tooltip", None)
        if tip is None:
            return
        notebook._saxs_tab_help = True
        keys = ("tip_tab_calibration", "tip_tab_batch", "tip_tab_external", "tip_tab_help")
        notebook._saxs_hover_tab = None

        def tab_text():
            index = notebook._saxs_hover_tab
            if index is None:
                index = notebook.index("current")
            return HELP_TEXT[self.app.language][keys[index]]

        def motion(event):
            try:
                index = notebook.index(f"@{event.x},{event.y}")
            except tk.TclError:
                notebook._saxs_hover_tab = None
                tip._hide()
                return
            if index != notebook._saxs_hover_tab:
                notebook._saxs_hover_tab = index
                tip._schedule()

        tip.detail_resolver = tab_text
        notebook.bind("<Motion>", motion, add="+")
        notebook.bind("<Leave>", lambda _: setattr(notebook, "_saxs_hover_tab", None), add="+")

    def _configure_dropdown(self, combo, tip):
        if getattr(combo, "_saxs_dropdown_help", False):
            return
        combo._saxs_dropdown_help = True
        previous = str(combo.cget("postcommand"))

        def posted():
            if previous:
                combo.tk.eval(previous)
            self._bind_dropdown(combo, tip)

        combo.configure(postcommand=posted)
        combo.bind("<<ComboboxSelected>>", lambda _: self._reset_option(tip), add="+")

    @staticmethod
    def _reset_option(tip):
        tip._hide()
        tip._option, tip._anchor, tip._beside = None, None, False

    def _bind_dropdown(self, combo, tip):
        # Tk's popdown list is a Tcl widget, not a Python Listbox instance.
        popdown = combo.tk.call("ttk::combobox::PopdownWindow", str(combo))
        listbox = f"{popdown}.f.l"
        if not int(combo.tk.call("winfo", "exists", listbox)):
            return
        if listbox in self._dropdown_callbacks:
            return

        def motion(y):
            y = int(y)
            index = int(combo.tk.call(listbox, "nearest", y))
            bbox = combo.tk.call(listbox, "bbox", index)
            if not bbox or not (int(bbox[1]) <= y < int(bbox[1]) + int(bbox[3])):
                tip._hide()
                return
            option = str(combo.tk.call(listbox, "get", index))
            if option == tip._option and (tip._id_after is not None or tip._tw is not None):
                return
            tip._option = option
            tip._anchor = (
                int(combo.tk.call("winfo", "rootx", listbox)),
                int(combo.tk.call("winfo", "rooty", listbox)) + int(bbox[1]),
                int(combo.tk.call("winfo", "width", listbox)), int(bbox[3]),
            )
            tip._beside = True
            tip._schedule()

        move_command = combo.register(motion)
        hide_command = combo.register(lambda: self._reset_option(tip))
        def closed():
            self._reset_option(tip)
            # Unpost withdraws the popup toplevel, not its child listbox. The
            # native focus return can enqueue FocusIn help in the same event
            # cycle; cancel that pending help after native bindings finish.
            combo.after_idle(tip._hide)

        close_command = combo.register(closed)
        combo.tk.call("bind", listbox, "<Motion>", f"+{move_command} %y")
        combo.tk.call("bind", listbox, "<Leave>", f"+{hide_command}")
        combo.tk.call("bind", listbox, "<Unmap>", f"+{hide_command}")
        combo.tk.call("bind", popdown, "<Unmap>", f"+{close_command}")
        self._dropdown_callbacks[listbox] = (move_command, hide_command, close_command)

    def audit(self):
        """Return missing and covered interactive controls for UI acceptance."""
        missing, covered = [], []
        for widget in _descendants(self.root):
            if widget.winfo_class() not in INTERACTIVE_CLASSES:
                continue
            tip = getattr(widget, "_saxs_context_tooltip", None)
            record = {"widget": str(widget), "class": widget.winfo_class()}
            if "text" in widget.keys():
                record["text"] = str(widget.cget("text"))
            if tip is None or not tip._get_text():
                missing.append(record)
            else:
                record["key"] = tip.help_key
                covered.append(record)
        return {"missing": missing, "covered": covered}


def install_context_help(root):
    """Install once, after the workbench has built its controls."""
    controller = getattr(root, "_saxs_help_controller", None)
    if controller is None:
        controller = HelpController(root)
        root._saxs_help_controller = controller
    else:
        controller.refresh()
    return controller
