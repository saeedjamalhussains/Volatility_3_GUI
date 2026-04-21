"""
frontend/widgets/results_panel.py — Industry-Grade Data Grid

Sortable table wired to ResultsTableModel with:
  - Row-count badge
  - Copy selected rows / cells via Ctrl+C and context menu
  - Column auto-resize with max-width capping
  - Professional header styling
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QSortFilterProxyModel
from PySide6.QtGui import QKeySequence, QAction
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QTableView, QLabel, QPushButton,
    QHeaderView, QMenu, QAbstractItemView,
    QApplication,
)

from models.table_model import ResultsTableModel


class ResultsPanel(QWidget):
    """Results data grid."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._model = ResultsTableModel()
        self._proxy = QSortFilterProxyModel()
        self._proxy.setSourceModel(self._model)
        self._proxy.setSortRole(Qt.ItemDataRole.UserRole)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # Header
        header = QHBoxLayout()
        header.setContentsMargins(4, 0, 4, 0)

        self._title = QLabel("ANALYSIS RESULTS")
        self._title.setObjectName("sectionTitle")
        header.addWidget(self._title)

        header.addStretch()

        self._badge = QLabel("0 rows")
        self._badge.setObjectName("badge")
        header.addWidget(self._badge)

        self._clear_btn = QPushButton("Clear")
        self._clear_btn.setObjectName("ghostButton")
        self._clear_btn.setFixedHeight(22)
        self._clear_btn.clicked.connect(self.clear)
        header.addWidget(self._clear_btn)

        layout.addLayout(header)

        # Table
        self._table = QTableView()
        self._table.setModel(self._proxy)
        self._table.setSortingEnabled(True)
        self._table.setAlternatingRowColors(True)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.verticalHeader().setDefaultSectionSize(30)
        self._table.verticalHeader().setVisible(False)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Interactive)
        self._table.horizontalHeader().setDefaultAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self._table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._table.customContextMenuRequested.connect(self._context_menu)
        self._table.setShowGrid(False)

        copy_action = QAction("Copy", self._table)
        copy_action.setShortcut(QKeySequence.StandardKey.Copy)
        copy_action.triggered.connect(self._copy_rows)
        self._table.addAction(copy_action)

        layout.addWidget(self._table)

    def load_data(self, columns, rows):
        self._model.load_data(columns, rows)
        self._proxy.invalidate()
        count = len(rows)
        self._badge.setText(f"{count:,} rows")
        if count:
            self._table.resizeColumnsToContents()
            for c in range(self._model.columnCount()):
                if self._table.columnWidth(c) > 300:
                    self._table.setColumnWidth(c, 300)

    def clear(self):
        self._model.clear()
        self._badge.setText("0 rows")

    def set_title(self, title: str):
        self._title.setText(f"{title.upper()} RESULTS")

    def get_model(self):
        return self._model

    def _copy_rows(self):
        indices = self._table.selectedIndexes()
        if not indices:
            return
        rows_map = {}
        for idx in indices:
            src = self._proxy.mapToSource(idx)
            rows_map.setdefault(src.row(), {})[src.column()] = str(
                self._model.data(src, Qt.ItemDataRole.DisplayRole) or "")
        lines = ["\t".join(self._model.column_names())]
        for r in sorted(rows_map):
            cells = [rows_map[r].get(c, "") for c in range(self._model.columnCount())]
            lines.append("\t".join(cells))
        QApplication.clipboard().setText("\n".join(lines))

    def _copy_cell(self):
        idx = self._table.currentIndex()
        if idx.isValid():
            src = self._proxy.mapToSource(idx)
            QApplication.clipboard().setText(
                str(self._model.data(src, Qt.ItemDataRole.DisplayRole) or ""))

    def _context_menu(self, pos):
        menu = QMenu(self._table)
        menu.addAction("Copy selected rows", self._copy_rows)
        menu.addAction("Copy cell", self._copy_cell)
        menu.exec(self._table.viewport().mapToGlobal(pos))
