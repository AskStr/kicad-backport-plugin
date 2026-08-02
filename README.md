# KiCad Backport

Copyright (C) 问星/askstar

Version 0.4.4

KiCad Backport creates a compatibility copy of a KiCad project or file for an
older KiCad target version. It is designed for practical downgrade and upgrade
workflows across modern S-expression files and KiCad 5-era legacy files. The
original project is not overwritten.

The converter core is implemented in pure Python and runs in-process for normal
plugin use. KiCad 5-era Python launches the same GUI through an external Python
3 interpreter so the conversion engine can still be used from old KiCad
installations.

## Translations

- [English](docs/README.en.md)
- [简体中文](docs/README.zh_CN.md)
- [繁體中文](docs/README.zh_TW.md)
- [Français](docs/README.fr.md)
- [Deutsch](docs/README.de.md)
- [Italiano](docs/README.it.md)

## Current Capabilities

- Converts whole KiCad project folders or individual KiCad files.
- Supports board, schematic, symbol-library, footprint, worksheet,
  design-rule, project, and legacy project/library/schematic files where the
  target format defines a conversion path.
- Converts modern `.kicad_sch`, `.kicad_sym`, and `.kicad_pro` files to KiCad
  5-era `.sch`, `.lib` / `.dcm`, and `.pro` files for V5 targets.
- Upgrades legacy `.sch`, `.lib`, `.dcm`, and `.pro` files back to modern
  KiCad S-expression or JSON project files for newer targets.
- Preserves project-local symbol libraries and normalizes library tables for
  old targets.
- Rebuilds KiCad 6+ schematic hierarchy and symbol instance data for modern
  project outputs when needed.
- Writes V6/V7/V8 project-local `.kicad_prl` files with compatible visible
  items and layers for board outputs.
- Extracts embedded PCB/footprint 3D model resources to project-local `3D/`
  files when zstd decompression is available. The core includes a small
  built-in zstd frame decoder for raw/RLE blocks and can also use Python's
  standard `compression.zstd`, system `libzstd`, or the optional `zstandard`
  package for full compressed blocks.
- Uses compatibility rewrites for newer PCB, footprint, schematic, symbol,
  worksheet, and design-rule features that are not accepted by older KiCad
  versions.
- Writes a JSON conversion report when requested by CLI or when launched from
  the GUI.

Some modern KiCad features are inherently lossy when converted to much older
formats. The converter removes, rewrites, or approximates unsupported constructs
and reports warnings for those changes.

## Supported Targets

The GUI target list is:

- KiCad 10
- KiCad 9
- KiCad 8
- KiCad 7
- KiCad 6
- KiCad 5.1
- KiCad 5.0
- KiCad 4

The conversion core also accepts raw numeric development-format targets, including
checkpoints from `20260410` through the current `20260728` board/footprint
format.  The bundled 10.99 profile currently writes symbol libraries at
`20260629`, schematics at `20260722`, and boards/footprints at `20260728`.

For targets that predate these 10.99 additions, native ellipses are approximated
with compatible polylines/polygons and footprint affine transforms are baked
into legacy geometry. Pin-to-pad maps, variant symbol overrides, net chains,
geometric constraints, and custom grid items are removed only when no
compatible representation exists; every approximation or removal is recorded
in the JSON conversion report. Embedded PNG reference images are rescaled when
crossing the corrected-PPI format boundary (`20260623`) to retain their rendered
size.

Supported input families include:

- Current KiCad 10.99 nightly files
- KiCad 10, 9, 8, 7, 6, and 5 files
- KiCad legacy `.sch`, `.lib`, `.dcm`, and `.pro` files

## Language

The plugin follows the language selected in KiCad when possible. It also checks
KiCad 5-style configuration files such as `kicad_common`, common KiCad language
environment variables, and finally the operating-system UI language.

Supported interface languages:

- English
- Simplified Chinese
- Traditional Chinese
- French
- German
- Italian

Restart KiCad or reopen the plugin window after changing the KiCad language.

## Platform Compatibility

Supported systems:

- Windows
- macOS
- Linux

The GUI tries wxPython first and falls back to tkinter. In KiCad 5 legacy mode,
the launcher prefers tkinter first and passes the detected KiCad language and
configuration path to the external Python 3 process.

## Install

1. Close KiCad.
2. Copy the whole `kicad-backport` folder into your KiCad user `plugins`
   folder.
3. For KiCad 10.99 and newer API plugins, use the versioned user plugins
   folder, for example `C:\Users\<you>\Documents\KiCad\10.99\plugins`.
4. In KiCad 10.99, enable the KiCad API/API server in Preferences; otherwise
   KiCad will not discover or load API plugins.
5. For older KiCad versions, also copy the same folder into your KiCad
   `scripting/plugins` folder.
6. Start KiCad again.
7. Open the KiCad Plugin Manager or the application toolbar/menu and look for
   `Create KiCad Backport`.

If the action does not appear, confirm the folder was copied into the plugin
folder for the KiCad version you are currently using. In KiCad 10.99, API
plugins are not loaded from the installed stock scripting folder such as
`share/kicad/scripting/plugins`; use the user `plugins` folder instead and make
sure the KiCad API/API server is enabled.

## Use From KiCad

1. Run `Create KiCad Backport`.
2. Choose a project folder or a supported KiCad file.
3. Choose a different output file or folder.
4. Select the target KiCad version.
5. Click `Convert`.

The output is written with a target suffix such as `_V7`, `_V5`, or `_V10_99`.
For V5 targets, modern schematic and symbol-library extensions are changed to
legacy extensions automatically.

## Use From Command Line

Run the launcher with arguments:

```powershell
python plugin\plugin.py --input <input-path> --output <output-path> --target-version 5.0 --report report.json
```

List GUI-supported targets:

```powershell
python plugin\plugin.py --list-targets
```

## Build Package

Build the plugin archive from the repository root:

```powershell
.\build.ps1 -Format all
```

```sh
./build.sh --format all
```

The supported package formats are `zip`, `tar.gz`, and `all`.

Useful environment variables:

- `KICAD_BACKPORT_PYTHON`: Python 3 executable used by the KiCad 5 launcher.
- `KICAD_BACKPORT_GUI_BACKEND`: `wx`, `tk`, `auto`, or `legacy`.
- `KICAD_BACKPORT_LANGUAGE`: explicit UI language override.
- `KICAD_BACKPORT_KICAD_CONFIG_PATH`: KiCad configuration file or folder used
  for language detection.

## Important Notes

- Always choose an output path different from the original project.
- Check the converted copy in the target KiCad version before sharing or
  manufacturing from it.
- Very old targets cannot preserve every modern feature. Review the conversion
  report and any warning messages.
