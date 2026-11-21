"""
backend/plugin_manager.py
--------------------------
Plugin discovery, registry, and metadata for the Volatility GUI.

Wraps volatility3.framework's plugin enumeration API to provide
a clean interface for the GUI plugin list and options form.

Handles ALL Volatility 3 requirement types:
  StringRequirement   → str input
  IntRequirement      → int spinbox
  BooleanRequirement  → checkbox
  FloatRequirement    → float spinbox
  ChoiceRequirement   → combobox
  ListRequirement     → comma-separated input  (element_type preserved)
  URIRequirement      → file path input + browse button
  TranslationLayerRequirement / SymbolTableRequirement / ModuleRequirement
                      → shown as informational read-only row (automagic handles)
  VersionRequirement  → skipped (internal framework wiring)
"""

from __future__ import annotations
import inspect
import logging
from typing import Any

log = logging.getLogger(__name__)

try:
    import volatility3.plugins as vol_plugins
    from volatility3.framework import import_files, list_plugins
    from volatility3.framework.interfaces.configuration import (
        RequirementInterface,
        SimpleTypeRequirement,
    )
    from volatility3.framework.configuration import requirements as vol_reqs
    VOL3_AVAILABLE = True
except ImportError:
    VOL3_AVAILABLE = False


# ---------------------------------------------------------------------------
# RequirementInfo
# ---------------------------------------------------------------------------

class RequirementInfo:
    """Structured description of a single plugin requirement.

    req_type values:
        "str"       — text input
        "int"       — integer spinbox
        "bool"      — checkbox
        "float"     — float spinbox
        "choice"    — combobox from choices list
        "list_int"  — comma-separated integers
        "list_str"  — comma-separated strings
        "uri"       — file path / URI input
        "info"      — read-only informational row (automagic handles it)
    """

    def __init__(
        self,
        name: str,
        description: str,
        req_type: str,
        optional: bool,
        default: Any = None,
        choices: list[str] | None = None,
        element_type: str = "str",   # for list_* types
    ) -> None:
        self.name = name
        self.description = description
        self.req_type = req_type
        self.optional = optional
        self.default = default
        self.choices = choices or []
        self.element_type = element_type   # "int" | "str" | "float"

    def __repr__(self) -> str:
        return (
            f"RequirementInfo(name={self.name!r}, type={self.req_type!r}, "
            f"optional={self.optional})"
        )


# ---------------------------------------------------------------------------
# PluginManager
# ---------------------------------------------------------------------------

class PluginManager:
    """
    Loads and catalogues all available Volatility 3 plugins.

    Usage::

        pm = PluginManager()
        pm.load_all()
        plugins = pm.get_plugins()           # dict[name, cls]
        groups  = pm.group_by_os()           # dict[os, list[name]]
        reqs    = pm.get_requirements(cls)   # list[RequirementInfo]
    """

    def __init__(self) -> None:
        self._plugins: dict[str, type] = {}
        self._loaded: bool = False
        self._req_cache: dict[str, list[RequirementInfo]] = {}

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def load_all(self) -> list[str]:
        """Import all plugins from the standard Volatility plugin directories."""
        if not VOL3_AVAILABLE:
            log.warning("volatility3 not installed — no plugins available")
            self._loaded = True
            return []

        failures = import_files(vol_plugins, True)
        self._plugins = dict(list_plugins())
        self._loaded = True
        log.info("Loaded %d plugins (%d import failures)", len(self._plugins), len(failures))
        return [str(f) for f in failures]

    def ensure_loaded(self) -> None:
        if not self._loaded:
            self.load_all()

    # ------------------------------------------------------------------
    # Query API
    # ------------------------------------------------------------------

    def get_plugins(self) -> dict[str, type]:
        self.ensure_loaded()
        return dict(self._plugins)

    def group_by_os(self) -> dict[str, list[str]]:
        """Group plugin names by target OS: Windows / Linux / macOS / Other."""
        self.ensure_loaded()
        groups: dict[str, list[str]] = {
            "Windows": [],
            "Linux":   [],
            "macOS":   [],
            "Other":   [],
        }
        for name in sorted(self._plugins):
            lower = name.lower()
            if lower.startswith("windows."):
                groups["Windows"].append(name)
            elif lower.startswith("linux."):
                groups["Linux"].append(name)
            elif lower.startswith("mac."):
                groups["macOS"].append(name)
            else:
                groups["Other"].append(name)
        return groups

    def get_requirements(self, plugin_cls: type) -> list[RequirementInfo]:
        """
        Return a list of RequirementInfo for every user-relevant requirement.

        Includes informational rows for automagic-handled requirements so
        users understand what symbol tables / layers the plugin needs.
        """
        cache_key = f"{plugin_cls.__module__}.{plugin_cls.__name__}"
        if cache_key in self._req_cache:
            return self._req_cache[cache_key]

        if not VOL3_AVAILABLE:
            return []

        result: list[RequirementInfo] = []
        try:
            raw: list[Any] = plugin_cls.get_requirements()
        except Exception as exc:
            log.debug("Could not get requirements for %s: %s", plugin_cls.__name__, exc)
            return []

        for req in raw:
            info = _parse_requirement(req)
            if info is not None:
                result.append(info)

        self._req_cache[cache_key] = result
        return result

    def get_description(self, plugin_cls: type) -> str:
        """Return the first non-empty line of the plugin's docstring."""
        doc = inspect.getdoc(plugin_cls) or ""
        for line in doc.splitlines():
            line = line.strip()
            if line:
                return line
        return plugin_cls.__name__

    def find_plugin(self, name: str) -> type | None:
        self.ensure_loaded()
        return self._plugins.get(name)


# ---------------------------------------------------------------------------
# Requirement parsing — handles ALL types
# ---------------------------------------------------------------------------

# Types that are wired internally / should only be shown as info rows
_INFO_TYPES: frozenset[str] = frozenset({
    "TranslationLayerRequirement",
    "SymbolTableRequirement",
    "SymbolFilesRequirement",
    "ModuleRequirement",
})

# Types that the framework uses internally and the user never sees
_SKIP_TYPES: frozenset[str] = frozenset({
    "VersionRequirement",
    "PluginRequirement",
    "ConstructableRequirementInterface",
})


def _parse_requirement(req: Any) -> RequirementInfo | None:
    """Convert a Volatility RequirementInterface into a RequirementInfo.

    Returns None only for pure internal/framework requirements the user
    should never be aware of.
    """
    type_name = type(req).__name__

    # Completely skip internal wiring requirements
    if type_name in _SKIP_TYPES:
        return None

    name: str        = getattr(req, "name", "unknown")
    description: str = getattr(req, "description", "") or ""
    optional: bool   = getattr(req, "optional", True)
    default: Any     = getattr(req, "default", None)

    # ------------------------------------------------------------------
    # Informational rows for automagic-handled complex requirements
    # ------------------------------------------------------------------
    if type_name in _INFO_TYPES:
        label = _info_label(type_name, name)
        return RequirementInfo(
            name=name,
            description=label,
            req_type="info",
            optional=optional,
            default=None,
        )

    if not VOL3_AVAILABLE:
        return RequirementInfo(name=name, description=description,
                               req_type="str", optional=optional, default=default)

    # ------------------------------------------------------------------
    # URI requirement (file path / ISF path)
    # ------------------------------------------------------------------
    if hasattr(vol_reqs, "URIRequirement") and isinstance(req, vol_reqs.URIRequirement):
        return RequirementInfo(
            name=name,
            description=description or "File URI / path",
            req_type="uri",
            optional=optional,
            default=str(default) if default else None,
        )

    # ------------------------------------------------------------------
    # List requirement — detect element type
    # ------------------------------------------------------------------
    if hasattr(vol_reqs, "ListRequirement") and isinstance(req, vol_reqs.ListRequirement):
        element_type = _detect_list_element_type(req)
        return RequirementInfo(
            name=name,
            description=description or f"Comma-separated {element_type} values",
            req_type=f"list_{element_type}",
            optional=optional,
            default=default,
            element_type=element_type,
        )

    # ------------------------------------------------------------------
    # Simple scalar types
    # ------------------------------------------------------------------
    if hasattr(vol_reqs, "BooleanRequirement") and isinstance(req, vol_reqs.BooleanRequirement):
        return RequirementInfo(name=name, description=description, req_type="bool",
                               optional=optional, default=default)

    if hasattr(vol_reqs, "IntRequirement") and isinstance(req, vol_reqs.IntRequirement):
        return RequirementInfo(name=name, description=description, req_type="int",
                               optional=optional, default=default)

    if hasattr(vol_reqs, "FloatRequirement") and isinstance(req, vol_reqs.FloatRequirement):
        return RequirementInfo(name=name, description=description, req_type="float",
                               optional=optional, default=default)

    if hasattr(vol_reqs, "ChoiceRequirement") and isinstance(req, vol_reqs.ChoiceRequirement):
        choices: list[str] = []
        try:
            choices = list(req.choices) if req.choices else []
        except Exception:
            pass
        return RequirementInfo(name=name, description=description, req_type="choice",
                               optional=optional, default=default, choices=choices)

    if hasattr(vol_reqs, "StringRequirement") and isinstance(req, vol_reqs.StringRequirement):
        return RequirementInfo(name=name, description=description, req_type="str",
                               optional=optional, default=default)

    # Fallback: treat as plain string so nothing silently disappears
    return RequirementInfo(name=name, description=description, req_type="str",
                           optional=optional, default=str(default) if default else None)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _detect_list_element_type(req: Any) -> str:
    """Determine whether a ListRequirement holds ints, floats, or strings."""
    try:
        et = req.element_type
        if et is None:
            return "str"
        name = getattr(et, "__name__", "") or type(et).__name__
        if "Int" in name or name == "int":
            return "int"
        if "Float" in name or name == "float":
            return "float"
    except Exception:
        pass
    return "str"


def _info_label(type_name: str, req_name: str) -> str:
    """Return a human-readable description for an automagic-handled requirement."""
    labels = {
        "TranslationLayerRequirement": "Memory layer  (handled by automagic)",
        "SymbolTableRequirement":       "Symbol table  (auto-downloaded or from symbols/)",
        "SymbolFilesRequirement":       "Symbol files  (from symbols/ directory)",
        "ModuleRequirement":            "Kernel module (resolved by automagic)",
    }
    return labels.get(type_name, f"{req_name}  (handled automatically)")
