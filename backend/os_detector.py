"""
backend/os_detector.py
----------------------
Detect the operating system of a loaded memory image by silently attempting
to run OS-specific Volatility 3 info plugins.

Returns one of: "Windows" | "Linux" | "macOS" | "Unknown"
"""

from __future__ import annotations
import logging
from typing import TYPE_CHECKING, Callable

log = logging.getLogger(__name__)

if TYPE_CHECKING:
    from backend.volatility_runner import VolatilityRunner, ProgressCallback


# ---------------------------------------------------------------------------
# Probe definitions — ordered by prevalence
# ---------------------------------------------------------------------------

_PROBES: list[tuple[str, str]] = [
    ("windows.info.Info",       "Windows"),
    ("linux.lsof.Lsof",        "Linux"),
    ("mac.pslist.PsList",       "macOS"),
]


def detect_os(
    runner: "VolatilityRunner",
    progress_callback: "ProgressCallback | None" = None,
) -> str:
    """
    Attempt OS detection by running lightweight probes against the loaded image.

    Args:
        runner:            An already-loaded VolatilityRunner instance.
        progress_callback: Optional callable(pct, description) for UI feedback.

    Returns:
        OS name string or "Unknown".
    """
    try:
        from volatility3 import framework as vol_framework
        import volatility3.plugins as vol_plugins
        from volatility3.framework import list_plugins, import_files
    except ImportError:
        log.warning("volatility3 not available — OS detection skipped")
        return "Unknown"

    # Make sure plugins are imported
    try:
        import_files(vol_plugins, True)
    except Exception:
        pass

    plugin_map = list_plugins()

    for plugin_name, os_name in _PROBES:
        plugin_cls = plugin_map.get(plugin_name)
        if plugin_cls is None:
            log.debug("Probe plugin %r not found — skipping", plugin_name)
            continue

        log.debug("Probing OS with %s …", plugin_name)
        if progress_callback:
            progress_callback(10, f"Detecting OS: trying {os_name} …")

        try:
            columns, rows = runner.run_plugin(
                plugin_cls,
                config_overrides=None,
                progress_callback=None,   # suppress noisy progress during probing
            )
            if rows:            # any output → OS confirmed
                log.info("OS detected: %s (via %s)", os_name, plugin_name)
                if progress_callback:
                    progress_callback(100, f"Detected OS: {os_name}")
                return os_name
        except Exception as exc:
            log.debug("OS probe %s failed: %s", plugin_name, exc)
            continue

    log.info("OS detection exhausted all probes — returning Unknown")
    return "Unknown"
