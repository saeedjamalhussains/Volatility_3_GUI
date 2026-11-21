"""
backend/volatility_runner.py
----------------------------
Core Volatility 3 integration engine.

Wraps the Volatility 3 Python API (not subprocess):
  Context → automagic → construct_plugin → .run() → TreeGrid → rows

Supports all memory image formats Volatility 3 can read — format detection
is handled by Volatility's automagic layer-stacker (not by file extension).
"""

from __future__ import annotations
import logging
import traceback
from pathlib import Path
from typing import Any, Callable

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Volatility 3 imports — wrapped so the GUI can still open without vol installed
# ---------------------------------------------------------------------------
try:
    import volatility3.framework as framework
    import volatility3.plugins as vol_plugins
    from volatility3 import framework as vol_framework
    from volatility3.framework import automagic, constants, contexts, interfaces, plugins
    from volatility3.framework.configuration import requirements
    from volatility3.framework.interfaces import renderers as iface_renderers
    from volatility3.framework.renderers import format_hints
    VOL3_AVAILABLE = True
except ImportError:
    VOL3_AVAILABLE = False
    log.warning("volatility3 not installed — running in demo mode")


# ---------------------------------------------------------------------------
# Public type aliases
# ---------------------------------------------------------------------------
Row = dict[str, Any]
ColumnList = list[str]
ProgressCallback = Callable[[float | None, str], None]


# ---------------------------------------------------------------------------
# VolatilityRunner
# ---------------------------------------------------------------------------

class VolatilityRunner:
    """
    Manages a single Volatility 3 analysis session.

    Lifecycle::

        runner = VolatilityRunner()
        runner.load_image("/path/to/mem.vmem")           # creates context
        columns, rows = runner.run_plugin(plugin_cls, {}) # run a plugin
    """

    BASE_CONFIG_PATH = "plugins"

    def __init__(self) -> None:
        self._context: Any = None          # volatility3 Context
        self._image_path: Path | None = None
        self._plugins_loaded: bool = False

    # ------------------------------------------------------------------
    # Session management
    # ------------------------------------------------------------------

    def load_image(self, image_path: str | Path) -> None:
        """
        Prepare a fresh context for the given memory image.

        This does NOT run automagic yet — that happens inside run_plugin
        so that progress reporting works correctly.
        """
        if not VOL3_AVAILABLE:
            raise RuntimeError(
                "volatility3 is not installed.\n\n"
                "Run:  pip install volatility3"
            )

        self._image_path = Path(image_path)
        if not self._image_path.exists():
            raise FileNotFoundError(f"Memory image not found: {self._image_path}")

        # Ensure plugins are loaded from all standard paths
        if not self._plugins_loaded:
            failures = vol_framework.import_files(vol_plugins, True)
            if failures:
                log.debug("Plugin import failures (usually harmless): %s", failures)
            self._plugins_loaded = True

        # Fresh context for each image
        self._context = contexts.Context()
        self._context.config[
            "automagic.LayerStacker.single_location"
        ] = self._image_path.as_uri()

        log.info("Image loaded: %s", self._image_path)

    def is_ready(self) -> bool:
        """Return True if an image has been loaded."""
        return self._context is not None and self._image_path is not None

    # ------------------------------------------------------------------
    # Plugin execution
    # ------------------------------------------------------------------

    def run_plugin(
        self,
        plugin_cls: type,
        config_overrides: dict[str, Any] | None = None,
        progress_callback: ProgressCallback | None = None,
    ) -> tuple[ColumnList, list[Row]]:
        """
        Run *plugin_cls* against the loaded memory image.

        Args:
            plugin_cls:       The Volatility 3 plugin class to run.
            config_overrides: Extra config values keyed by requirement name.
            progress_callback: Optional callable(pct, description).

        Returns:
            (columns, rows) — column names and list of row dicts.
        """
        if not self.is_ready():
            raise RuntimeError("No memory image loaded. Call load_image() first.")

        # Make a clean copy of the context so repeated runs don't interfere
        ctx = self._fresh_context()

        # Apply any user-supplied overrides
        # Only push non-None, non-empty values so we don't override Volatility defaults
        if config_overrides:
            for key, value in config_overrides.items():
                if value is None:
                    continue
                # Skip empty strings and empty lists
                if isinstance(value, (str, list)) and not value:
                    continue
                config_path = interfaces.configuration.path_join(
                    self.BASE_CONFIG_PATH, plugin_cls.__name__, key
                )
                ctx.config[config_path] = value
                log.debug("Config override: %s = %r", config_path, value)

        # Build progress callback bridging Volatility's API → our callback
        vol_progress = self._make_progress_callback(progress_callback)

        # Select automagics appropriate for this plugin
        available = automagic.available(ctx)
        chosen = automagic.choose_automagic(available, plugin_cls)

        # Construct and run the plugin (automagic runs here)
        try:
            constructed = plugins.construct_plugin(
                ctx,
                chosen,
                plugin_cls,
                self.BASE_CONFIG_PATH,
                vol_progress,
                None,  # file_consumer — not needed
            )
        except Exception as exc:
            fmt = self._image_path.suffix.lower() if self._image_path else ""
            hint = (
                f"\n\nHint: Tried to read '{fmt}' format. Volatility may need additional "
                f"symbol tables or the file format may not be supported."
                if fmt else ""
            )
            raise RuntimeError(f"Plugin construction failed: {exc}{hint}") from exc

        try:
            grid = constructed.run()
        except Exception as exc:
            raise RuntimeError(f"Plugin execution failed: {exc}") from exc

        columns, rows = self._parse_treegrid(grid)
        log.info(
            "Plugin %s completed: %d rows, %d columns",
            plugin_cls.__name__,
            len(rows),
            len(columns),
        )
        return columns, rows

    # ------------------------------------------------------------------
    # OS detection
    # ------------------------------------------------------------------

    def detect_os(self, progress_callback: ProgressCallback | None = None) -> str:
        """
        Try to detect the operating system of the loaded memory image.

        Tries windows → linux → mac plugins in order and returns the first
        that succeeds.  Returns "Unknown" on failure.
        """
        if not self.is_ready():
            return "Unknown"

        from backend.os_detector import detect_os  # local import avoids circularity
        return detect_os(self, progress_callback)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _fresh_context(self) -> Any:
        """Return a shallow copy of the base context for one plugin run."""
        ctx = contexts.Context()
        # Copy existing config tree entries
        for key in self._context.config:
            ctx.config[key] = self._context.config[key]
        return ctx

    @staticmethod
    def _make_progress_callback(cb: ProgressCallback | None):
        """Return a Volatility-compatible progress callback."""
        if cb is None:
            return lambda pct, desc: None

        def _vol_cb(pct, desc=""):
            safe_pct = int(pct) if pct is not None else 0
            cb(safe_pct, desc or "")

        return _vol_cb

    @staticmethod
    def _parse_treegrid(grid: Any) -> tuple[ColumnList, list[Row]]:
        """
        Walk a Volatility TreeGrid and return (column_names, rows).

        We flatten the tree — child rows are included without hierarchy for
        the table display.  Values that are absent/unreadable are shown as
        an empty string.
        """
        columns: ColumnList = [col.name for col in grid.columns]
        rows: list[Row] = []

        def visitor(node: Any, _acc: None) -> None:
            row: Row = {}
            for idx, col in enumerate(grid.columns):
                try:
                    value = node.values[idx]
                    row[col.name] = _render_value(value)
                except Exception:
                    row[col.name] = ""
            rows.append(row)
            return None

        try:
            grid.populate(visitor, None)
        except Exception as exc:
            log.warning("TreeGrid population error: %s", exc)

        return columns, rows


# ---------------------------------------------------------------------------
# Value rendering helpers
# ---------------------------------------------------------------------------

def _render_value(value: Any) -> Any:
    """Convert a Volatility TreeGrid cell value to a Python-native type."""
    if value is None:
        return ""

    if not VOL3_AVAILABLE:
        return str(value)

    # Absent values
    try:
        if isinstance(value, iface_renderers.BaseAbsentValue):
            return ""
    except Exception:
        pass

    # Format hints — display as hex where appropriate
    try:
        if isinstance(value, format_hints.Hex):
            return hex(int(value))
        if isinstance(value, format_hints.HexBytes):
            return value.hex()
        if isinstance(value, format_hints.Bin):
            return bin(int(value))
    except Exception:
        pass

    # datetime
    try:
        from datetime import datetime
        if isinstance(value, datetime):
            return value.isoformat()
    except Exception:
        pass

    # bytes → hex string
    if isinstance(value, (bytes, bytearray)):
        return value.hex()

    # All other types — str fallback
    return value
