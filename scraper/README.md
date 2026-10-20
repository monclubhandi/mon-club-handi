# Scraper Handiguide → Supabase

Récupère les fiches du [Handiguide des sports](https://www.handiguide.sports.gouv.fr/) et les met au format
de la base Supabase de **Paralliance** (une ligne par sport et par lieu de pratique).

## Garde-fous intégrés
- vérifie le fichier `robots.txt` du site avant de commencer ;
- une fiche toutes les 3 secondes minimum (impossible de descendre plus bas) ;
- saute les clubs déjà présents dans ta base Supabase ;
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
- `nouveaux_clubs.csv` : ouvre-le dans Excel ou LibreOffice pour **vérifier** les clubs avant l'import
  (supprime les lignes douteuses si besoin, puis relance `python ../supabase/csv_vers_sql.py nouveaux_clubs.csv > nouveaux_clubs.sql`).
- `nouveaux_clubs.sql` : ouvre-le avec un éditeur de texte, copie tout, et colle-le dans Supabase
  (**SQL Editor → New query → Run**). Les clubs apparaissent aussitôt dans l'appli.

Les colonnes `latitude`/`longitude` (calculées avec la Base Adresse Nationale) permettent à l'appli d'afficher
la carte instantanément, même avec 800 clubs. `creneaux` et `verifie_le` restent vides : c'est ta valeur
ajoutée, à remplir dans Supabase après contact avec le club.

## Tests
```
python tests/test_parse.py
```
Les tests utilisent 5 vraies fiches du Handiguide (contacts anonymisés) dans `tests/fixtures/`.

Si le site change et que le script affiche « 0 fiches trouvées » ou « Fiche illisible », relance avec
`--debug --test` et regarde (ou partage) les fichiers de debug.
