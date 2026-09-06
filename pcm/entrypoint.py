# -*- coding: utf-8 -*-
"""PCM registration only; manual installs retain their original entrypoint."""

import json
import os
import re
import sys


def _use_ipc(pcbnew):
    version = None
    for name in ('GetMajorMinorVersion', 'GetBuildVersion', 'FullVersion', 'Version'):
        getter = getattr(pcbnew, name, None)
        try:
            match = re.search(r'(\d+)\.(\d+)', str(getter())) if callable(getter) else None
        except Exception:
            match = None
        if match:
            version = tuple(map(int, match.groups()))
            break
    if version is None or version < (9, 0):
        return False

    # Prefer the running host's settings manager (portable/custom installs).
    directories = []
    getter = getattr(pcbnew, 'GetSettingsManager', None)
    try:
        manager = getter() if callable(getter) else None
    except Exception:
        manager = None
    for owner in (manager, getattr(pcbnew, 'SETTINGS_MANAGER', None)):
        getter = getattr(owner, 'GetUserSettingsPath', None)
        if callable(getter):
            try:
                path = getter()
                if path:
                    directories.append(str(path))
                    break
            except Exception:
                pass
    if not directories:
        suffix = '{}.{}'.format(*version)
        base = os.environ.get('KICAD_CONFIG_HOME')
        if not base:
            home = os.path.expanduser('~')
            if sys.platform == 'win32':
                base = os.path.join(os.environ.get('APPDATA', os.path.join(home, 'AppData', 'Roaming')), 'kicad')
            elif sys.platform == 'darwin':
                base = os.path.join(home, 'Library', 'Preferences', 'kicad')
            else:
                base = os.path.join(os.environ.get('XDG_CONFIG_HOME', os.path.join(home, '.config')), 'kicad')
        base = os.path.expanduser(base)
        directories.append(base if os.path.basename(os.path.normpath(base)) == suffix else os.path.join(base, suffix))
    try:
        with open(os.path.join(directories[0], 'kicad_common.json'), encoding='utf-8') as stream:
            return json.load(stream).get('api', {}).get('enable_server') is True
    except (OSError, ValueError, TypeError, AttributeError):
        return False


try:
    import pcbnew
except ImportError:
    pass  # IPC-only hosts discover plugin.json without importing legacy code.
else:
    if not _use_ipc(pcbnew):
        from .legacy import kicad_backport_action
