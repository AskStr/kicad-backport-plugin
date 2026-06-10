# KiCad Backport

Copyright (C) askstar

Versione 0.4.1

KiCad Backport crea una copia compatibile di un progetto o file KiCad per una
versione KiCad precedente. Supporta flussi pratici di downgrade e upgrade tra
file S-expression moderni e file legacy dell'epoca KiCad 5. Il progetto
originale non viene sovrascritto.

Il core di conversione e implementato in puro Python. Il Python di KiCad 5
avvia la stessa GUI tramite un interprete Python 3 esterno, quindi anche le
vecchie installazioni KiCad possono usare il motore corrente.

## Funzionalita attuali

- Converte intere cartelle di progetto o singoli file KiCad.
- Gestisce board, schemi, librerie di simboli, footprint, worksheet, regole di
  progettazione, progetti e file legacy di progetto/libreria/schema quando
  esiste un percorso di conversione.
- Converte `.kicad_sch`, `.kicad_sym` e `.kicad_pro` nei formati legacy
  KiCad 5 `.sch`, `.lib` / `.dcm` e `.pro`.
- Aggiorna file legacy `.sch`, `.lib`, `.dcm` e `.pro` in file KiCad moderni
  per destinazioni piu recenti.
- Preserva le librerie di simboli locali, normalizza le tabelle libreria,
  ricostruisce quando necessario le istanze gerarchiche KiCad 6+ e scrive
  `.kicad_prl` compatibili per output board V6/V7/V8.
- Scrive un report JSON di conversione quando richiesto dalla GUI o dalla CLI.

## Versioni di destinazione

Destinazioni GUI: KiCad 10, 9, 8, 7, 6, 5.1, 5.0 e 4.

Il core accetta anche destinazioni numeriche raw supportate, come `20260603` e
`20260521`.

Gli input supportati includono file nightly KiCad 10.99 correnti, KiCad 10 fino
a KiCad 5, e file legacy `.sch`, `.lib`, `.dcm` e `.pro`.

## Lingua

Il plugin usa la lingua selezionata in KiCad quando possibile. Legge i file di
configurazione in stile KiCad 5, le comuni variabili d'ambiente di lingua KiCad
e infine la lingua dell'interfaccia del sistema operativo.

Lingue supportate: inglese, cinese semplificato, cinese tradizionale, francese,
tedesco e italiano.

## Compatibilita multipiattaforma

Sistemi supportati: Windows, macOS e Linux.

La GUI prova prima wxPython e poi tkinter. In modalita legacy KiCad 5, il
launcher preferisce tkinter e passa la lingua KiCad rilevata e il percorso di
configurazione al processo Python 3 esterno.

## Installazione

1. Chiudere KiCad.
2. Copiare l'intera cartella `kicad-backport` nella cartella utente `plugins`
   di KiCad.
3. Per KiCad 10.99 e i plugin API piu recenti, usare la cartella utente
   versionata, per esempio `C:\Users\<utente>\Documents\KiCad\10.99\plugins`.
4. In KiCad 10.99, abilitare KiCad API/API server nelle preferenze.
5. Per le versioni meno recenti di KiCad, copiare la stessa cartella anche in
   `scripting/plugins`.
6. Riavviare KiCad.
7. Avviare `Crea backport KiCad`.

## Uso

1. Scegliere un file KiCad o una cartella di progetto.
2. Scegliere un file o una cartella di destinazione diversa.
3. Selezionare la versione KiCad di destinazione.
4. Fare clic su `Converti`.

L'output riceve un suffisso target come `_V7`, `_V5` o `_V10_99`. Per le
destinazioni V5, le estensioni moderne di schema e libreria simboli vengono
convertite automaticamente in estensioni legacy.

CLI:

```powershell
python plugin\plugin.py --input <input-path> --output <output-path> --target-version 5.0 --report report.json
```

Controllare la copia convertita nella versione KiCad di destinazione prima di
condividerla o usarla per la produzione.
