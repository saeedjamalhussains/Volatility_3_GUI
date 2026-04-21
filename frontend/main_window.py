"""
frontend/main_window.py
------------------------
Industry-grade main application window for Volatility 3 GUI.

Layout:
  ┌─── HEADER BAR ───────────────────────────────────────────────┐
  │  Logo  │  Open  │  Export  │  Clear  │ ─spacer─ │  About     │
  ├────────┼─────────────────────────────────────────────────────┤
  │        │  PLUGIN CONFIG                                      │
  │ SIDE   │  ┌───────────────────────────────────────────┐     │
  │ BAR    │  │ Options form + Run button                  │     │
  │        │  └───────────────────────────────────────────┘     │
  │ File   ├─────────────────────────────────────────────────────┤
  │ Panel  │  RESULTS / LOGS  (tabs)                             │
  │        │  ┌───────────────────────────────────────────┐     │
  │ Plugin │  │ Sortable data table / Log console          │     │
  │ Tree   │  │                                            │     │
  │        │  └───────────────────────────────────────────┘     │
  ├────────┴─────────────────────────────────────────────────────┤
  │  ─── PROGRESS BAR ───  │  Status info  │  Plugin count       │
  └──────────────────────────────────────────────────────────────┘
"""

from __future__ import annotations
import logging
import sys
from pathlib import Path
from datetime import datetime

from PySide6.QtCore import Qt, QThread, Slot, QSize, QTimer
from PySide6.QtGui import QAction, QKeySequence, QFont, QIcon
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QSplitter, QVBoxLayout, QHBoxLayout,
    QStatusBar, QTabWidget, QFileDialog, QMessageBox,
    QApplication, QFrame, QLabel, QPushButton, QSizePolicy,
)

from backend.volatility_runner import VolatilityRunner
from backend.plugin_manager import PluginManager
from backend.plugin_runner import PluginWorker, OSDetectWorker
from backend.exporters import export_json, export_csv

from frontend.widgets.file_panel import FilePanel
from frontend.widgets.plugin_panel import PluginPanel
from frontend.widgets.options_panel import OptionsPanel
from frontend.widgets.results_panel import ResultsPanel
from frontend.widgets.log_panel import LogPanel
from frontend.widgets.progress_widget import ProgressWidget

log = logging.getLogger(__name__)


# ─── Design Tokens ────────────────────────────────────────────────────────────

class _C:
    """Colour constants for inline styling."""
    BG_0        = "#06080f"     # deepest
    BG_1        = "#080c16"     # sidebar
    BG_2        = "#0b1020"     # cards
    BG_3        = "#0d1628"     # hover
    BORDER      = "#141e35"
    BORDER_LITE = "#111a2e"
    ACCENT      = "#00aaff"
    ACCENT_DIM  = "#00aaff40"
    VIOLET      = "#7c5cfc"
    SUCCESS     = "#00e68a"
    WARNING     = "#ffb020"
    DANGER      = "#ff4060"
    TEXT_0      = "#e8edf5"     # headings
    TEXT_1      = "#c0cce0"     # body
    TEXT_2      = "#809cc0"     # secondary
    TEXT_3      = "#506888"     # muted
    TEXT_4      = "#374560"     # very muted


class MainWindow(QMainWindow):
    """Industry-grade forensics workstation window."""

    APP_TITLE = "Volatility 3"
    VERSION   = "1.0.0"

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"{self.APP_TITLE}")
        self.setMinimumSize(1280, 760)
        self.resize(1500, 900)
        self.setContentsMargins(0, 0, 0, 0)

        # Backend
        self._runner = VolatilityRunner()
        self._plugin_mgr = PluginManager()
        self._active_worker: QThread | None = None
        self._last_columns: list[str] = []
        self._last_rows: list[dict] = []
        self._current_plugin_name: str = ""
        self._session_start = datetime.now()

        self._build_ui()
        self._connect_signals()
        self._load_plugins_async()

    # ══════════════════════════════════════════════════════════════════════
    # UI CONSTRUCTION
    # ══════════════════════════════════════════════════════════════════════

    def _build_ui(self) -> None:
        central = QWidget()
        central.setObjectName("centralWidget")
        central.setStyleSheet(f"QWidget#centralWidget {{ background-color: {_C.BG_0}; }}")
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Header bar ────────────────────────────────────────────────
        root.addWidget(self._build_header())

        # ── Main content area ─────────────────────────────────────────
        content = QWidget()
        content_layout = QHBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # Sidebar
        content_layout.addWidget(self._build_sidebar())

        # Center area
        center = QWidget()
        center_layout = QVBoxLayout(center)
        center_layout.setContentsMargins(12, 10, 12, 8)
        center_layout.setSpacing(8)

        # Options card
        self._options_panel = OptionsPanel()
        options_card = self._make_card("PLUGIN CONFIGURATION", self._options_panel)
        options_card.setMaximumHeight(300)

        # Tabs: Results | Logs
        self._tab_widget = QTabWidget()
        self._results_panel = ResultsPanel()
        self._log_panel = LogPanel()
        self._tab_widget.addTab(self._results_panel, "  Results  ")
        self._tab_widget.addTab(self._log_panel,     "  Console  ")

        # Split between options and tabs
        vsplit = QSplitter(Qt.Orientation.Vertical)
        vsplit.setHandleWidth(1)
        vsplit.addWidget(options_card)
        vsplit.addWidget(self._tab_widget)
        vsplit.setStretchFactor(0, 0)
        vsplit.setStretchFactor(1, 1)
        vsplit.setSizes([220, 500])

        center_layout.addWidget(vsplit)
        content_layout.addWidget(center)

        root.addWidget(content, 1)

        # ── Bottom bar ────────────────────────────────────────────────
        root.addWidget(self._build_bottom_bar())

    # ──────────────────────────────────────────────────────────────────
    # HEADER BAR
    # ──────────────────────────────────────────────────────────────────

    def _build_header(self) -> QWidget:
        header = QWidget()
        header.setObjectName("headerBar")
        header.setFixedHeight(50)

        layout = QHBoxLayout(header)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(6)

        # ─ Logo ─
        logo = QLabel("⬡ VOLATILITY")
        logo.setStyleSheet(
            f"color: {_C.ACCENT}; font-size: 15px; font-weight: 800; "
            f"letter-spacing: 2px; background: transparent; padding-right: 6px;"
        )
        layout.addWidget(logo)

        ver = QLabel(f"v{self.VERSION}")
        ver.setStyleSheet(
            f"color: {_C.TEXT_4}; font-size: 10px; font-weight: 500; "
            f"background: transparent; padding-right: 20px;"
        )
        layout.addWidget(ver)

        # ─ Header divider ─
        layout.addWidget(self._vline())

        # ─ Buttons ─
        self._btn_open = self._header_btn("Open Image", "Ctrl+O")
        self._btn_open.clicked.connect(self._action_open)
        layout.addWidget(self._btn_open)

        layout.addWidget(self._vline())

        self._btn_export_json = self._header_btn("Export JSON")
        self._btn_export_json.setEnabled(False)
        self._btn_export_json.clicked.connect(self._action_export_json)
        layout.addWidget(self._btn_export_json)

        self._btn_export_csv = self._header_btn("Export CSV")
        self._btn_export_csv.setEnabled(False)
        self._btn_export_csv.clicked.connect(self._action_export_csv)
        layout.addWidget(self._btn_export_csv)

        layout.addWidget(self._vline())

        self._btn_clear = self._header_btn("Clear")
        self._btn_clear.setEnabled(False)
        self._btn_clear.clicked.connect(self._action_clear)
        layout.addWidget(self._btn_clear)

        # ─ Spacer ─
        layout.addStretch()

        # ─ Session timer ─
        self._session_label = QLabel("")
        self._session_label.setStyleSheet(
            f"color: {_C.TEXT_4}; font-size: 10px; font-weight: 500; "
            f"background: transparent; padding-right: 8px;"
        )
        layout.addWidget(self._session_label)
        self._session_timer = QTimer(self)
        self._session_timer.timeout.connect(self._update_session_timer)
        self._session_timer.start(1000)
        self._update_session_timer()

        layout.addWidget(self._vline())

        self._btn_about = self._header_btn("About")
        self._btn_about.clicked.connect(self._action_about)
        layout.addWidget(self._btn_about)

        return header

    # ──────────────────────────────────────────────────────────────────
    # SIDEBAR
    # ──────────────────────────────────────────────────────────────────

    def _build_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(280)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(10, 10, 0, 10)
        layout.setSpacing(10)

        # ─ File Panel ─
        self._file_panel = FilePanel()
        file_card = self._make_card("EVIDENCE", self._file_panel, accent=True)
        layout.addWidget(file_card)

        # ─ Plugin Panel ─
        self._plugin_panel = PluginPanel()
        plugin_card = self._make_card("PLUGINS", self._plugin_panel)
        layout.addWidget(plugin_card, 1)

        return sidebar

    # ──────────────────────────────────────────────────────────────────
    # BOTTOM BAR
    # ──────────────────────────────────────────────────────────────────

    def _build_bottom_bar(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(36)
        bar.setStyleSheet(
            f"background-color: {_C.BG_0}; border-top: 1px solid {_C.BORDER_LITE};"
        )

        layout = QHBoxLayout(bar)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(12)

        # Progress widget
        self._progress = ProgressWidget()
        self._progress.setFixedWidth(300)
        layout.addWidget(self._progress)

        # Separator
        layout.addWidget(self._vline())

        # Status label
        self._status_label = QLabel("Ready")
        self._status_label.setStyleSheet(
            f"color: {_C.TEXT_3}; font-size: 11px; background: transparent;"
        )
        layout.addWidget(self._status_label)

        layout.addStretch()

        # Plugin count badge
        self._plugin_count_label = QLabel("⬡  Loading …")
        self._plugin_count_label.setObjectName("badge")
        layout.addWidget(self._plugin_count_label)

        return bar

    # ══════════════════════════════════════════════════════════════════════
    # UI COMPONENT FACTORIES
    # ══════════════════════════════════════════════════════════════════════

    def _make_card(self, title: str, content: QWidget,
                   accent: bool = False) -> QFrame:
        """Create a titled section card with consistent styling."""
        card = QFrame()
        card.setObjectName("card")

        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 10, 12, 12)
        layout.setSpacing(8)

        # Title row
        title_row = QHBoxLayout()
        title_row.setSpacing(8)

        title_label = QLabel(title)
        title_label.setObjectName("sectionTitleAccent" if accent else "sectionTitle")

        title_row.addWidget(title_label)
        title_row.addStretch()
        layout.addLayout(title_row)

        # Accent separator
        sep = QFrame()
        sep.setObjectName("separatorAccent" if accent else "separator")
        layout.addWidget(sep)

        layout.addWidget(content, 1)
        return card

    def _header_btn(self, text: str, shortcut: str | None = None) -> QPushButton:
        """Create a header toolbar button."""
        btn = QPushButton(text)
        btn.setObjectName("headerBtn")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        if shortcut:
            btn.setShortcut(QKeySequence(shortcut))
            btn.setToolTip(f"{text}  ({shortcut})")
        return btn

    @staticmethod
    def _vline() -> QFrame:
        line = QFrame()
        line.setFrameShape(QFrame.Shape.VLine)
        line.setFixedWidth(1)
        line.setStyleSheet(
            f"background-color: {_C.BORDER}; border: none; max-width: 1px;"
        )
        return line

    # ══════════════════════════════════════════════════════════════════════
    # STATUS & SESSION
    # ══════════════════════════════════════════════════════════════════════

    def _set_status(self, msg: str) -> None:
        self._status_label.setText(msg)

    def _update_session_timer(self) -> None:
        elapsed = datetime.now() - self._session_start
        mins, secs = divmod(int(elapsed.total_seconds()), 60)
        hrs, mins = divmod(mins, 60)
        self._session_label.setText(
            f"SESSION  {hrs:02d}:{mins:02d}:{secs:02d}"
        )

    # ══════════════════════════════════════════════════════════════════════
    # SIGNAL WIRING
    # ══════════════════════════════════════════════════════════════════════

    def _connect_signals(self) -> None:
        self._file_panel.file_loaded.connect(self._on_file_loaded)
        self._plugin_panel.plugin_selected.connect(self._on_plugin_selected)
        self._options_panel.run_requested.connect(self._on_run_requested)

    # ══════════════════════════════════════════════════════════════════════
    # PLUGIN LOADING (async)
    # ══════════════════════════════════════════════════════════════════════

    def _load_plugins_async(self) -> None:
        from utils.threading import BaseWorker

        class LoadWorker(BaseWorker):
            def __init__(self, mgr, parent=None):
                super().__init__(parent)
                self._mgr = mgr

            def _run(self):
                self._emit_log("INFO", "Initializing Volatility 3 framework …")
                failures = self._mgr.load_all()
                if failures:
                    self._emit_log("WARNING",
                        f"{len(failures)} optional plugin(s) unavailable "
                        f"(missing dependencies like yara-python)")
                count = len(self._mgr.get_plugins())
                self._emit_log("SUCCESS", f"Framework ready — {count} plugins loaded")
                self.signals.result_ready.emit([], [])

        worker = LoadWorker(self._plugin_mgr, self)
        worker.signals.log_message.connect(self._log_panel.append_log)
        worker.signals.result_ready.connect(self._on_plugins_loaded)
        worker.signals.finished.connect(worker.deleteLater)
        worker.start()
        self._progress.set_running("Initializing framework …")
        self._set_status("Loading Volatility 3 …")

    @Slot(list, list)
    def _on_plugins_loaded(self, _r, _c) -> None:
        groups = self._plugin_mgr.group_by_os()
        all_plugins = self._plugin_mgr.get_plugins()
        descriptions = {
            n: self._plugin_mgr.get_description(c) for n, c in all_plugins.items()
        }
        self._plugin_panel.load_plugins(groups, all_plugins, descriptions)
        total = sum(len(v) for v in groups.values())
        self._progress.set_done(f"{total} plugins ready")
        self._set_status("Ready")
        self._plugin_count_label.setText(f"⬡  {total} plugins")
        self._plugin_count_label.setObjectName("badgeSuccess")
        self._plugin_count_label.setStyleSheet(
            self._plugin_count_label.styleSheet()  # force re-apply
        )

    # ══════════════════════════════════════════════════════════════════════
    # FILE LOADING
    # ══════════════════════════════════════════════════════════════════════

    @Slot(str)
    def _on_file_loaded(self, path: str) -> None:
        fname = Path(path).name
        self._set_status(f"Loading: {fname}")
        self._options_panel.set_file_loaded(False)
        self._progress.set_running(f"Loading {fname} …")
        self._log_panel.append_log("INFO", f"Loading evidence: {path}")

        try:
            self._runner.load_image(path)
        except Exception as exc:
            self._log_panel.append_log("ERROR", str(exc))
            self._progress.set_error("Load failed")
            self._set_status("Error")
            QMessageBox.critical(self, "Load Error",
                                 f"Could not load memory image:\n\n{exc}")
            return

        self._options_panel.set_file_loaded(True)
        fsize = Path(path).stat().st_size
        fsize_str = _fmt_bytes(fsize)
        self._set_status(f"{fname}  ({fsize_str})")
        self._log_panel.append_log("SUCCESS",
            f"Evidence loaded: {fname}  ({fsize_str})")
        self._progress.set_done("Evidence loaded", auto_reset_ms=1500)
        self._start_os_detection()

    def _start_os_detection(self) -> None:
        worker = OSDetectWorker(self._runner, self)
        worker.signals.log_message.connect(self._log_panel.append_log)
        worker.signals.progress.connect(self._on_worker_progress)
        worker.signals.result_ready.connect(self._on_os_detected)
        worker.signals.finished.connect(worker.deleteLater)
        worker.start()
        self._progress.set_running("Identifying OS …")

    @Slot(list, list)
    def _on_os_detected(self, rows: list, _cols: list) -> None:
        os_name = rows[0].get("os", "Unknown") if rows else "Unknown"
        self._file_panel.set_os(os_name)
        self._log_panel.append_log("SUCCESS", f"Identified OS: {os_name}")
        self._progress.set_done(f"OS: {os_name}", auto_reset_ms=2000)

    # ══════════════════════════════════════════════════════════════════════
    # PLUGIN SELECTION
    # ══════════════════════════════════════════════════════════════════════

    @Slot(str, object)
    def _on_plugin_selected(self, name: str, cls: type) -> None:
        self._current_plugin_name = name
        reqs = self._plugin_mgr.get_requirements(cls)
        desc = self._plugin_mgr.get_description(cls)
        self._options_panel.load_plugin(name, cls, reqs, desc)
        self._set_status(f"Plugin: {name}")
        self._log_panel.append_log("INFO", f"Selected → {name}")

    # ══════════════════════════════════════════════════════════════════════
    # PLUGIN EXECUTION
    # ══════════════════════════════════════════════════════════════════════

    @Slot(object, dict)
    def _on_run_requested(self, plugin_cls: type, config: dict) -> None:
        if self._active_worker and self._active_worker.isRunning():
            QMessageBox.warning(self, "Busy",
                "An analysis is already running.\nPlease wait for it to finish.")
            return

        name = self._current_plugin_name or plugin_cls.__name__
        self._log_panel.append_separator()
        self._log_panel.append_log("INFO", f"Executing: {name}")
        if config:
            self._log_panel.append_log("INFO", f"Parameters: {config}")

        self._results_panel.clear()
        self._results_panel.set_title(name.split(".")[-1])
        self._tab_widget.setCurrentIndex(0)

        self._btn_export_json.setEnabled(False)
        self._btn_export_csv.setEnabled(False)
        self._btn_clear.setEnabled(False)
        self._progress.set_running(f"Analyzing: {name} …")
        self._set_status(f"Running: {name}")

        worker = PluginWorker(self._runner, plugin_cls, config, self)
        self._active_worker = worker
        worker.signals.progress.connect(self._on_worker_progress)
        worker.signals.log_message.connect(self._log_panel.append_log)
        worker.signals.result_ready.connect(self._on_plugin_done)
        worker.signals.error.connect(self._on_plugin_error)
        worker.signals.finished.connect(self._on_worker_finished)
        worker.signals.finished.connect(worker.deleteLater)
        worker.start()

    @Slot(int, str)
    def _on_worker_progress(self, pct: int, desc: str) -> None:
        self._progress.set_progress(pct, desc)

    @Slot(list, list)
    def _on_plugin_done(self, rows: list, columns: list) -> None:
        self._last_rows = rows
        self._last_columns = columns
        self._results_panel.load_data(columns, rows)
        self._log_panel.append_log("SUCCESS",
            f"Analysis complete — {len(rows):,} rows")
        self._progress.set_done(f"{len(rows):,} rows")
        self._btn_export_json.setEnabled(bool(rows))
        self._btn_export_csv.setEnabled(bool(rows))
        self._btn_clear.setEnabled(True)
        self._set_status(f"Done — {len(rows):,} rows")

    @Slot(str)
    def _on_plugin_error(self, tb: str) -> None:
        self._log_panel.append_log("ERROR", tb)
        self._progress.set_error("Analysis failed")
        self._tab_widget.setCurrentIndex(1)
        QMessageBox.critical(self, "Analysis Error",
            "The plugin encountered an error.\n\nSee the Console tab for details.")

    @Slot()
    def _on_worker_finished(self) -> None:
        self._active_worker = None

    # ══════════════════════════════════════════════════════════════════════
    # TOOLBAR ACTIONS
    # ══════════════════════════════════════════════════════════════════════

    def _action_open(self) -> None:
        from frontend.widgets.file_panel import _BROWSE_FILTER
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Memory Image", "", _BROWSE_FILTER)
        if path:
            self._file_panel._on_file_selected(path)

    def _action_export_json(self) -> None:
        if not self._last_rows:
            return
        default_name = f"vol3_{self._current_plugin_name.replace('.','_')}.json"
        path, _ = QFileDialog.getSaveFileName(
            self, "Export JSON", default_name, "JSON Files (*.json)")
        if path:
            try:
                export_json(path, self._last_columns, self._last_rows)
                self._log_panel.append_log("SUCCESS", f"Exported → {path}")
                self._set_status(f"Exported: {Path(path).name}")
            except Exception as exc:
                QMessageBox.critical(self, "Export Error", str(exc))

    def _action_export_csv(self) -> None:
        if not self._last_rows:
            return
        default_name = f"vol3_{self._current_plugin_name.replace('.','_')}.csv"
        path, _ = QFileDialog.getSaveFileName(
            self, "Export CSV", default_name, "CSV Files (*.csv)")
        if path:
            try:
                export_csv(path, self._last_columns, self._last_rows)
                self._log_panel.append_log("SUCCESS", f"Exported → {path}")
                self._set_status(f"Exported: {Path(path).name}")
            except Exception as exc:
                QMessageBox.critical(self, "Export Error", str(exc))

    def _action_clear(self) -> None:
        self._results_panel.clear()
        self._last_rows = []
        self._last_columns = []
        self._btn_export_json.setEnabled(False)
        self._btn_export_csv.setEnabled(False)
        self._btn_clear.setEnabled(False)

    def _action_about(self) -> None:
        dlg = QMessageBox(self)
        dlg.setWindowTitle("About Volatility 3 GUI")
        dlg.setTextFormat(Qt.TextFormat.RichText)
        dlg.setText(
            "<div style='text-align:center;'>"
            "<h2 style='color:#00aaff; margin-bottom:4px;'>⬡ VOLATILITY 3 GUI</h2>"
            f"<p style='color:#506888;'>Version {self.VERSION}</p>"
            "<hr style='border-color:#141e35;'>"
            "<p style='color:#a0b0cc;'>Industry-grade desktop interface for the "
            "<b>Volatility 3</b> memory forensics framework.</p>"
            "<br>"
            "<table style='color:#607090; font-size:12px;' cellpadding='4'>"
            "<tr><td align='right'><b>Framework</b></td>"
            "<td>Volatility 3</td></tr>"
            "<tr><td align='right'><b>GUI</b></td>"
            "<td>PySide6 (Qt6)</td></tr>"
            "<tr><td align='right'><b>Language</b></td>"
            "<td>Python 3</td></tr>"
            "</table>"
            "<br>"
            "<p style='color:#374560; font-size:11px;'>"
            "Built for memory forensics professionals</p>"
            "</div>"
        )
        dlg.exec()

    # ══════════════════════════════════════════════════════════════════════
    # WINDOW EVENTS
    # ══════════════════════════════════════════════════════════════════════

    def closeEvent(self, event) -> None:
        if self._active_worker and self._active_worker.isRunning():
            self._active_worker.cancel()
            self._active_worker.quit()
            self._active_worker.wait(3000)
        event.accept()


# ─── Utilities ─────────────────────────────────────────────────────────────────

def _fmt_bytes(n: int) -> str:
    """Format a byte count as a human-readable string."""
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(n) < 1024:
            return f"{n:.1f} {unit}" if unit != "B" else f"{n} {unit}"
        n /= 1024
    return f"{n:.1f} PB"
