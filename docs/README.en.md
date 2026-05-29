# KiCad Backport

Copyright (C) askstar

Version 0.2.1

KiCad Backport creates a copy of a KiCad project or file that can be opened by
an older KiCad version. The original project is not overwritten.

Version 0.2.1 supports projects saved by current KiCad 10.99 nightly builds and
can write KiCad 10, KiCad 9, KiCad 8, or KiCad 7 compatible copies.

## Language

The plugin follows the language selected in KiCad when possible. If KiCad has
no saved language setting, it uses the operating system language.

Supported interface languages: English, Simplified Chinese, Traditional
Chinese, French, German, and Italian.

## Platform Compatibility

KiCad Backport's conversion core is implemented entirely in Python and runs
in-process inside the plugin. It does not require platform-specific converter
binaries.

Supported systems:

- Windows
- macOS
- Linux

## Supported Targets

Supported input versions:

- KiCad 10.99 nightly
- KiCad 10
- KiCad 9
- KiCad 8
- KiCad 7

Supported output targets:

- KiCad 10
- KiCad 9
- KiCad 8
- KiCad 7

## Install

1. Close KiCad.
2. Copy the whole `kicad_backport` folder into your KiCad user `plugins`
   folder.
3. For KiCad 10.99 and newer API plugins, use the versioned user plugins
   folder, for example `C:\Users\<you>\Documents\KiCad\10.99\plugins`.
4. In KiCad 10.99, enable the KiCad API/API server in Preferences; otherwise
   KiCad will not discover or load API plugins.
5. For older KiCad versions, also copy it into `scripting/plugins`.
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

Check the converted copy in the target KiCad version before sharing or
manufacturing from it.
