# Scraper Handiguide → Google Sheets

Récupère les fiches du [Handiguide des sports](https://www.handiguide.sports.gouv.fr/) et les met au format
du Google Sheets de **Mon club handisport** (une ligne par sport et par lieu de pratique).

## Garde-fous intégrés
- vérifie le fichier `robots.txt` du site avant de commencer ;
- une fiche toutes les 3 secondes minimum (impossible de descendre plus bas) ;
- saute les clubs déjà présents dans le Google Sheets ;
- reprend là où il s'était arrêté en cas d'interruption (`.progression.json`).

À savoir : les fiches contiennent des contacts parfois personnels (RGPD) et la base est protégée par le droit
des producteurs de bases de données. Le plus sûr reste de demander un export au Centre d'Expertise Sport
Handicaps (CESH), qui anime le Handiguide, et de citer le Handiguide comme source dans l'appli (c'est fait
dans le pied de page).

## Installation (une seule fois, sur ordinateur)
```
pip install -r requirements.txt
playwright install chromium
```

## Utilisation
```
# 1. Test sur 5 fiches
python handiguide_scraper.py "https://www.handiguide.sports.gouv.fr/recherche-structure?x=2.36&y=48.93&distance=15&location=93200%20Saint-Denis,%20France" --test

# 2. Collecte complète (même commande sans --test). Relancer la même commande reprend après une coupure.
python handiguide_scraper.py "https://www.handiguide.sports.gouv.fr/recherche-structure?..."
```

Options utiles :

| Option | Effet |
|---|---|
| `--test` | 5 fiches seulement |
| `--limite 50` | 50 fiches au maximum |
| `--pause 5` | 5 secondes entre deux fiches |
| `--sans-geo` | ne calcule pas Latitude/Longitude |
| `--recommencer` | oublie la progression enregistrée |
| `--visible` | affiche le navigateur pendant la collecte |
| `--debug` | enregistre les pages lues (`debug_recherche.html`, `debug_fiches/`) pour ajuster le script |
| `--fichier fiches.txt` | lit des fiches copiées-collées (séparées par « Fiche 1 : », « Fiche 2 : »…) sans aller sur le site |

## Résultat
- `nouveaux_clubs.tsv` : sans titres. Ouvre-le avec un éditeur de texte, copie tout, colle dans la
  première ligne vide du Google Sheets (case A).
- `nouveaux_clubs.csv` : avec les titres, pour vérifier dans Excel/LibreOffice avant de coller.

Colonnes produites (A à T), à avoir dans cet ordre dans le Google Sheets :

`Sport · Nom · Adresse · Code postal · Ville · Handicaps · Pratique · Creneaux · Accessibilite · Telephone ·
Email · Site · Label · Para sportifs au club · Encadrant forme · Verifie le · Essai · Latitude · Longitude · Source`

Les colonnes Q à T sont nouvelles : ajoute leurs titres dans le Sheets. `Latitude`/`Longitude` (calculées avec
la Base Adresse Nationale) permettent à l'appli d'afficher la carte instantanément, même avec 800 clubs.
`Creneaux` et `Verifie le` restent vides : c'est ta valeur ajoutée, à remplir après contact avec le club.

## Tests
```
python tests/test_parse.py
```
Les tests utilisent 5 vraies fiches du Handiguide (contacts anonymisés) dans `tests/fixtures/`.

Si le site change et que le script affiche « 0 fiches trouvées » ou « Fiche illisible », relance avec
`--debug --test` et regarde (ou partage) les fichiers de debug.
