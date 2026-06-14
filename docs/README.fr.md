# KiCad Backport

Copyright (C) askstar

Version 0.4.1

KiCad Backport cree une copie compatible d'un projet ou fichier KiCad pour une
ancienne version cible de KiCad. Il prend en charge les flux de downgrade et
d'upgrade entre fichiers S-expression modernes et fichiers legacy de l'epoque
KiCad 5. Le projet original n'est pas ecrase.

Le coeur de conversion est implemente en Python pur. Le Python de KiCad 5 lance
la meme GUI via un interpreteur Python 3 externe, ce qui permet aux anciennes
installations KiCad d'utiliser le moteur actuel.

## Fonctions actuelles

- Convertit des dossiers de projet complets ou des fichiers KiCad individuels.
- Gere les fichiers board, schema, bibliotheque de symboles, footprint,
  worksheet, regles de conception, projet, ainsi que les projets/bibliotheques/
  schemas legacy lorsqu'un chemin de conversion existe.
- Convertit `.kicad_sch`, `.kicad_sym` et `.kicad_pro` vers les formats
  KiCad 5 legacy `.sch`, `.lib` / `.dcm` et `.pro`.
- Met a niveau les fichiers legacy `.sch`, `.lib`, `.dcm` et `.pro` vers des
  fichiers KiCad modernes pour les cibles recentes.
- Preserve les bibliotheques de symboles locales, normalise les tables de
  bibliotheques, reconstruit si besoin les instances hierarchiques KiCad 6+ et
  ecrit des `.kicad_prl` compatibles pour les sorties board V6/V7/V8.
- Ecrit un rapport JSON de conversion lorsque la GUI ou la CLI le demande.

## Versions cibles

Cibles de la GUI : KiCad 10, 9, 8, 7, 6, 5.1, 5.0 et 4.

Le coeur de conversion accepte aussi des cibles numeriques brutes prises en
charge, comme `20260603` et `20260521`.

Les entrees prises en charge incluent les fichiers nightly KiCad 10.99 actuels,
KiCad 10 a KiCad 5, et les fichiers legacy `.sch`, `.lib`, `.dcm` et `.pro`.

## Langue

Le plugin utilise la langue choisie dans KiCad lorsque c'est possible. Il lit
les fichiers de configuration de style KiCad 5, les variables d'environnement
de langue KiCad courantes, puis la langue de l'interface du systeme.

Langues prises en charge : anglais, chinois simplifie, chinois traditionnel,
francais, allemand et italien.

## Compatibilite multiplateforme

Systemes pris en charge : Windows, macOS et Linux.

La GUI essaie d'abord wxPython puis se replie sur tkinter. En mode legacy
KiCad 5, le lanceur prefere tkinter et transmet la langue KiCad detectee ainsi
que le chemin de configuration au processus Python 3 externe.

## Installation

1. Fermez KiCad.
2. Copiez tout le dossier `kicad-backport` dans le dossier utilisateur
   `plugins` de KiCad.
3. Pour KiCad 10.99 et les plugins API plus recents, utilisez le dossier
   utilisateur versionne, par exemple
   `C:\Users\<vous>\Documents\KiCad\10.99\plugins`.
4. Dans KiCad 10.99, activez KiCad API/API server dans les preferences.
5. Pour les anciennes versions de KiCad, copiez aussi ce dossier dans
   `scripting/plugins`.
6. Redemarrez KiCad.
7. Lancez `Creer un backport KiCad`.

## Utilisation

1. Choisissez un fichier ou dossier de projet KiCad.
2. Choisissez un fichier ou dossier de sortie different.
3. Selectionnez la version KiCad cible.
4. Cliquez sur `Convertir`.

La sortie recoit un suffixe cible comme `_V7`, `_V5` ou `_V10_99`. Pour les
cibles V5, les extensions modernes de schema et bibliotheque de symboles sont
automatiquement remplacees par les extensions legacy.

CLI :

```powershell
python plugin\plugin.py --input <input-path> --output <output-path> --target-version 5.0 --report report.json
```

## Construction du paquet

Construisez l'archive du plugin depuis la racine du depot :

```powershell
.\build.ps1 -Format all
```

```sh
./build.sh --format all
```

Les formats de paquet pris en charge sont `zip`, `tar.gz` et `all`.

Verifiez la copie convertie dans la version KiCad cible avant de la partager ou
de l'utiliser pour la fabrication.
