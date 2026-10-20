# Paralliance

Annuaire des clubs de sport qui accueillent les personnes en situation de handicap, partout en France (métropole et outre-mer).
Site web et application téléphone (PWA installable) : https://monclubhandi.github.io/mon-club-handi/

## Comment ça marche
- **Données** : une base Supabase (table `clubs`, voir `supabase/`), lue en direct par l'appli à chaque ouverture.
  La clé publique ne permet que la lecture des clubs publiés (règle de sécurité RLS).
- **Appli / site** : `index.html` (recherche, filtres sport / département / handicap, « Autour de moi »,
  carte interactive OpenStreetMap avec regroupement des clubs, fiches avec créneaux, accès, séance d'essai, contact).
- **Téléphone** : `manifest.webmanifest` + `sw.js` rendent le site installable sur l'écran d'accueil
  (Android : « Installer l'application » ; iPhone : Safari → Partager → « Sur l'écran d'accueil ») et utilisable
  hors connexion avec la dernière copie des données.
- **Référencement** : `sitemap.xml` et `robots.txt` pour Google Search Console.
- **Scraper** : `scraper/` collecte des fiches du Handiguide des sports au format du tableau (voir son README).

## Un club = une fiche
La colonne `sport` peut contenir plusieurs sports séparés par des virgules. La base refuse les doublons
(même nom, sans tenir compte des majuscules/espaces/tirets, et même code postal) : voir `supabase/03_un_club_une_fiche.sql`.
Les imports utilisent `on conflict do nothing` : on peut les relancer sans créer de doublon.

## Sources importées
- `supabase/import_34_clubs.sql` : les premiers clubs (Île-de-France).
- `supabase/04_import_doubs.sql` : 120 structures du Doubs et alentours, généré par `supabase/import_doubs.py` depuis
  l'annuaire parasport du Département du Doubs (plateforme Oz, data.gouv.fr, licence ODbL : attribution dans le pied de page).
- `supabase/05_import_cotes_armor.sql` : 98 structures, généré par `supabase/import_cotes_armor.py` (lecture des tableaux du
  « Guide des associations accueillantes 2019-2021 » du Département des Côtes-d'Armor, partie handicap). Le guide ne donne que
  la commune : `code_postal` contient le numéro du département et l'appli géocode la commune.

## Table `clubs` (Supabase)
`sport, nom, adresse, code_postal, ville, handicaps, pratique, creneaux, accessibilite, telephone, email, site,
label, para_sportifs, encadrant_forme, verifie_le, essai, latitude, longitude, source, publie`

- **handicaps** : `visuel, auditif, moteur, mental, psychique, autisme, polyhandicap` séparés par des virgules.
- **pratique** : `handisport`, `sport adapte` ou `les deux`.
- **creneaux** : `Catégorie : jours et horaires` séparés par des points-virgules.
- **para_sportifs / encadrant_forme** : cases à cocher (donnent le badge « Club de confiance »).
- **publie** : décocher pour masquer un club sans le supprimer.

## Inscriptions de clubs (formulaire)
Les boutons « Proposer / Inscrire un club » ouvrent un formulaire qui écrit directement dans la table `clubs`,
avec `publie = false` et `source = 'formulaire'` (une ligne par sport). Pour valider : Table Editor → clubs →
filtre `publie` = false → vérifier → cocher `publie`. Les colonnes privées `propose_par`, `message`, `propose_le`
ne sont jamais lisibles depuis le site (`supabase/02_propositions.sql`). Une nouvelle colonne publique doit être
ajoutée au `grant select (...)` de ce fichier et à `PUBLIC_COLS` dans `index.html`.

Import d'un CSV (export Sheets ou scraper) : `python supabase/csv_vers_sql.py fichier.csv > import.sql`,
puis coller `import.sql` dans le SQL Editor de Supabase.
