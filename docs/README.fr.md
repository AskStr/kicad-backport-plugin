# KiCad Backport

Copyright (C) askstar

Version 0.4.4

KiCad Backport cree une copie compatible d'un projet ou fichier KiCad pour une
ancienne version cible de KiCad. Il est concu pour des flux pratiques de
downgrade et d'upgrade entre fichiers S-expression modernes et fichiers legacy
de l'epoque KiCad 5. Le projet original n'est pas ecrase.

Le coeur de conversion est implemente en Python pur et s'execute dans le
processus pour l'utilisation normale du plugin. Le Python de KiCad 5 lance la
meme GUI via un interpreteur Python 3 externe, ce qui permet aux anciennes
installations KiCad d'utiliser encore le moteur de conversion.

## Traductions

- [English](README.en.md)
- [简体中文](README.zh_CN.md)
- [繁體中文](README.zh_TW.md)
- [Français](README.fr.md)
- [Deutsch](README.de.md)
- [Italiano](README.it.md)

## Fonctions actuelles

- Convertit des dossiers de projet KiCad complets ou des fichiers KiCad
  individuels.
- Prend en charge les fichiers board, schema, bibliotheque de symboles,
  footprint, worksheet, regles de conception, projet, ainsi que les fichiers
  legacy de projet/bibliotheque/schema lorsque le format cible definit un
  chemin de conversion.
- Convertit les fichiers modernes `.kicad_sch`, `.kicad_sym` et `.kicad_pro`
  vers les fichiers KiCad 5 legacy `.sch`, `.lib` / `.dcm` et `.pro` pour les
  cibles V5.
- Met a niveau les fichiers legacy `.sch`, `.lib`, `.dcm` et `.pro` vers des
  fichiers KiCad S-expression ou JSON modernes pour les cibles recentes.
- Preserve les bibliotheques de symboles locales au projet et normalise les
  tables de bibliotheques pour les anciennes cibles.
- Reconstruit si besoin les donnees de hierarchie de schema et d'instances de
  symboles KiCad 6+ pour les sorties de projet modernes.
- Ecrit des fichiers `.kicad_prl` locaux compatibles pour les sorties board
  V6/V7/V8, avec elements visibles et couches compatibles.
- Extrait les ressources de modeles 3D integrees aux PCB/footprints vers des
  fichiers locaux `3D/` lorsque la decompression zstd est disponible. Le coeur
  inclut un petit decodeur de trames zstd pour les blocs raw/RLE et peut aussi
  utiliser `compression.zstd` de Python, `libzstd` du systeme ou le paquet
  optionnel `zstandard` pour les blocs compresses complets.
- Applique des reecritures de compatibilite pour les fonctions recentes de PCB,
  footprint, schema, symbole, worksheet et regles de conception qui ne sont pas
  acceptees par les anciennes versions de KiCad.
- Ecrit un rapport JSON de conversion lorsque la CLI le demande ou lorsque la
  conversion est lancee depuis la GUI.

Certaines fonctions KiCad modernes sont intrinsequement avec perte lorsqu'elles
sont converties vers des formats beaucoup plus anciens. Le convertisseur
supprime, reecrit ou approxime les constructions non prises en charge et signale
ces changements par des avertissements.

## Versions cibles

La liste des cibles de la GUI est :

- KiCad 10
- KiCad 9
- KiCad 8
- KiCad 7
- KiCad 6
- KiCad 5.1
- KiCad 5.0
- KiCad 4

Le coeur de conversion accepte aussi des cibles numeriques brutes lorsqu'elles
sont prises en charge, y compris des formats de developpement board/footprint
comme `20260603` et `20260521`.

Les familles d'entree prises en charge incluent :

- Les fichiers nightly KiCad 10.99 actuels
- Les fichiers KiCad 10, 9, 8, 7, 6 et 5
- Les fichiers KiCad legacy `.sch`, `.lib`, `.dcm` et `.pro`

## Langue

Le plugin suit si possible la langue selectionnee dans KiCad. Il verifie aussi
les fichiers de configuration de style KiCad 5 comme `kicad_common`, les
variables d'environnement de langue KiCad courantes, puis la langue de
l'interface du systeme d'exploitation.

Langues d'interface prises en charge :

- Anglais
- Chinois simplifie
- Chinois traditionnel
- Francais
- Allemand
- Italien

Redemarrez KiCad ou rouvrez la fenetre du plugin apres avoir change la langue
de KiCad.

## Compatibilite multiplateforme

Systemes pris en charge :

- Windows
- macOS
- Linux

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
4. Dans KiCad 10.99, activez KiCad API/API server dans les preferences ; sinon
   KiCad ne decouvrira pas et ne chargera pas les plugins API.
5. Pour les anciennes versions de KiCad, copiez aussi ce dossier dans le
   dossier `scripting/plugins` de KiCad.
6. Redemarrez KiCad.
7. Ouvrez le gestionnaire de plugins KiCad ou la barre d'outils/le menu de
   l'application et cherchez `Creer un backport KiCad`.

Si l'action n'apparait pas, verifiez que le dossier a ete copie dans le dossier
de plugins de la version de KiCad que vous utilisez. Dans KiCad 10.99, les
plugins API ne sont pas charges depuis le dossier de scripts installe, comme
`share/kicad/scripting/plugins`; utilisez plutot le dossier utilisateur
`plugins` et assurez-vous que KiCad API/API server est active.

## Utilisation depuis KiCad

1. Lancez `Creer un backport KiCad`.
2. Choisissez un dossier de projet ou un fichier KiCad pris en charge.
3. Choisissez un fichier ou dossier de sortie different.
4. Selectionnez la version KiCad cible.
5. Cliquez sur `Convertir`.

La sortie recoit un suffixe cible comme `_V7`, `_V5` ou `_V10_99`. Pour les
cibles V5, les extensions modernes de schema et de bibliotheque de symboles
sont automatiquement remplacees par les extensions legacy.

## Utilisation en ligne de commande

Lancez le programme avec des arguments :

```powershell
python plugin\plugin.py --input <input-path> --output <output-path> --target-version 5.0 --report report.json
```

Lister les cibles prises en charge par la GUI :

```powershell
python plugin\plugin.py --list-targets
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

Variables d'environnement utiles :

- `KICAD_BACKPORT_PYTHON` : executable Python 3 utilise par le lanceur KiCad 5.
- `KICAD_BACKPORT_GUI_BACKEND` : `wx`, `tk`, `auto` ou `legacy`.
- `KICAD_BACKPORT_LANGUAGE` : remplacement explicite de la langue de
  l'interface.
- `KICAD_BACKPORT_KICAD_CONFIG_PATH` : fichier ou dossier de configuration
  KiCad utilise pour la detection de langue.

## Notes importantes

- Choisissez toujours un chemin de sortie different du projet original.
- Verifiez la copie convertie dans la version KiCad cible avant de la partager
  ou de l'utiliser pour la fabrication.
- Les cibles tres anciennes ne peuvent pas conserver toutes les fonctions
  modernes. Consultez le rapport de conversion et les avertissements.
