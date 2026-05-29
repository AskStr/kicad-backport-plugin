# KiCad Backport

Copyright (C) askstar

Version 0.2.1

KiCad Backport cree une copie d'un projet ou fichier KiCad pouvant etre
ouverte avec une ancienne version de KiCad. Le projet original n'est pas
ecrase.

La version 0.2.1 prend en charge les projets enregistres par les versions
nocturnes actuelles de KiCad 10.99 et peut ecrire des copies compatibles avec
KiCad 10, KiCad 9, KiCad 8 ou KiCad 7.

## Langue

Le plugin utilise la langue choisie dans KiCad lorsque c'est possible. Si
aucun reglage de langue KiCad n'est trouve, il utilise la langue du systeme.

Langues prises en charge : anglais, chinois simplifie, chinois traditionnel,
francais, allemand et italien.

## Compatibilite multiplateforme

Le coeur de conversion de KiCad Backport est entierement implemente en Python
et s'execute dans le processus du plugin. Les binaires de conversion propres a
chaque plateforme ne sont plus necessaires pour une utilisation normale.

Systemes pris en charge :

- Windows
- macOS
- Linux

## Versions cibles

Versions d'entree prises en charge :

- KiCad 10.99 nightly
- KiCad 10
- KiCad 9
- KiCad 8
- KiCad 7

Versions de sortie prises en charge :

- KiCad 10
- KiCad 9
- KiCad 8
- KiCad 7

## Installation

1. Fermez KiCad.
2. Copiez tout le dossier `kicad_backport` dans le dossier utilisateur
   `plugins` de KiCad.
3. Pour KiCad 10.99 et les plugins API plus recents, utilisez le dossier
   utilisateur versionne, par exemple
   `C:\Users\<vous>\Documents\KiCad\10.99\plugins`.
4. Dans KiCad 10.99, activez KiCad API/API server dans les preferences; sinon
   KiCad ne detecte pas et ne charge pas les plugins API.
5. Pour les anciennes versions de KiCad, copiez aussi ce dossier dans
   `scripting/plugins`.
6. Redemarrez KiCad.
7. Lancez `Creer un backport KiCad`.

Dans KiCad 10.99, les plugins API ne sont pas charges depuis le dossier de
scripts integre a l'installation, par exemple `share/kicad/scripting/plugins`;
utilisez plutot le dossier utilisateur `plugins` et verifiez que KiCad API/API
server est active.

## Utilisation

1. Choisissez un fichier ou dossier de projet KiCad.
2. Choisissez un fichier ou dossier de sortie different.
3. Selectionnez la version KiCad cible.
4. Cliquez sur `Convertir`.

Verifiez la copie convertie dans la version KiCad cible avant de la partager ou
de l'utiliser pour la fabrication.
