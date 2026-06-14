# KiCad Backport

Copyright (C) askstar

Versione 0.4.3

KiCad Backport crea una copia compatibile di un progetto o file KiCad per una
versione KiCad di destinazione precedente. E pensato per flussi pratici di
downgrade e upgrade tra file S-expression moderni e file legacy dell'epoca
KiCad 5. Il progetto originale non viene sovrascritto.

Il core di conversione e implementato in puro Python ed esegue nello stesso
processo durante il normale uso del plugin. Il Python di KiCad 5 avvia la stessa
GUI tramite un interprete Python 3 esterno, quindi anche le vecchie
installazioni KiCad possono usare il motore di conversione corrente.

## Traduzioni

- [English](README.en.md)
- [简体中文](README.zh_CN.md)
- [繁體中文](README.zh_TW.md)
- [Français](README.fr.md)
- [Deutsch](README.de.md)
- [Italiano](README.it.md)

## Funzionalita attuali

- Converte intere cartelle di progetto KiCad o singoli file KiCad.
- Supporta board, schemi, librerie di simboli, footprint, worksheet, regole di
  progettazione, progetti e file legacy di progetto/libreria/schema quando il
  formato di destinazione definisce un percorso di conversione.
- Converte file moderni `.kicad_sch`, `.kicad_sym` e `.kicad_pro` nei formati
  KiCad 5 legacy `.sch`, `.lib` / `.dcm` e `.pro` per destinazioni V5.
- Aggiorna file legacy `.sch`, `.lib`, `.dcm` e `.pro` in file KiCad moderni
  S-expression o JSON per destinazioni piu recenti.
- Preserva le librerie di simboli locali al progetto e normalizza le tabelle
  libreria per destinazioni vecchie.
- Ricostruisce quando necessario i dati di gerarchia schema e istanze simbolo
  KiCad 6+ per output di progetto moderni.
- Scrive file `.kicad_prl` locali compatibili per output board V6/V7/V8, con
  elementi visibili e layer compatibili.
- Estrae risorse di modelli 3D integrate in PCB/footprint in file locali `3D/`
  quando la decompressione zstd e disponibile. Il core include un piccolo
  decoder di frame zstd integrato per blocchi raw/RLE e puo usare anche
  `compression.zstd` di Python, `libzstd` di sistema o il pacchetto opzionale
  `zstandard` per blocchi compressi completi.
- Usa riscritture di compatibilita per funzionalita piu recenti di PCB,
  footprint, schema, simbolo, worksheet e regole di progettazione che non sono
  accettate dalle versioni KiCad piu vecchie.
- Scrive un report JSON di conversione quando richiesto dalla CLI o quando la
  conversione e avviata dalla GUI.

Alcune funzionalita moderne di KiCad sono intrinsecamente con perdita quando
convertite in formati molto piu vecchi. Il convertitore rimuove, riscrive o
approssima costrutti non supportati e segnala avvisi per tali cambiamenti.

## Versioni di destinazione

La lista delle destinazioni GUI e:

- KiCad 10
- KiCad 9
- KiCad 8
- KiCad 7
- KiCad 6
- KiCad 5.1
- KiCad 5.0
- KiCad 4

Il core accetta anche destinazioni numeriche raw dove supportate, inclusi
formati di sviluppo board/footprint come `20260603` e `20260521`.

Le famiglie di input supportate includono:

- File nightly KiCad 10.99 correnti
- File KiCad 10, 9, 8, 7, 6 e 5
- File KiCad legacy `.sch`, `.lib`, `.dcm` e `.pro`

## Lingua

Il plugin segue la lingua selezionata in KiCad quando possibile. Controlla anche
file di configurazione in stile KiCad 5 come `kicad_common`, le comuni variabili
d'ambiente di lingua KiCad e infine la lingua dell'interfaccia del sistema
operativo.

Lingue interfaccia supportate:

- Inglese
- Cinese semplificato
- Cinese tradizionale
- Francese
- Tedesco
- Italiano

Riavviare KiCad o riaprire la finestra del plugin dopo aver cambiato la lingua
di KiCad.

## Compatibilita multipiattaforma

Sistemi supportati:

- Windows
- macOS
- Linux

La GUI prova prima wxPython e poi ripiega su tkinter. In modalita legacy
KiCad 5, il launcher preferisce tkinter e passa la lingua KiCad rilevata e il
percorso di configurazione al processo Python 3 esterno.

## Installazione

1. Chiudere KiCad.
2. Copiare l'intera cartella `kicad-backport` nella cartella utente `plugins`
   di KiCad.
3. Per KiCad 10.99 e i plugin API piu recenti, usare la cartella utente
   versionata, per esempio `C:\Users\<utente>\Documents\KiCad\10.99\plugins`.
4. In KiCad 10.99, abilitare KiCad API/API server nelle preferenze; altrimenti
   KiCad non scoprira o carichera i plugin API.
5. Per le versioni meno recenti di KiCad, copiare la stessa cartella anche nella
   cartella `scripting/plugins` di KiCad.
6. Riavviare KiCad.
7. Aprire il gestore plugin KiCad o la barra strumenti/il menu
   dell'applicazione e cercare `Crea backport KiCad`.

Se l'azione non appare, confermare che la cartella sia stata copiata nella
cartella plugin della versione KiCad in uso. In KiCad 10.99, i plugin API non
vengono caricati dalla cartella scripting installata, come
`share/kicad/scripting/plugins`; usare invece la cartella utente `plugins` e
assicurarsi che KiCad API/API server sia abilitato.

## Uso da KiCad

1. Eseguire `Crea backport KiCad`.
2. Scegliere una cartella di progetto o un file KiCad supportato.
3. Scegliere un file o una cartella di output diversa.
4. Selezionare la versione KiCad di destinazione.
5. Fare clic su `Converti`.

L'output viene scritto con un suffisso di destinazione come `_V7`, `_V5` o
`_V10_99`. Per destinazioni V5, le estensioni moderne di schema e libreria
simboli vengono cambiate automaticamente in estensioni legacy.

## Uso da riga di comando

Eseguire il launcher con argomenti:

```powershell
python plugin\plugin.py --input <input-path> --output <output-path> --target-version 5.0 --report report.json
```

Elencare le destinazioni supportate dalla GUI:

```powershell
python plugin\plugin.py --list-targets
```

## Creare il pacchetto

Creare l'archivio del plugin dalla radice del repository:

```powershell
.\build.ps1 -Format all
```

```sh
./build.sh --format all
```

I formati pacchetto supportati sono `zip`, `tar.gz` e `all`.

Variabili d'ambiente utili:

- `KICAD_BACKPORT_PYTHON`: eseguibile Python 3 usato dal launcher KiCad 5.
- `KICAD_BACKPORT_GUI_BACKEND`: `wx`, `tk`, `auto` o `legacy`.
- `KICAD_BACKPORT_LANGUAGE`: override esplicito della lingua UI.
- `KICAD_BACKPORT_KICAD_CONFIG_PATH`: file o cartella di configurazione KiCad
  usata per il rilevamento della lingua.

## Note importanti

- Scegliere sempre un percorso di output diverso dal progetto originale.
- Controllare la copia convertita nella versione KiCad di destinazione prima di
  condividerla o usarla per la produzione.
- Destinazioni molto vecchie non possono preservare ogni funzionalita moderna.
  Consultare il report di conversione e gli eventuali messaggi di avviso.
