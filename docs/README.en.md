# KiCad Backport

Copyright (C) askstar

Version 0.4.0

KiCad Backport creates a compatibility copy of a KiCad project or file for an
older KiCad target version. It supports practical downgrade and upgrade
workflows across modern S-expression files and KiCad 5-era legacy files. The
original project is not overwritten.

The converter core is pure Python. KiCad 5-era Python launches the GUI through
an external Python 3 interpreter so old KiCad installations can still use the
current conversion engine.

## Current Capabilities

- Converts whole project folders or individual KiCad files.
- Handles board, schematic, symbol-library, footprint, worksheet, design-rule,
  project, and legacy project/library/schematic files where a conversion path
  exists.
- Converts modern `.kicad_sch`, `.kicad_sym`, and `.kicad_pro` files to KiCad
  5-era `.sch`, `.lib` / `.dcm`, and `.pro` files.
- Upgrades legacy `.sch`, `.lib`, `.dcm`, and `.pro` files to modern KiCad
  files for newer targets.
- Preserves project-local symbol libraries, normalizes library tables, rebuilds
  modern schematic hierarchy instances when needed, and writes compatible
  project-local `.kicad_prl` files for V6/V7/V8 board outputs.
- Writes a JSON conversion report when requested or launched from the GUI.

## Supported Targets

GUI targets: KiCad 10, 9, 8, 7, 6, 5.1, 5.0, and 4.

The conversion core also accepts supported raw numeric format targets such as
`20260603` and `20260521`.

Supported input families include current KiCad 10.99 nightly files, KiCad 10
through KiCad 5 files, and legacy `.sch`, `.lib`, `.dcm`, and `.pro` files.

## Language

The plugin follows the language selected in KiCad when possible. It checks
KiCad 5-style configuration files, common KiCad language environment variables,
and finally the operating-system UI language.

Supported interface languages: English, Simplified Chinese, Traditional
Chinese, French, German, and Italian.

## Platform Compatibility

Supported systems: Windows, macOS, and Linux.

The GUI tries wxPython first and falls back to tkinter. In KiCad 5 legacy mode,
the launcher prefers tkinter first and passes the detected KiCad language and
configuration path to the external Python 3 process.

## Install

1. Close KiCad.
2. Copy the whole `kicad-backport` folder into your KiCad user `plugins`
   folder.
3. For KiCad 10.99 and newer API plugins, use the versioned user plugins
   folder, for example `C:\Users\<you>\Documents\KiCad\10.99\plugins`.
4. In KiCad 10.99, enable the KiCad API/API server in Preferences.
5. For older KiCad versions, also copy the same folder into `scripting/plugins`.
6. Start KiCad again.
7. Run `Create KiCad Backport`.

In KiCad 10.99, API plugins are not loaded from the installed stock scripting
folder such as `share/kicad/scripting/plugins`; use the user `plugins` folder
instead and make sure the KiCad API/API server is enabled.

## Use

1. Choose a KiCad file or project folder.
2. Choose a different output file or folder.
3. Select the target KiCad version.
4. Click `Convert`.

The output is written with a target suffix such as `_V7`, `_V5`, or `_V10_99`.
For V5 targets, modern schematic and symbol-library extensions are changed to
legacy extensions automatically.

Command-line launcher:

```powershell
python plugin\plugin.py --input <input-path> --output <output-path> --target-version 5.0 --report report.json
```

Check the converted copy in the target KiCad version before sharing or
manufacturing from it.
