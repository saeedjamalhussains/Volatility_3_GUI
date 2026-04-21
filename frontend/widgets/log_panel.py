"""
frontend/widgets/log_panel.py — Industry-Grade Analysis Console

Color-coded scrollable log console with timestamp, level badges,
copy/clear controls, and monospace rendering for forensic readability.
"""

from __future__ import annotations
from datetime import datetime

from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QTextCharFormat, QColor, QTextCursor, QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QPlainTextEdit, QPushButton, QLabel,
)

_LEVELS = {
    "DEBUG":   ("#283850", "DBG"),
    "INFO":    ("#00aaff", "INF"),
    "SUCCESS": ("#00e68a", " OK"),
    "WARNING": ("#ffb020", "WRN"),
    "ERROR":   ("#ff4060", "ERR"),
}


class LogPanel(QWidget):
    """Forensic analysis console."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Header
        header = QHBoxLayout()
        header.setContentsMargins(4, 0, 4, 0)

        title = QLabel("ANALYSIS CONSOLE")
        title.setObjectName("sectionTitle")
        header.addWidget(title)
        header.addStretch()

        self._copy_btn = QPushButton("Copy")
        self._copy_btn.setObjectName("ghostButton")
        self._copy_btn.setFixedHeight(22)
        self._copy_btn.clicked.connect(self._copy_all)
        header.addWidget(self._copy_btn)

        self._clear_btn = QPushButton("Clear")
        self._clear_btn.setObjectName("ghostButton")
        self._clear_btn.setFixedHeight(22)
        self._clear_btn.clicked.connect(self.clear)
        header.addWidget(self._clear_btn)

        layout.addLayout(header)

        # Console
        self._text = QPlainTextEdit()
        self._text.setReadOnly(True)
        self._text.setMaximumBlockCount(5000)
        font = QFont("Cascadia Code", 11)
        if not font.exactMatch():
            font = QFont("JetBrains Mono", 11)
        if not font.exactMatch():
            font = QFont("Consolas", 11)
        self._text.setFont(font)
        layout.addWidget(self._text)

    @Slot(str, str)
    def append_log(self, level: str, message: str):
        ts = datetime.now().strftime("%H:%M:%S")
        colour, prefix = _LEVELS.get(level.upper(), ("#506888", "???"))
        line = f"  {ts}  │  {prefix}  │  {message}"

        fmt = QTextCharFormat()
        fmt.setForeground(QColor(colour))

        cursor = self._text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(line + "\n", fmt)
        self._text.verticalScrollBar().setValue(
            self._text.verticalScrollBar().maximum()
        )

    def append_separator(self):
        self.append_log("DEBUG", "─" * 58)

    def clear(self):
        self._text.clear()

    def _copy_all(self):
        from PySide6.QtWidgets import QApplication
        QApplication.clipboard().setText(self._text.toPlainText())
