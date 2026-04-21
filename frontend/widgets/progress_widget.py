"""
frontend/widgets/progress_widget.py — Minimal Progress Indicator

States: idle → running → done → error
Fits in the thin bottom bar of the main window.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout,
    QProgressBar, QLabel,
)


class ProgressWidget(QWidget):
    """Compact inline progress bar + status label."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._reset_timer = QTimer(self)
        self._reset_timer.setSingleShot(True)
        self._reset_timer.timeout.connect(self.reset)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)
        layout.setSpacing(2)

        # Status row
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)

        self._label = QLabel("Idle")
        self._label.setStyleSheet(
            "color: #374560; font-size: 10px; font-weight: 500; "
            "background: transparent;"
        )
        self._pct = QLabel("")
        self._pct.setAlignment(Qt.AlignmentFlag.AlignRight)
        self._pct.setStyleSheet(
            "color: #283850; font-size: 10px; background: transparent;"
        )
        row.addWidget(self._label)
        row.addWidget(self._pct)
        layout.addLayout(row)

        # Bar
        self._bar = QProgressBar()
        self._bar.setRange(0, 100)
        self._bar.setValue(0)
        self._bar.setFixedHeight(4)
        self._bar.setTextVisible(False)
        layout.addWidget(self._bar)

    def set_progress(self, pct: int, desc: str = ""):
        safe = max(0, min(100, pct))
        self._bar.setRange(0, 100)
        self._bar.setValue(safe)
        self._label.setText(desc or f"Running … {safe}%")
        self._label.setStyleSheet(
            "color: #00aaff; font-size: 10px; font-weight: 500; "
            "background: transparent;"
        )
        self._pct.setText(f"{safe}%")

    def set_running(self, desc: str = "Running …"):
        self._bar.setRange(0, 0)   # indeterminate
        self._label.setText(desc)
        self._label.setStyleSheet(
            "color: #00aaff; font-size: 10px; font-weight: 500; "
            "background: transparent;"
        )
        self._pct.setText("")

    def set_done(self, msg: str = "Done", auto_reset_ms: int = 3000):
        self._bar.setRange(0, 100)
        self._bar.setValue(100)
        self._label.setText(msg)
        self._label.setStyleSheet(
            "color: #00e68a; font-size: 10px; font-weight: 500; "
            "background: transparent;"
        )
        self._pct.setText("✓")
        if auto_reset_ms > 0:
            self._reset_timer.start(auto_reset_ms)

    def set_error(self, msg: str = "Error"):
        self._bar.setRange(0, 100)
        self._bar.setValue(0)
        self._label.setText(msg)
        self._label.setStyleSheet(
            "color: #ff4060; font-size: 10px; font-weight: 500; "
            "background: transparent;"
        )
        self._pct.setText("✗")

    def reset(self):
        self._bar.setRange(0, 100)
        self._bar.setValue(0)
        self._label.setText("Idle")
        self._label.setStyleSheet(
            "color: #374560; font-size: 10px; font-weight: 500; "
            "background: transparent;"
        )
        self._pct.setText("")
