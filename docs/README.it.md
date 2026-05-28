# KiCad Backport

Copyright (C) askstar

Versione 0.0.2

KiCad Backport crea una copia di un progetto o file KiCad che puo essere aperta
con una versione precedente di KiCad. Il progetto originale non viene
sovrascritto.

## Lingua

Il plugin usa la lingua selezionata in KiCad quando possibile. Se non trova una
lingua salvata in KiCad, usa la lingua del sistema operativo.

Lingue supportate: inglese, cinese semplificato, cinese tradizionale, francese,
tedesco e italiano.

## Compatibilita multipiattaforma

Sistemi supportati:

- Windows x64 e Windows ARM64
- macOS Intel e Apple Silicon
- Linux x64 e Linux ARM64

Il plugin sceglie automaticamente il convertitore adatto al sistema.

## Versioni di destinazione

- KiCad 10
- KiCad 9
- KiCad 8
- KiCad 7

## Installazione

1. Chiudere KiCad.
2. Copiare l'intera cartella `kicad_backport` nella cartella `plugins` di
   KiCad.
3. Per le versioni meno recenti di KiCad, copiare la stessa cartella anche in
   `scripting/plugins`.
4. Riavviare KiCad.
5. Avviare `Crea backport KiCad`.

## Uso

1. Scegliere un file KiCad o una cartella di progetto.
2. Scegliere un file o una cartella di destinazione diversa.
3. Selezionare la versione KiCad di destinazione.
4. Fare clic su `Converti`.

Controllare la copia convertita nella versione KiCad di destinazione prima di
condividerla o usarla per la produzione.
