"""
frontend/widgets/plugin_panel.py — Industry-Grade Plugin Browser

Searchable, OS-grouped tree with live filter, count badges, and
smooth selection feedback.
"""

from __future__ import annotations
from typing import Any

from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont, QColor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QTreeWidget, QTreeWidgetItem, QLineEdit, QLabel,
)

_CATEGORY_ORDER = ["Windows", "Linux", "macOS", "Other"]
_CATEGORY_META = {
    "Windows": ("W", "#00aaff"),
    "Linux":   ("L", "#00e68a"),
    "macOS":   ("M", "#b47cff"),
    "Other":   ("O", "#506888"),
}


class PluginPanel(QWidget):
    """Searchable plugin browser with OS grouping."""
    plugin_selected = Signal(str, object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._plugin_map = {}
        self._category_items = {}
        self._setup_ui()
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(150)
        self._search_timer.timeout.connect(self._apply_filter)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # Search
        self._search = QLineEdit()
        self._search.setPlaceholderText("Search plugins …")
        self._search.setClearButtonEnabled(True)
        self._search.textChanged.connect(lambda _: self._search_timer.start())
        layout.addWidget(self._search)

        # Count
        self._count = QLabel("—")
        self._count.setStyleSheet(
            "color: #283850; font-size: 10px; background: transparent;"
        )
        layout.addWidget(self._count)

        # Tree
        self._tree = QTreeWidget()
        self._tree.setHeaderHidden(True)
        self._tree.setAlternatingRowColors(True)
        self._tree.setExpandsOnDoubleClick(False)
        self._tree.setAnimated(True)
        self._tree.setIndentation(14)
        self._tree.setRootIsDecorated(True)
        self._tree.itemDoubleClicked.connect(self._on_double_click)
        self._tree.itemClicked.connect(self._on_click)
        layout.addWidget(self._tree)

    def load_plugins(self, groups, plugin_map, descriptions=None):
        self._tree.clear()
        self._category_items.clear()
        self._plugin_map.clear()
        descriptions = descriptions or {}
        total = 0

        for cat in _CATEGORY_ORDER:
            names = groups.get(cat, [])
            if not names:
                continue

            letter, color = _CATEGORY_META.get(cat, ("?", "#506888"))
            cat_item = QTreeWidgetItem([f"  {cat.upper()}   ({len(names)})"])
            cat_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            cat_item.setForeground(0, QColor(color))
            f = QFont()
            f.setBold(True)
            f.setPointSize(9)
            cat_item.setFont(0, f)
            cat_item.setData(0, Qt.ItemDataRole.UserRole, None)
            self._tree.addTopLevelItem(cat_item)
            self._category_items[cat] = cat_item

            for name in sorted(names):
                short = name.split(".")[-1]
                desc = descriptions.get(name, "")
                cls = plugin_map.get(name)
                leaf = QTreeWidgetItem([short])
                leaf.setToolTip(0, f"{name}\n{desc}" if desc else name)
                leaf.setData(0, Qt.ItemDataRole.UserRole, (name, cls))
                cat_item.addChild(leaf)
                self._plugin_map[short] = (name, cls)
                total += 1

            cat_item.setExpanded(True)

        self._count.setText(f"{total} available")

    def clear(self):
        self._tree.clear()
        self._plugin_map.clear()
        self._count.setText("—")

    def _apply_filter(self):
        q = self._search.text().strip().lower()
        if not q:
            for i in range(self._tree.topLevelItemCount()):
                cat = self._tree.topLevelItem(i)
                cat.setHidden(False)
                for j in range(cat.childCount()):
                    cat.child(j).setHidden(False)
                cat.setExpanded(True)
            return

        for i in range(self._tree.topLevelItemCount()):
            cat = self._tree.topLevelItem(i)
            visible = False
            for j in range(cat.childCount()):
                child = cat.child(j)
                match = q in child.text(0).lower()
                child.setHidden(not match)
                if match:
                    visible = True
            cat.setHidden(not visible)
            cat.setExpanded(visible)

    def _on_double_click(self, item, _col):
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if data is not None:
            name, cls = data
            if cls is not None:
                self.plugin_selected.emit(name, cls)

    def _on_click(self, item, _col):
        if item.childCount() > 0:
            item.setExpanded(not item.isExpanded())
