# KiCad Backport

Copyright (C) askstar

Version 0.4.1

KiCad Backport erstellt eine kompatible Kopie eines KiCad-Projekts oder einer
KiCad-Datei fuer eine aeltere KiCad-Zielversion. Es unterstuetzt Downgrade- und
Upgrade-Ablaeufe fuer moderne S-Expression-Dateien und KiCad-5-Legacy-Dateien.
Das Originalprojekt wird nicht ueberschrieben.

Der Konvertierungskern ist in reinem Python implementiert. KiCad-5-Python
startet die GUI ueber einen externen Python-3-Interpreter, sodass alte
KiCad-Installationen den aktuellen Konvertierungskern verwenden koennen.

## Aktuelle Funktionen

- Konvertiert ganze Projektordner oder einzelne KiCad-Dateien.
- Unterstuetzt Board-, Schaltplan-, Symbolbibliothek-, Footprint-,
  Worksheet-, Design-Rule-, Projekt- und Legacy-Projekt/Bibliothek/
  Schaltplandateien, sofern ein Konvertierungspfad vorhanden ist.
- Konvertiert moderne `.kicad_sch`, `.kicad_sym` und `.kicad_pro` Dateien zu
  KiCad-5-Legacy-Dateien `.sch`, `.lib` / `.dcm` und `.pro`.
- Aktualisiert Legacy-Dateien `.sch`, `.lib`, `.dcm` und `.pro` zu modernen
  KiCad-Dateien fuer neuere Ziele.
- Erhaelt lokale Symbolbibliotheken, normalisiert Bibliothekstabellen,
  rekonstruiert bei Bedarf KiCad-6+-Schaltplanhierarchie-Instanzen und schreibt
  kompatible lokale `.kicad_prl` Dateien fuer V6/V7/V8-Board-Ausgaben.
- Schreibt einen JSON-Konvertierungsbericht, wenn die GUI oder CLI ihn anlegt.

## Zielversionen

GUI-Ziele: KiCad 10, 9, 8, 7, 6, 5.1, 5.0 und 4.

Der Konvertierungskern akzeptiert auch unterstuetzte numerische Rohformatziele
wie `20260603` und `20260521`.

Unterstuetzte Eingaben umfassen aktuelle KiCad-10.99-Nightly-Dateien, KiCad 10
bis KiCad 5 und Legacy-Dateien `.sch`, `.lib`, `.dcm` und `.pro`.

## Sprache

Das Plugin verwendet nach Moeglichkeit die in KiCad gewaehlte Sprache. Es liest
KiCad-5-Konfigurationsdateien, uebliche KiCad-Sprachumgebungsvariablen und
danach die Systemsprache.

Unterstuetzte Oberflaechensprachen: Englisch, vereinfachtes Chinesisch,
traditionelles Chinesisch, Franzoesisch, Deutsch und Italienisch.

## Plattformkompatibilitaet

Unterstuetzte Systeme: Windows, macOS und Linux.

Die GUI versucht zuerst wxPython und faellt auf tkinter zurueck. Im
KiCad-5-Legacy-Modus bevorzugt der Launcher tkinter und uebergibt erkannte
Sprache und Konfigurationspfad an den externen Python-3-Prozess.

## Installation

1. Schliessen Sie KiCad.
2. Kopieren Sie den gesamten Ordner `kicad-backport` in den KiCad-Ordner fuer
   Benutzer-Plugins.
3. Fuer KiCad 10.99 und neuere API-Plugins verwenden Sie den versionierten
   Benutzer-Plugin-Ordner, zum Beispiel
   `C:\Users\<Sie>\Documents\KiCad\10.99\plugins`.
4. Aktivieren Sie in KiCad 10.99 die KiCad API/API server in den Einstellungen.
5. Fuer aeltere KiCad-Versionen kopieren Sie denselben Ordner auch nach
   `scripting/plugins`.
6. Starten Sie KiCad neu.
7. Starten Sie `KiCad-Backport erstellen`.

## Verwendung

1. Waehlen Sie eine KiCad-Datei oder einen Projektordner.
2. Waehlen Sie eine andere Ausgabedatei oder einen anderen Ausgabeordner.
3. Waehlen Sie die Zielversion von KiCad.
4. Klicken Sie auf `Konvertieren`.

Die Ausgabe erhaelt einen Ziel-Suffix wie `_V7`, `_V5` oder `_V10_99`. Fuer
V5-Ziele werden moderne Schaltplan- und Symbolbibliothek-Erweiterungen
automatisch in Legacy-Erweiterungen geaendert.

CLI:

```powershell
python plugin\plugin.py --input <input-path> --output <output-path> --target-version 5.0 --report report.json
```

Pruefen Sie die konvertierte Kopie in der Zielversion von KiCad, bevor Sie sie
weitergeben oder fuer die Fertigung verwenden.
