from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

try:
    import pcbnew
except Exception:
    pcbnew = None

try:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "plugin"))
    from i18n import detect_language, translate
except Exception:
    detect_language = lambda: "en"
    translate = lambda key, language=None: {
        "action_name": "Create KiCad Backport",
        "action_category": "KiCad Backport",
        "action_description": "Create a compatibility copy of a KiCad project or file.",
    }.get(key, key)


def plugin_root() -> Path:
    here = Path(__file__).resolve()
    if here.parent.name == "legacy":
        return here.parents[1]
    return here.parent


def launch_gui() -> None:
    root = plugin_root()
    launcher = root / "plugin" / "plugin.py"
    if not launcher.exists():
        raise RuntimeError("plugin/plugin.py was not found")

    sys.path.insert(0, str(launcher.parent))
    spec = importlib.util.spec_from_file_location("kicad_backport_gui", launcher)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load plugin/plugin.py")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    result = module.run_gui()
    if result not in (None, 0):
        raise RuntimeError(f"KiCad Backport exited with code {result}")


if pcbnew is not None:

    class KiCadBackportAction(pcbnew.ActionPlugin):
        def defaults(self):
            lang = detect_language()
            self.name = translate("action_name", lang)
            self.category = translate("action_category", lang)
            self.description = translate("action_description", lang)
            self.show_toolbar_button = True
            icon = plugin_root() / "assets" / "icons" / "backport-light-32.png"
            if icon.exists():
                self.icon_file_name = str(icon)

        def Run(self):
            launch_gui()


    KiCadBackportAction().register()
