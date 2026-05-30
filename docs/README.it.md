# KiCad Backport

Copyright (C) askstar

Versione 0.3.1

KiCad Backport crea una copia di un progetto o file KiCad che puo essere aperta
con una versione precedente di KiCad. Il progetto originale non viene
sovrascritto.

La versione 0.3.1 supporta i progetti salvati dalle versioni nightly attuali di
KiCad 10.99 e puo scrivere copie compatibili con KiCad 10, KiCad 9, KiCad 8 o
KiCad 7.

## Novita della versione 0.3.1

- Le prestazioni di conversione sono state migliorate in modo significativo,
  circa 3x piu veloci nei test con progetti di grandi dimensioni.
- Parsing, formattazione e attraversamento dell'albero S-expression sono
  ottimizzati per file di grandi dimensioni.
- La gestione delle regole di downgrade e raggruppata per ridurre gli
  attraversamenti completi ripetuti dell'albero.
- Sono migliorati la compatibilita con Python di KiCad 7 e i controlli di
  completezza dei pacchetti.

## Lingua

Il plugin usa la lingua selezionata in KiCad quando possibile. Se non trova una
lingua salvata in KiCad, usa la lingua del sistema operativo.

Lingue supportate: inglese, cinese semplificato, cinese tradizionale, francese,
tedesco e italiano.

## Compatibilita multipiattaforma

Il core di conversione di KiCad Backport e implementato interamente in Python
ed eseguito nel processo del plugin. I binari di conversione specifici per
piattaforma non sono piu necessari per l'uso normale.

Sistemi supportati:

- Windows
- macOS
- Linux

## Versioni di destinazione

Versioni di input supportate:

- KiCad 10.99 nightly
- KiCad 10
- KiCad 9
- KiCad 8
- KiCad 7

Destinazioni di output supportate:

- KiCad 10
- KiCad 9
- KiCad 8
- KiCad 7

## Installazione

1. Chiudere KiCad.
2. Copiare l'intera cartella `kicad-backport` nella cartella utente `plugins`
   di KiCad.
3. Per KiCad 10.99 e i plugin API piu recenti, usare la cartella utente
   versionata, per esempio `C:\Users\<utente>\Documents\KiCad\10.99\plugins`.
4. In KiCad 10.99, abilitare KiCad API/API server nelle preferenze; altrimenti
   KiCad non rileva e non carica i plugin API.
5. Per le versioni meno recenti di KiCad, copiare la stessa cartella anche in
   `scripting/plugins`.
6. Riavviare KiCad.
7. Avviare `Crea backport KiCad`.

In KiCad 10.99 i plugin API non vengono caricati dalla cartella di scripting
stock dell'installazione, per esempio `share/kicad/scripting/plugins`; usare
invece la cartella utente `plugins` e verificare che KiCad API/API server sia
abilitato.

## Uso

1. Scegliere un file KiCad o una cartella di progetto.
2. Scegliere un file o una cartella di destinazione diversa.
3. Selezionare la versione KiCad di destinazione.
4. Fare clic su `Converti`.

Controllare la copia convertita nella versione KiCad di destinazione prima di
condividerla o usarla per la produzione.
