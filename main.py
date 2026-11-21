"""
main.py
--------
Entry point for the Volatility 3 GUI application.

Sets up the QApplication, applies the dark neon QSS theme, configures
logging, and launches the MainWindow.

Run with:
    python main.py
"""

from __future__ import annotations
import logging
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Ensure the project root is on sys.path so imports work regardless of CWD
# ---------------------------------------------------------------------------
_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# ---------------------------------------------------------------------------
# Logging configuration
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)-7s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Guard: PySide6 must be importable
# ---------------------------------------------------------------------------
try:
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import Qt, QCoreApplication, QDir
    from PySide6.QtGui import QFont, QFontDatabase
except ImportError as exc:
    print(
        f"ERROR: PySide6 is not installed.\n"
        f"  Run:  pip install PySide6\n\n"
        f"  Detail: {exc}",
        file=sys.stderr,
    )
    sys.exit(1)


# ---------------------------------------------------------------------------
# Theme loader
# ---------------------------------------------------------------------------

def _load_stylesheet(app: QApplication) -> None:
    """Load assets/main.qss and apply it to the application."""
    qss_path = _ROOT / "assets" / "main.qss"
    if qss_path.exists():
        with qss_path.open("r", encoding="utf-8") as fh:
            app.setStyleSheet(fh.read())
        log.debug("Stylesheet loaded: %s", qss_path)
    else:
        log.warning("Stylesheet not found: %s — using default Qt style", qss_path)


# ---------------------------------------------------------------------------
# Application setup
# ---------------------------------------------------------------------------

def _configure_app(app: QApplication) -> None:
    """Apply global application settings."""
    app.setApplicationName("Volatility 3 GUI")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("VolatilityGUI")

    # High-DPI is enabled by default in PySide6 6.x — no attribute needed

    # System font override — prefer Inter/Segoe UI for a crisp look
    for family in ("Inter", "Segoe UI", "Roboto", "SF Pro Display"):
        if family in QFontDatabase.families():
            app.setFont(QFont(family, 10))
            log.debug("UI font set to: %s", family)
            break


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    app = QApplication(sys.argv)

    _configure_app(app)
    _load_stylesheet(app)

    # Lazy import of the main window (keeps startup fast if vol3 not installed)
    try:
        from frontend.main_window import MainWindow
    except ImportError as exc:
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.critical(
            None,
            "Import Error",
            f"Could not load the GUI:\n\n{exc}\n\n"
            "Make sure all dependencies are installed:\n"
            "  pip install PySide6 volatility3",
        )
        sys.exit(1)

    window = MainWindow()
    window.show()

    log.info("Volatility 3 GUI started")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
