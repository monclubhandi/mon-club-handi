# Mon club handisport

Annuaire des clubs de sport qui accueillent les personnes en situation de handicap en Île-de-France.
Site web et application téléphone (PWA installable) : https://monclubhandi.github.io/mon-club-handi/

## Comment ça marche
- **Données** : un Google Sheets publié en CSV, lu en direct par l'appli à chaque ouverture.
- **Appli / site** : `index.html` (recherche, filtres sport / département / handicap, « Autour de moi »,
  carte OpenStreetMap, fiches avec créneaux, accès, séance d'essai, contact).
- **Téléphone** : `manifest.webmanifest` + `sw.js` rendent le site installable sur l'écran d'accueil
  (Android : « Installer l'application » ; iPhone : Safari → Partager → « Sur l'écran d'accueil ») et utilisable
  hors connexion avec la dernière copie des données.
- **Référencement** : `sitemap.xml` et `robots.txt` pour Google Search Console.
- **Scraper** : `scraper/` collecte des fiches du Handiguide des sports au format du tableau (voir son README).

## Colonnes du Google Sheets
`Sport · Nom · Adresse · Code postal · Ville · Handicaps · Pratique · Creneaux · Accessibilite · Telephone ·
Email · Site · Label · Para sportifs au club · Encadrant forme · Verifie le · Essai · Latitude · Longitude · Source`

L'appli lit les colonnes par leur titre : l'ordre n'a pas d'importance et les colonnes Essai, Latitude,
Longitude et Source sont facultatives.
- **Handicaps** : `visuel, auditif, moteur, mental, psychique, autisme, polyhandicap` séparés par des virgules.
- **Pratique** : `handisport`, `sport adapte` ou `les deux`.
- **Creneaux** : `Catégorie : jours et horaires` séparés par des points-virgules.
- **Para sportifs au club / Encadrant forme** : `oui` ou vide (donne le badge « Club de confiance »).
