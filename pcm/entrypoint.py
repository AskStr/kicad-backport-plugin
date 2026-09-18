# -*- coding: utf-8 -*-
"""Select the supported KiCad startup path for a single PCM package."""

import re


def _host_version(pcbnew):
    """Return the running KiCad major/minor pair when pcbnew exposes it."""
    for name in ('GetMajorMinorVersion', 'GetBuildVersion', 'FullVersion', 'Version'):
        getter = getattr(pcbnew, name, None)
        try:
            match = re.search(r'(\d+)\.(\d+)', str(getter())) if callable(getter) else None
        except Exception:
            match = None
        if match:
            return tuple(map(int, match.groups()))
    return None


def _use_ipc(pcbnew):
    """KiCad 10.99+ is IPC-only; KiCad 6-10 uses pcbnew.ActionPlugin."""
    version = _host_version(pcbnew)
    return version is not None and version >= (10, 99)


try:
    import pcbnew
except ImportError:
    pass  # IPC-only hosts discover plugin.json without importing legacy code.
else:
    if not _use_ipc(pcbnew):
        from .legacy import kicad_backport_action
