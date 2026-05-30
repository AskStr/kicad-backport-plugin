# KiCad Backport

Copyright (C) askstar

Version 0.3.1

KiCad Backport erstellt eine Kopie eines KiCad-Projekts oder einer KiCad-Datei,
die mit einer aelteren KiCad-Version geoeffnet werden kann. Das Originalprojekt
wird nicht ueberschrieben.

Version 0.3.1 unterstuetzt Projekte, die mit aktuellen KiCad-10.99-Nightly-
Versionen gespeichert wurden, und kann kompatible Kopien fuer KiCad 10, KiCad
9, KiCad 8 oder KiCad 7 schreiben.

## Highlights der Version 0.3.1

- Die Konvertierungsleistung wurde deutlich verbessert, in Tests mit grossen
  Projekten etwa 3x schneller.
- S-Expression-Parsing, Formatierung und Baumdurchlaeufe wurden fuer grosse
  Dateien optimiert.
- Downgrade-Regeln werden gebuendelt verarbeitet, um wiederholte vollstaendige
  Baumdurchlaeufe zu reduzieren.
- Die Kompatibilitaet mit KiCad 7 Python und die Vollstaendigkeitspruefung der
  Pakete wurden verbessert.

## Sprache

Das Plugin verwendet nach Moeglichkeit die in KiCad gewaehlte Sprache. Wenn
keine KiCad-Spracheinstellung gefunden wird, wird die Systemsprache verwendet.

Unterstuetzte Oberflaechensprachen: Englisch, vereinfachtes Chinesisch,
traditionelles Chinesisch, Franzoesisch, Deutsch und Italienisch.

## Plattformkompatibilitaet

Der Konvertierungskern von KiCad Backport ist vollstaendig in Python
implementiert und laeuft direkt im Plugin-Prozess. Plattformspezifische
Konverter-Binaerdateien sind fuer die normale Nutzung nicht mehr erforderlich.

Unterstuetzte Systeme:

- Windows
- macOS
- Linux

## Zielversionen

Unterstuetzte Eingabeversionen:

- KiCad 10.99 Nightly
- KiCad 10
- KiCad 9
- KiCad 8
- KiCad 7

Unterstuetzte Ausgabeziele:

- KiCad 10
- KiCad 9
- KiCad 8
- KiCad 7

## Installation

1. Schliessen Sie KiCad.
2. Kopieren Sie den gesamten Ordner `kicad-backport` in den KiCad-Ordner
   fuer Benutzer-Plugins.
3. Fuer KiCad 10.99 und neuere API-Plugins verwenden Sie den versionierten
   Benutzer-Plugin-Ordner, zum Beispiel
   `C:\Users\<Sie>\Documents\KiCad\10.99\plugins`.
4. Aktivieren Sie in KiCad 10.99 die KiCad API/API server in den Einstellungen;
   sonst erkennt oder laedt KiCad keine API-Plugins.
5. Fuer aeltere KiCad-Versionen kopieren Sie denselben Ordner auch nach
   `scripting/plugins`.
6. Starten Sie KiCad neu.
7. Starten Sie `KiCad-Backport erstellen`.

In KiCad 10.99 werden API-Plugins nicht aus dem installierten Stock-Scripting-
Ordner wie `share/kicad/scripting/plugins` geladen. Verwenden Sie stattdessen
den Benutzerordner `plugins` und stellen Sie sicher, dass KiCad API/API server
aktiviert ist.

## Verwendung

1. Waehlen Sie eine KiCad-Datei oder einen Projektordner.
2. Waehlen Sie eine andere Ausgabedatei oder einen anderen Ausgabeordner.
3. Waehlen Sie die Zielversion von KiCad.
4. Klicken Sie auf `Konvertieren`.

Pruefen Sie die konvertierte Kopie in der Zielversion von KiCad, bevor Sie sie
weitergeben oder fuer die Fertigung verwenden.
