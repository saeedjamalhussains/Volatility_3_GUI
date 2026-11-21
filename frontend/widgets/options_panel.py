"""
frontend/widgets/options_panel.py — Industry-Grade Plugin Configuration

Dynamic form with typed inputs for all Volatility 3 requirement types.
Professional layout with info badges for automagic-handled requirements.
"""

from __future__ import annotations
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QSpinBox, QDoubleSpinBox,
    QCheckBox, QComboBox, QPushButton,
    QScrollArea, QFrame, QFileDialog,
)


class OptionsPanel(QWidget):
    """Dynamic plugin configuration form."""
    run_requested = Signal(object, dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._plugin_cls = None
        self._plugin_name = ""
        self._field_widgets = {}
        self._field_types = {}
        self._has_file = False
        self._setup_ui()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)

        # Plugin header
        header = QHBoxLayout()
        header.setSpacing(8)

        self._title = QLabel("Select a plugin")
        self._title.setStyleSheet(
            "color: #283850; font-size: 13px; font-weight: 600; "
            "background: transparent;"
        )
        header.addWidget(self._title)
        header.addStretch()

        self._desc = QLabel("")
        self._desc.setStyleSheet(
            "color: #374560; font-size: 11px; background: transparent;"
        )
        self._desc.setWordWrap(True)
        header.addWidget(self._desc)

        root.addLayout(header)

        # Scrollable form
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        self._form_widget = QWidget()
        self._form = QFormLayout(self._form_widget)
        self._form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        self._form.setSpacing(10)
        self._form.setContentsMargins(4, 4, 4, 4)
        scroll.setWidget(self._form_widget)
        root.addWidget(scroll, 1)

        # Run button
        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(0, 4, 0, 0)

        self._run_btn = QPushButton("▶   RUN ANALYSIS")
        self._run_btn.setObjectName("runButton")
        self._run_btn.setFixedHeight(36)
        self._run_btn.setMinimumWidth(160)
        self._run_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._run_btn.setEnabled(False)
        self._run_btn.clicked.connect(self._on_run)

        btn_row.addStretch()
        btn_row.addWidget(self._run_btn)
        root.addLayout(btn_row)

    def set_file_loaded(self, loaded: bool):
        self._has_file = loaded
        self._update_btn()

    def load_plugin(self, name, cls, requirements, description=""):
        self._plugin_cls = cls
        self._plugin_name = name
        self._field_widgets.clear()
        self._field_types.clear()

        short = name.split(".")[-1]
        self._title.setText(short)
        self._title.setStyleSheet(
            "color: #00aaff; font-size: 14px; font-weight: 700; "
            "background: transparent;"
        )
        self._desc.setText(description or "")

        _clear_form(self._form)

        config_reqs = [r for r in requirements if r.req_type != "info"]
        info_reqs   = [r for r in requirements if r.req_type == "info"]

        if not config_reqs and not info_reqs:
            ph = QLabel("No configurable options")
            ph.setStyleSheet(
                "color: #283850; font-style: italic; font-size: 11px; "
                "background: transparent;"
            )
            self._form.addRow(ph)
        else:
            for req in config_reqs:
                widget = _build_widget(req)
                label = QLabel(_fmt_label(req.name, req.optional))
                label.setObjectName(
                    "formLabel" if req.optional else "formLabelRequired")
                label.setToolTip(req.description)
                self._form.addRow(label, widget)
                self._field_widgets[req.name] = widget
                self._field_types[req.name]   = req.req_type

            if info_reqs and config_reqs:
                sep = QFrame()
                sep.setObjectName("separator")
                self._form.addRow(sep)

            for req in info_reqs:
                lbl = QLabel(_fmt_label(req.name, req.optional))
                lbl.setStyleSheet(
                    "color: #283850; font-size: 11px; background: transparent;")
                val = QLabel(req.description)
                val.setStyleSheet(
                    "color: #283850; font-size: 10px; font-style: italic; "
                    "background-color: #080c18; border: 1px solid #111a2e; "
                    "border-radius: 4px; padding: 3px 8px;"
                )
                val.setWordWrap(True)
                self._form.addRow(lbl, val)

        self._update_btn()

    def clear(self):
        self._plugin_cls = None
        self._plugin_name = ""
        self._field_widgets.clear()
        self._field_types.clear()
        _clear_form(self._form)
        self._title.setText("Select a plugin")
        self._title.setStyleSheet(
            "color: #283850; font-size: 13px; font-weight: 600; "
            "background: transparent;"
        )
        self._desc.setText("")
        self._run_btn.setEnabled(False)

    def _on_run(self):
        if not self._plugin_cls:
            return
        overrides = {}
        for name, widget in self._field_widgets.items():
            rt = self._field_types.get(name, "str")
            val = _read_widget(widget, rt)
            if val is not None:
                overrides[name] = val
        self.run_requested.emit(self._plugin_cls, overrides)

    def _update_btn(self):
        self._run_btn.setEnabled(self._plugin_cls is not None and self._has_file)
        if self._plugin_cls and not self._has_file:
            self._run_btn.setToolTip("Load evidence first")
        else:
            self._run_btn.setToolTip("")


# ─── Widget Builders ──────────────────────────────────────────────────────────

def _build_widget(req):
    rt = req.req_type

    if rt == "bool":
        cb = QCheckBox()
        if req.default is not None:
            cb.setChecked(bool(req.default))
        return cb

    if rt == "int":
        sb = QSpinBox()
        sb.setRange(-2_147_483_648, 2_147_483_647)
        if req.default is not None:
            try: sb.setValue(int(req.default))
            except: pass
        return sb

    if rt == "float":
        dsb = QDoubleSpinBox()
        dsb.setRange(-1e12, 1e12)
        dsb.setDecimals(6)
        if req.default is not None:
            try: dsb.setValue(float(req.default))
            except: pass
        return dsb

    if rt == "choice" and req.choices:
        cb = QComboBox()
        cb.addItem("")
        for c in req.choices:
            cb.addItem(str(c))
        if req.default and str(req.default) in req.choices:
            cb.setCurrentText(str(req.default))
        return cb

    if rt in ("list_int", "list_str", "list"):
        le = QLineEdit()
        elem = "integers" if rt == "list_int" else "values"
        le.setPlaceholderText(f"Comma-separated {elem}  e.g. 4, 288")
        if req.default is not None:
            le.setText(str(req.default))
        return le

    if rt == "uri":
        return _URIWidget(req.description or "Select file …", req.default)

    le = QLineEdit()
    le.setPlaceholderText(req.description or req.name)
    if req.default is not None:
        le.setText(str(req.default))
    return le


def _read_widget(widget, req_type):
    if isinstance(widget, QCheckBox):
        return widget.isChecked()
    if isinstance(widget, QSpinBox):
        return widget.value()
    if isinstance(widget, QDoubleSpinBox):
        return widget.value()
    if isinstance(widget, QComboBox):
        t = widget.currentText().strip()
        return t if t else None
    if isinstance(widget, _URIWidget):
        p = widget.get_path()
        if not p: return None
        return Path(p).as_uri() if Path(p).exists() else p
    if isinstance(widget, QLineEdit):
        t = widget.text().strip()
        if not t: return None
        if req_type in ("list_int", "list_str", "list"):
            return _parse_list(t, req_type)
        return t
    return None


def _parse_list(text, req_type):
    parts = [p.strip() for p in text.replace(";", ",").split(",") if p.strip()]
    if req_type == "list_int":
        result = []
        for p in parts:
            try: result.append(int(p, 0))
            except:
                try: result.append(int(float(p)))
                except: pass
        return result
    return parts


class _URIWidget(QWidget):
    def __init__(self, placeholder, default=None, parent=None):
        super().__init__(parent)
        l = QHBoxLayout(self)
        l.setContentsMargins(0, 0, 0, 0)
        l.setSpacing(4)
        self._le = QLineEdit()
        self._le.setPlaceholderText(placeholder)
        if default:
            self._le.setText(str(default))
        btn = QPushButton("…")
        btn.setFixedSize(28, 28)
        btn.setObjectName("ghostButton")
        btn.setToolTip("Browse …")
        btn.clicked.connect(self._browse)
        l.addWidget(self._le, 1)
        l.addWidget(btn)

    def _browse(self):
        p, _ = QFileDialog.getOpenFileName(self, "Select File", "", "All Files (*)")
        if p:
            self._le.setText(p)

    def get_path(self):
        return self._le.text().strip()


def _fmt_label(name, optional):
    label = name.replace("_", " ").replace("-", " ").title()
    return label if optional else label + " *"


def _clear_form(layout):
    while layout.rowCount() > 0:
        layout.removeRow(0)
