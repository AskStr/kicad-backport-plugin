from __future__ import annotations

# Compatibility entry for KiCad's legacy pcbnew ActionPlugin loader.
# When this folder is placed under scripting/plugins, KiCad imports this package.
try:
    from .legacy import kicad_backport_action  # noqa: F401
except Exception:
    pass
