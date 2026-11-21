"""
utils/threading.py
------------------
Reusable async worker infrastructure for the Volatility GUI.
Provides BaseWorker (QThread subclass) and WorkerSignals for consistent
signal-based communication between background threads and the Qt UI.
"""

from __future__ import annotations
import traceback
from PySide6.QtCore import QObject, QThread, Signal


# ---------------------------------------------------------------------------
# Shared signal container
# ---------------------------------------------------------------------------

class WorkerSignals(QObject):
    """Defines all signals emitted by workers running in background threads."""

    # (percentage 0-100, description string)
    progress = Signal(int, str)

    # (level string, message string)  e.g. ("INFO", "Scanning...")
    log_message = Signal(str, str)

    # (list[dict] rows, list[str] column_names)
    result_ready = Signal(list, list)

    # Full traceback string on failure
    error = Signal(str)

    # Emitted when the worker finishes regardless of success/failure
    finished = Signal()


# ---------------------------------------------------------------------------
# Base worker
# ---------------------------------------------------------------------------

class BaseWorker(QThread):
    """
    Base class for long-running background tasks.

    Subclasses must implement _run().  Signals are exposed via self.signals.

    Usage::

        class MyWorker(BaseWorker):
            def _run(self):
                self.signals.progress.emit(50, "Halfway...")
                result = do_work()
                self.signals.result_ready.emit(result, columns)
    """

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.signals = WorkerSignals()
        self._cancelled = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def cancel(self) -> None:
        """Request cancellation.  _run() should check self._cancelled."""
        self._cancelled = True

    # ------------------------------------------------------------------
    # QThread override
    # ------------------------------------------------------------------

    def run(self) -> None:
        """Entry point called by QThread.start()."""
        try:
            self._run()
        except Exception:
            tb = traceback.format_exc()
            self.signals.log_message.emit("ERROR", tb)
            self.signals.error.emit(tb)
        finally:
            self.signals.finished.emit()

    # ------------------------------------------------------------------
    # Subclass interface
    # ------------------------------------------------------------------

    def _run(self) -> None:  # pragma: no cover
        raise NotImplementedError("BaseWorker subclasses must implement _run()")

    # ------------------------------------------------------------------
    # Helpers for subclasses
    # ------------------------------------------------------------------

    def _emit_log(self, level: str, message: str) -> None:
        self.signals.log_message.emit(level, message)

    def _emit_progress(self, pct: int, description: str) -> None:
        self.signals.progress.emit(pct, description)
