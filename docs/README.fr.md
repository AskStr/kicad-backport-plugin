# KiCad Backport

Copyright (C) askstar

Version 0.0.2

KiCad Backport cree une copie d'un projet ou fichier KiCad pouvant etre
ouverte avec une ancienne version de KiCad. Le projet original n'est pas
ecrase.

## Langue

Le plugin utilise la langue choisie dans KiCad lorsque c'est possible. Si
aucun reglage de langue KiCad n'est trouve, il utilise la langue du systeme.

Langues prises en charge : anglais, chinois simplifie, chinois traditionnel,
francais, allemand et italien.

## Compatibilite multiplateforme

Systemes pris en charge :

- Windows x64 et Windows ARM64
- macOS Intel et Apple Silicon
- Linux x64 et Linux ARM64

Le plugin choisit automatiquement le convertisseur adapte au systeme.

## Versions cibles

- KiCad 10
- KiCad 9
- KiCad 8
- KiCad 7

## Installation

1. Fermez KiCad.
2. Copiez tout le dossier `kicad_backport` dans le dossier `plugins` de KiCad.
3. Pour les anciennes versions de KiCad, copiez aussi ce dossier dans
   `scripting/plugins`.
4. Redemarrez KiCad.
5. Lancez `Creer un backport KiCad`.

## Utilisation

1. Choisissez un fichier ou dossier de projet KiCad.
2. Choisissez un fichier ou dossier de sortie different.
3. Selectionnez la version KiCad cible.
4. Cliquez sur `Convertir`.

Verifiez la copie convertie dans la version KiCad cible avant de la partager ou
de l'utiliser pour la fabrication.
