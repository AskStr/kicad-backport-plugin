# KiCad Backport

Copyright (C) askstar

Version 0.0.2

KiCad Backport erstellt eine Kopie eines KiCad-Projekts oder einer KiCad-Datei,
die mit einer aelteren KiCad-Version geoeffnet werden kann. Das Originalprojekt
wird nicht ueberschrieben.

## Sprache

Das Plugin verwendet nach Moeglichkeit die in KiCad gewaehlte Sprache. Wenn
keine KiCad-Spracheinstellung gefunden wird, wird die Systemsprache verwendet.

Unterstuetzte Oberflaechensprachen: Englisch, vereinfachtes Chinesisch,
traditionelles Chinesisch, Franzoesisch, Deutsch und Italienisch.

## Plattformkompatibilitaet

Unterstuetzte Systeme:

- Windows x64 und Windows ARM64
- macOS Intel und Apple Silicon
- Linux x64 und Linux ARM64

Das Plugin waehlt automatisch den passenden Konverter.

## Zielversionen

- KiCad 10
- KiCad 9
- KiCad 8
- KiCad 7

## Installation

1. Schliessen Sie KiCad.
2. Kopieren Sie den gesamten Ordner `kicad_backport` in den KiCad-Ordner
   `plugins`.
3. Fuer aeltere KiCad-Versionen kopieren Sie denselben Ordner auch nach
   `scripting/plugins`.
4. Starten Sie KiCad neu.
5. Starten Sie `KiCad-Backport erstellen`.

## Verwendung

1. Waehlen Sie eine KiCad-Datei oder einen Projektordner.
2. Waehlen Sie eine andere Ausgabedatei oder einen anderen Ausgabeordner.
3. Waehlen Sie die Zielversion von KiCad.
4. Klicken Sie auf `Konvertieren`.

Pruefen Sie die konvertierte Kopie in der Zielversion von KiCad, bevor Sie sie
weitergeben oder fuer die Fertigung verwenden.
