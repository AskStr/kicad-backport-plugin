# KiCad Backport

Copyright (C) 问星/askstar

Version 0.0.2

KiCad Backport helps you create a copy of a KiCad project or file that
can be opened by an older KiCad version.

The original project is not overwritten.

The plugin automatically follows your KiCad or system language when possible.
The current user interface includes English, Simplified Chinese, Traditional
Chinese, French, German, and Italian.

## Translations

- [English](docs/README.en.md)
- [简体中文](docs/README.zh_CN.md)
- [繁體中文](docs/README.zh_TW.md)
- [Français](docs/README.fr.md)
- [Deutsch](docs/README.de.md)
- [Italiano](docs/README.it.md)

## Language

KiCad Backport automatically uses the language selected in KiCad when it can
read it. If KiCad has no saved language setting, it uses the operating system
language.

Supported interface languages:

- English
- Simplified Chinese
- Traditional Chinese
- French
- German
- Italian

Restart KiCad or reopen the plugin window after changing the KiCad language.

## Platform Compatibility

KiCad Backport includes converters for:

- Windows x64 and Windows ARM64
- macOS Intel and Apple Silicon
- Linux x64 and Linux ARM64

The plugin automatically chooses the matching converter for the current
system. No manual command-line setup is needed for normal KiCad use.

## Supported Targets

- KiCad 10
- KiCad 9
- KiCad 8
- KiCad 7

KiCad 6 output is hidden for now and will be enabled after more compatibility
work.

## Install

1. Close KiCad.
2. Copy the whole `kicad_backport` folder into your KiCad `plugins` folder.
3. For older KiCad versions, also copy the same folder into your KiCad
   `scripting/plugins` folder.
4. Start KiCad again.
5. Open the KiCad Plugin Manager or the application toolbar/menu and look for
   `Create KiCad Backport`.

If the action does not appear, confirm the folder was copied into the plugin
folder for the KiCad version you are currently using.

## Use

1. Run `Create KiCad Backport` from KiCad.
2. Choose a KiCad file or project folder as the input.
3. Choose a different output file or folder.
4. Select the target KiCad version.
5. Click `Convert`.

The plugin writes the converted copy to the output path and creates a small
conversion report next to it.

## Important Notes

- Always choose an output path different from the original project.
- Some features from newer KiCad versions may be removed or simplified when
  saving for older KiCad versions.
- Check the converted copy in the target KiCad version before sharing or
  manufacturing from it.
