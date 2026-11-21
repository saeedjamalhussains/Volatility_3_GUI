"""
backend/plugin_runner.py
------------------------
QThread-based worker that runs a Volatility plugin asynchronously.

Extends BaseWorker from utils.threading.  Bridges Volatility's
progress_callback → Qt signals so the UI stays live during analysis.
"""

from __future__ import annotations
import logging
from typing import Any

from PySide6.QtCore import QObject

from utils.threading import BaseWorker
from backend.volatility_runner import VolatilityRunner

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# OS Detection Worker
# ---------------------------------------------------------------------------

class OSDetectWorker(BaseWorker):
    """
    Detect the operating system of the loaded memory image in a background thread.

    Emits:
        result_ready([detected_os_string], ["os"])  — single-row "result"
        progress(pct, description)
        error(traceback_string)
        finished()
    """

    def __init__(self, runner: VolatilityRunner, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._runner = runner

    def _run(self) -> None:
        self._emit_progress(0, "Starting OS detection …")
        self._emit_log("INFO", "Probing memory image for OS fingerprint …")

        detected = self._runner.detect_os(
            progress_callback=self._emit_progress  # type: ignore[arg-type]
        )

        self._emit_log("INFO", f"OS detection complete: {detected}")
        self._emit_progress(100, f"Detected OS: {detected}")
        # Emit as a minimal result so callers can use the standard signal
        self.signals.result_ready.emit([{"os": detected}], ["os"])


# ---------------------------------------------------------------------------
# Plugin Runner Worker
# ---------------------------------------------------------------------------

class PluginWorker(BaseWorker):
    """
    Run a Volatility 3 plugin against the loaded memory image.

    Args:
        runner:           An already-loaded VolatilityRunner.
        plugin_cls:       The plugin class to execute.
        config_overrides: Extra configuration values from the options form.

    Emits:
        progress(pct, description)
        log_message(level, message)
        result_ready(rows, columns)
        error(traceback_string)
        finished()
    """

    def __init__(
        self,
        runner: VolatilityRunner,
        plugin_cls: type,
        config_overrides: dict[str, Any] | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._runner = runner
        self._plugin_cls = plugin_cls
        self._config_overrides = config_overrides or {}

    # ------------------------------------------------------------------
    # Worker implementation
    # ------------------------------------------------------------------

    def _run(self) -> None:
        plugin_name = self._plugin_cls.__name__
        self._emit_log("INFO", f"Starting plugin: {plugin_name}")
        self._emit_progress(0, f"Running {plugin_name} …")

        columns, rows = self._runner.run_plugin(
            self._plugin_cls,
            config_overrides=self._config_overrides,
            progress_callback=self._progress_bridge,
        )

        self._emit_progress(100, f"Complete — {len(rows)} rows returned")
        self._emit_log(
            "INFO",
            f"Plugin {plugin_name} finished: {len(rows)} rows, {len(columns)} columns",
        )
        self.signals.result_ready.emit(rows, columns)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _progress_bridge(self, pct: float | None, description: str) -> None:
        """Bridge Volatility's progress callback to Qt signals."""
        if self._cancelled:
            raise InterruptedError("Plugin cancelled by user")
        safe_pct = int(pct) if pct is not None else 0
        self._emit_progress(safe_pct, description)
