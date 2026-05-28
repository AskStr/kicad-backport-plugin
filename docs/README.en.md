# KiCad Backport

Copyright (C) askstar

Version 0.0.2

KiCad Backport creates a copy of a KiCad project or file that can be opened by
an older KiCad version. The original project is not overwritten.

## Language

The plugin follows the language selected in KiCad when possible. If KiCad has
no saved language setting, it uses the operating system language.

Supported interface languages: English, Simplified Chinese, Traditional
Chinese, French, German, and Italian.

## Platform Compatibility

Supported systems:

- Windows x64 and Windows ARM64
- macOS Intel and Apple Silicon
- Linux x64 and Linux ARM64

The plugin automatically chooses the matching converter.

## Supported Targets

- KiCad 10
- KiCad 9
- KiCad 8
- KiCad 7

## Install

1. Close KiCad.
2. Copy the whole `kicad_backport` folder into your KiCad `plugins` folder.
3. For older KiCad versions, also copy it into `scripting/plugins`.
4. Start KiCad again.
5. Run `Create KiCad Backport`.

## Use

1. Choose a KiCad file or project folder.
2. Choose a different output file or folder.
3. Select the target KiCad version.
4. Click `Convert`.

Check the converted copy in the target KiCad version before sharing or
manufacturing from it.
