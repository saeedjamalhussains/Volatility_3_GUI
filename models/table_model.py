"""
models/table_model.py
---------------------
QAbstractTableModel implementation for Volatility plugin results.

Provides:
  - ResultsTableModel: the main model used by the results QTableView
  - Sortable columns (client-side sort via Python's built-in sort)
  - Safe display of all Volatility data types
  - Efficient data loading via beginResetModel / endResetModel
"""

from __future__ import annotations
from typing import Any

from PySide6.QtCore import (
    Qt,
    QAbstractTableModel,
    QModelIndex,
    QSortFilterProxyModel,
)
from PySide6.QtGui import QColor, QFont


# ---------------------------------------------------------------------------
# Colour palette — matches the industry-grade dark forensics theme
# ---------------------------------------------------------------------------
_ALT_ROW_BG    = QColor("#0b1020")
_NORMAL_ROW_BG = QColor("#080c16")
_HEADER_FG     = QColor("#506888")
_CELL_FG       = QColor("#c0cce0")
_NONE_FG       = QColor("#283850")


# ---------------------------------------------------------------------------
# ResultsTableModel
# ---------------------------------------------------------------------------

class ResultsTableModel(QAbstractTableModel):
    """
    Table model for Volatility plugin results.

    Data is stored as a list of dicts:  [{column_name: value, ...}, ...]
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._columns: list[str] = []
        self._rows: list[dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load_data(self, columns: list[str], rows: list[dict[str, Any]]) -> None:
        """
        Replace the current dataset with new data and notify all views.

        Args:
            columns: Ordered list of column header names.
            rows:    List of dicts mapping column name to display value.
        """
        self.beginResetModel()
        self._columns = list(columns)
        self._rows = list(rows)
        self.endResetModel()

    def clear(self) -> None:
        """Remove all data."""
        self.load_data([], [])

    def row_count(self) -> int:
        return len(self._rows)

    def column_names(self) -> list[str]:
        return list(self._columns)

    def to_dict_list(self) -> list[dict[str, Any]]:
        """Return a copy of the data suitable for JSON/CSV export."""
        return [dict(row) for row in self._rows]

    # ------------------------------------------------------------------
    # QAbstractTableModel interface
    # ------------------------------------------------------------------

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._rows)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._columns)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid():
            return None

        row_idx = index.row()
        col_idx = index.column()

        if row_idx >= len(self._rows) or col_idx >= len(self._columns):
            return None

        col_name = self._columns[col_idx]
        value    = self._rows[row_idx].get(col_name)

        if role == Qt.ItemDataRole.DisplayRole:
            return _format_display(value)

        if role == Qt.ItemDataRole.ToolTipRole:
            return str(value) if value is not None else ""

        if role == Qt.ItemDataRole.ForegroundRole:
            if value is None or value == "":
                return _NONE_FG
            return _CELL_FG

        if role == Qt.ItemDataRole.BackgroundRole:
            if row_idx % 2 == 0:
                return _NORMAL_ROW_BG
            return _ALT_ROW_BG

        if role == Qt.ItemDataRole.UserRole:
            # Raw value for sorting
            return value

        return None

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                if 0 <= section < len(self._columns):
                    return self._columns[section]
            else:
                return str(section + 1)

        if role == Qt.ItemDataRole.ForegroundRole and orientation == Qt.Orientation.Horizontal:
            return _HEADER_FG

        if role == Qt.ItemDataRole.FontRole and orientation == Qt.Orientation.Horizontal:
            font = QFont()
            font.setBold(True)
            return font

        return None

    def sort(self, column: int, order: Qt.SortOrder = Qt.SortOrder.AscendingOrder) -> None:
        """In-place sort by the given column index."""
        if column >= len(self._columns) or not self._rows:
            return

        col_name = self._columns[column]
        reverse = (order == Qt.SortOrder.DescendingOrder)

        self.layoutAboutToBeChanged.emit()
        self._rows.sort(
            key=lambda row: _sort_key(row.get(col_name)),
            reverse=reverse,
        )
        self.layoutChanged.emit()

    # ------------------------------------------------------------------
    # Flags
    # ------------------------------------------------------------------

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _format_display(value: Any) -> str:
    """Convert a cell value to its display string."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "True" if value else "False"
    return str(value)


def _sort_key(value: Any) -> tuple:
    """
    Return a sort key that handles mixed types gracefully.
    Numeric values sort numerically; everything else sorts as lowercase string.
    """
    if value is None or value == "":
        return (1, "")           # empty values go to the end
    if isinstance(value, bool):
        return (0, int(value))
    if isinstance(value, (int, float)):
        return (0, value)
    try:
        return (0, float(str(value).replace("0x", ""), 16 if "0x" in str(value) else 10))
    except (ValueError, TypeError):
        pass
    return (0, str(value).lower())
