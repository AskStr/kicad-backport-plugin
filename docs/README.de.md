# KiCad Backport

Copyright (C) askstar

Version 0.4.4

KiCad Backport erstellt eine kompatible Kopie eines KiCad-Projekts oder einer
KiCad-Datei fuer eine aeltere KiCad-Zielversion. Es ist fuer praktische
Downgrade- und Upgrade-Ablaeufe zwischen modernen S-Expression-Dateien und
KiCad-5-Legacy-Dateien gedacht. Das Originalprojekt wird nicht ueberschrieben.

Der Konvertierungskern ist in reinem Python implementiert und laeuft bei
normaler Plugin-Nutzung im Prozess. KiCad-5-Python startet dieselbe GUI ueber
einen externen Python-3-Interpreter, sodass alte KiCad-Installationen den
Konvertierungskern weiterhin verwenden koennen.

## Uebersetzungen

- [English](README.en.md)
- [简体中文](README.zh_CN.md)
- [繁體中文](README.zh_TW.md)
- [Français](README.fr.md)
- [Deutsch](README.de.md)
- [Italiano](README.it.md)

## Aktuelle Funktionen

- Konvertiert ganze KiCad-Projektordner oder einzelne KiCad-Dateien.
- Unterstuetzt Board-, Schaltplan-, Symbolbibliothek-, Footprint-,
  Worksheet-, Design-Rule-, Projekt- und Legacy-Projekt/Bibliothek/
  Schaltplandateien, sofern das Zielformat einen Konvertierungspfad definiert.
- Konvertiert moderne `.kicad_sch`, `.kicad_sym` und `.kicad_pro` Dateien zu
  KiCad-5-Legacy-Dateien `.sch`, `.lib` / `.dcm` und `.pro` fuer V5-Ziele.
- Aktualisiert Legacy-Dateien `.sch`, `.lib`, `.dcm` und `.pro` zurueck zu
  modernen KiCad-S-Expression- oder JSON-Projektdateien fuer neuere Ziele.
- Erhaelt lokale Symbolbibliotheken des Projekts und normalisiert
  Bibliothekstabellen fuer alte Ziele.
- Rekonstruiert bei Bedarf KiCad-6+-Schaltplanhierarchie- und
  Symbolinstanzdaten fuer moderne Projektausgaben.
- Schreibt kompatible lokale `.kicad_prl` Dateien fuer V6/V7/V8-Board-Ausgaben
  mit kompatiblen sichtbaren Elementen und Layern.
- Extrahiert in PCB/Footprint eingebettete 3D-Modellressourcen in lokale
  `3D/` Dateien des Projekts, wenn zstd-Dekompression verfuegbar ist. Der Kern
  enthaelt einen kleinen eingebauten zstd-Frame-Decoder fuer Raw/RLE-Bloecke und
  kann fuer voll komprimierte Bloecke auch Pythons `compression.zstd`, das
  System-`libzstd` oder das optionale Paket `zstandard` verwenden.
- Nutzt Kompatibilitaets-Umschreibungen fuer neuere PCB-, Footprint-,
  Schaltplan-, Symbol-, Worksheet- und Design-Rule-Funktionen, die von
  aelteren KiCad-Versionen nicht akzeptiert werden.
- Schreibt einen JSON-Konvertierungsbericht, wenn er per CLI angefordert oder
  aus der GUI gestartet wird.

Einige moderne KiCad-Funktionen sind bei der Konvertierung in deutlich aeltere
Formate grundsaetzlich verlustbehaftet. Der Konverter entfernt, schreibt um
oder approximiert nicht unterstuetzte Konstrukte und meldet Warnungen fuer
diese Aenderungen.

## Zielversionen

Die GUI-Zielliste ist:

- KiCad 10
- KiCad 9
- KiCad 8
- KiCad 7
- KiCad 6
- KiCad 5.1
- KiCad 5.0
- KiCad 4

Der Konvertierungskern akzeptiert auch unterstuetzte numerische Rohformatziele,
einschliesslich Entwicklungsformate fuer Board/Footprint wie `20260603` und
`20260521`.

Unterstuetzte Eingabefamilien:

- Aktuelle KiCad-10.99-Nightly-Dateien
- KiCad 10, 9, 8, 7, 6 und 5 Dateien
- KiCad-Legacy-Dateien `.sch`, `.lib`, `.dcm` und `.pro`

## Sprache

Das Plugin verwendet nach Moeglichkeit die in KiCad gewaehlte Sprache. Es
prueft ausserdem KiCad-5-Konfigurationsdateien wie `kicad_common`, uebliche
KiCad-Sprachumgebungsvariablen und zuletzt die UI-Sprache des Betriebssystems.

Unterstuetzte Oberflaechensprachen:

- Englisch
- Vereinfachtes Chinesisch
- Traditionelles Chinesisch
- Franzoesisch
- Deutsch
- Italienisch

Starten Sie KiCad neu oder oeffnen Sie das Plugin-Fenster erneut, nachdem Sie
die KiCad-Sprache geaendert haben.

## Plattformkompatibilitaet

Unterstuetzte Systeme:

- Windows
- macOS
- Linux

Die GUI versucht zuerst wxPython und faellt auf tkinter zurueck. Im
KiCad-5-Legacy-Modus bevorzugt der Launcher tkinter und uebergibt die erkannte
KiCad-Sprache und den Konfigurationspfad an den externen Python-3-Prozess.

## Installation

1. Schliessen Sie KiCad.
2. Kopieren Sie den gesamten Ordner `kicad-backport` in den KiCad-Ordner fuer
   Benutzer-`plugins`.
3. Fuer KiCad 10.99 und neuere API-Plugins verwenden Sie den versionierten
   Benutzer-Plugin-Ordner, zum Beispiel
   `C:\Users\<Sie>\Documents\KiCad\10.99\plugins`.
4. Aktivieren Sie in KiCad 10.99 die KiCad API/API server in den Einstellungen;
   andernfalls erkennt oder laedt KiCad API-Plugins nicht.
5. Fuer aeltere KiCad-Versionen kopieren Sie denselben Ordner auch in den
   KiCad-Ordner `scripting/plugins`.
6. Starten Sie KiCad neu.
7. Oeffnen Sie den KiCad Plugin Manager oder die Werkzeugleiste/das Menue der
   Anwendung und suchen Sie nach `KiCad-Backport erstellen`.

Wenn die Aktion nicht erscheint, pruefen Sie, ob der Ordner in den Plugin-Ordner
der KiCad-Version kopiert wurde, die Sie gerade verwenden. In KiCad 10.99
werden API-Plugins nicht aus dem installierten Standard-Scripting-Ordner wie
`share/kicad/scripting/plugins` geladen; verwenden Sie stattdessen den
Benutzerordner `plugins` und stellen Sie sicher, dass KiCad API/API server
aktiviert ist.

## Verwendung aus KiCad

1. Starten Sie `KiCad-Backport erstellen`.
2. Waehlen Sie einen Projektordner oder eine unterstuetzte KiCad-Datei.
3. Waehlen Sie eine andere Ausgabedatei oder einen anderen Ausgabeordner.
4. Waehlen Sie die Zielversion von KiCad.
5. Klicken Sie auf `Konvertieren`.

Die Ausgabe wird mit einem Ziel-Suffix wie `_V7`, `_V5` oder `_V10_99`
geschrieben. Fuer V5-Ziele werden moderne Schaltplan- und
Symbolbibliothek-Erweiterungen automatisch in Legacy-Erweiterungen geaendert.

## Verwendung ueber die Kommandozeile

Starten Sie den Launcher mit Argumenten:

```powershell
python plugin\plugin.py --input <input-path> --output <output-path> --target-version 5.0 --report report.json
```

GUI-unterstuetzte Ziele auflisten:

```powershell
python plugin\plugin.py --list-targets
```

## Paket bauen

Bauen Sie das Plugin-Archiv aus dem Repository-Stamm:

```powershell
.\build.ps1 -Format all
```

```sh
./build.sh --format all
```

Die unterstuetzten Paketformate sind `zip`, `tar.gz` und `all`.

Nuetzliche Umgebungsvariablen:

- `KICAD_BACKPORT_PYTHON`: Python-3-Executable, das vom KiCad-5-Launcher
  verwendet wird.
- `KICAD_BACKPORT_GUI_BACKEND`: `wx`, `tk`, `auto` oder `legacy`.
- `KICAD_BACKPORT_LANGUAGE`: explizite Ueberschreibung der UI-Sprache.
- `KICAD_BACKPORT_KICAD_CONFIG_PATH`: KiCad-Konfigurationsdatei oder -Ordner
  fuer die Spracherkennung.

## Wichtige Hinweise

- Waehlen Sie immer einen Ausgabepfad, der sich vom Originalprojekt
  unterscheidet.
- Pruefen Sie die konvertierte Kopie in der Zielversion von KiCad, bevor Sie
  sie weitergeben oder fuer die Fertigung verwenden.
- Sehr alte Ziele koennen nicht jede moderne Funktion erhalten. Lesen Sie den
  Konvertierungsbericht und alle Warnmeldungen.
