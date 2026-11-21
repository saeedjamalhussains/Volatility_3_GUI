"""
frontend/widgets/file_panel.py — Industry-Grade Evidence Loader

Premium file drop-zone with glassmorphic hover effect, animated OS badge,
and comprehensive format support. Accepts ANY file Volatility 3 can read.
"""

from __future__ import annotations
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QFrame, QSizePolicy,
)

_ALL_MEMORY_EXTS = (
    "*.raw *.img *.bin *.dd *.mem *.dump "
    "*.vmem *.vmss *.vmsn *.vmdk "
    "*.dmp *.mdmp *.hdmp *.tdmp *.hpak hiberfil.sys "
    "*.elf *.lime *.qcow2 *.bin *.hv *.mddramimage "
    "*.vhd *.vhdx *.vmware"
).split()

_BROWSE_FILTER = (
    "All Memory Images (" + " ".join(_ALL_MEMORY_EXTS) + ");;"
    "Raw / DD Images (*.raw *.img *.bin *.dd *.mem *.dump);;"
    "VMware (*.vmem *.vmss *.vmsn *.vmdk);;"
    "Windows Dumps (*.dmp *.mdmp *.hdmp);;"
    "Windows Hibernation (hiberfil.sys);;"
    "LiME (*.lime);;"
    "VirtualBox (*.elf);;"
    "QEMU / KVM (*.qcow2);;"
    "Hyper-V (*.vhd *.vhdx);;"
    "All Files (*)"
)

_OS_THEMES = {
    "Windows": ("#00aaff", "#00aaff15", "#00aaff30"),
    "Linux":   ("#00e68a", "#00e68a15", "#00e68a30"),
    "macOS":   ("#b47cff", "#b47cff15", "#b47cff30"),
    "Unknown": ("#506888", "#50688815", "#50688830"),
}


class OSBadge(QLabel):
    """Capsule-shaped OS indicator badge."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.set_os("—")
        self.setFixedHeight(26)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumWidth(90)

    def set_os(self, os_name: str):
        fg, bg, border = _OS_THEMES.get(os_name, _OS_THEMES["Unknown"])
        self.setText(os_name)
        self.setStyleSheet(f"""
            QLabel {{
                background-color: {bg};
                color: {fg};
                border: 1px solid {border};
                border-radius: 13px;
                font-weight: 700;
                font-size: 11px;
                padding: 3px 14px;
                letter-spacing: 1px;
            }}
        """)


class DropZone(QFrame):
    """Premium drop zone — accepts any file."""
    file_dropped = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setMinimumHeight(80)
        self.setMaximumHeight(100)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(4)
        layout.setContentsMargins(8, 8, 8, 8)

        icon_row = QHBoxLayout()
        icon_row.setAlignment(Qt.AlignmentFlag.AlignCenter)

        dot = QLabel("●")
        dot.setStyleSheet(
            "color: #00aaff; font-size: 8px; background: transparent;"
        )
        icon_row.addWidget(dot)

        title = QLabel("  DROP EVIDENCE FILE  ")
        title.setStyleSheet(
            "color: #506888; font-size: 10px; font-weight: 700; "
            "letter-spacing: 2px; background: transparent;"
        )
        icon_row.addWidget(title)

        dot2 = QLabel("●")
        dot2.setStyleSheet(
            "color: #00aaff; font-size: 8px; background: transparent;"
        )
        icon_row.addWidget(dot2)

        layout.addLayout(icon_row)

        sub = QLabel(".vmem  .raw  .dmp  .lime  .elf  .vmss  .qcow2  …")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setStyleSheet(
            "color: #283850; font-size: 9px; background: transparent;"
        )
        layout.addWidget(sub)
        self._apply_style(False)

    def _apply_style(self, hover: bool):
        if hover:
            self.setStyleSheet("""
                QFrame {
                    background-color: #00aaff08;
                    border: 1px dashed #00aaff50;
                    border-radius: 8px;
                }
            """)
        else:
            self.setStyleSheet("""
                QFrame {
                    background-color: #080c18;
                    border: 1px dashed #1a2540;
                    border-radius: 8px;
                }
            """)

    def dragEnterEvent(self, e: QDragEnterEvent):
        if e.mimeData().hasUrls():
            for u in e.mimeData().urls():
                if Path(u.toLocalFile()).is_file():
                    e.acceptProposedAction()
                    self._apply_style(True)
                    return
        e.ignore()

    def dragLeaveEvent(self, e):
        self._apply_style(False)

    def dropEvent(self, e: QDropEvent):
        for u in e.mimeData().urls():
            p = u.toLocalFile()
            if Path(p).is_file():
                self.file_dropped.emit(p)
                break
        self._apply_style(False)

    def mousePressEvent(self, e):
        # Click to browse
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Evidence File", "", _BROWSE_FILTER)
        if path:
            self.file_dropped.emit(path)


class FilePanel(QWidget):
    """Evidence file loader panel."""
    file_loaded = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_path = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self._drop_zone = DropZone()
        self._drop_zone.file_dropped.connect(self._on_file_selected)
        layout.addWidget(self._drop_zone)

        # File info row
        info_card = QFrame()
        info_card.setObjectName("cardInner")
        info_layout = QVBoxLayout(info_card)
        info_layout.setContentsMargins(10, 8, 10, 8)
        info_layout.setSpacing(4)

        self._file_name = QLabel("No evidence loaded")
        self._file_name.setStyleSheet(
            "color: #283850; font-size: 12px; font-weight: 600; "
            "background: transparent;"
        )
        self._file_name.setWordWrap(True)
        info_layout.addWidget(self._file_name)

        self._file_size = QLabel("")
        self._file_size.setStyleSheet(
            "color: #1e2d40; font-size: 10px; background: transparent;"
        )
        info_layout.addWidget(self._file_size)

        layout.addWidget(info_card)

        # OS row
        os_row = QHBoxLayout()
        os_row.setSpacing(6)

        os_label = QLabel("OS")
        os_label.setStyleSheet(
            "color: #374560; font-size: 10px; font-weight: 700; "
            "letter-spacing: 1px; background: transparent;"
        )
        self._os_badge = OSBadge()

        os_row.addWidget(os_label)
        os_row.addWidget(self._os_badge)
        os_row.addStretch()
        layout.addLayout(os_row)

    def set_os(self, os_name: str):
        self._os_badge.set_os(os_name)

    def current_path(self):
        return self._current_path

    def _on_file_selected(self, path: str):
        self._current_path = path
        p = Path(path)
        self._file_name.setText(p.name)
        self._file_name.setStyleSheet(
            "color: #c0cce0; font-size: 12px; font-weight: 600; "
            "background: transparent;"
        )
        self._file_name.setToolTip(path)

        size = p.stat().st_size
        for unit in ("B", "KB", "MB", "GB"):
            if abs(size) < 1024:
                self._file_size.setText(f"{size:.1f} {unit}" if unit != "B" else f"{size} {unit}")
                break
            size /= 1024
        self._file_size.setStyleSheet(
            "color: #506888; font-size: 10px; background: transparent;"
        )

        self._os_badge.set_os("—")
        self.file_loaded.emit(path)
