"""
backend/exporters.py
--------------------
Export helpers for saving plugin results as JSON or CSV.
"""

from __future__ import annotations
import csv
import json
import logging
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)


def export_json(path: str | Path, columns: list[str], rows: list[dict[str, Any]]) -> None:
    """Write *rows* to *path* as a JSON array.

    Args:
        path:    Destination file path.
        columns: Ordered list of column names (used to sanity-check rows).
        rows:    List of dicts mapping column name → value.
    """
    path = Path(path)
    data = {
        "columns": columns,
        "rows": rows,
        "total": len(rows),
    }
    with path.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, default=_json_default)
    log.info("Exported %d rows → %s (JSON)", len(rows), path)


def export_csv(path: str | Path, columns: list[str], rows: list[dict[str, Any]]) -> None:
    """Write *rows* to *path* as a CSV file.

    Args:
        path:    Destination file path.
        columns: Ordered column headers.
        rows:    List of dicts mapping column name → value.
    """
    path = Path(path)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: _csv_safe(v) for k, v in row.items()})
    log.info("Exported %d rows → %s (CSV)", len(rows), path)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _json_default(obj: Any) -> Any:
    """Fallback serialiser for types json.dump doesn't know."""
    try:
        return str(obj)
    except Exception:
        return None


def _csv_safe(value: Any) -> str:
    """Convert a value to a CSV-safe string."""
    if value is None:
        return ""
    return str(value)
