"""Import de clubs repérés dans les annuaires d'associations publiés en données ouvertes par des collectivités.

Sources (le programme télécharge les fichiers) :
  - Nantes Métropole, « Liste des associations évoluant à Nantes Métropole », Licence Ouverte 2.0
  - Orléans Métropole, « Annuaire des associations - Orléans », Licence Ouverte 2.0
  - Angers Loire Métropole, « Annuaire des associations - Angers », licence ODbL

Dans ces annuaires, chaque association décrit elle-même son activité. Le tableau RETENUS liste, après lecture une
par une, les associations sportives qui y disent proposer une pratique pour les personnes en situation de handicap
(section handisport, sport adapté, foot fauteuil…), avec les sports et les handicaps tirés de leur propre texte.
Ne sont pas retenus : comités et ligues, associations d'aide ou de soutien, clubs qui ne mentionnent qu'un tarif ou une
journée de découverte, et (Nantes) les fiches que l'association n'a pas mises à jour depuis plus de 3 ans.

Ni l'adresse du siège (souvent le domicile d'un bénévole), ni le nom du responsable, ni un mail personnel ne sont repris.

Utilisation : python import_annuaires_ouverts.py > 15_import_annuaires_ouverts.sql
              python import_annuaires_ouverts.py dossier > 15_import_annuaires_ouverts.sql   (fichiers déjà téléchargés)
"""
import json
import ssl
import sys
import time
import urllib.request

from csv_vers_sql import requete
from import_eure import mail_du_club

SOURCES = {
    "nantes": ("Nantes Métropole, annuaire des associations (Licence Ouverte 2.0)",
               "https://data.nantesmetropole.fr/api/explore/v2.1/catalog/datasets/244400404_associations_nantes_metropole/exports/json"),
    "orleans": ("Orléans Métropole, annuaire des associations (Licence Ouverte 2.0)",
                "https://data.orleans-metropole.fr/api/explore/v2.1/catalog/datasets/om-vieassociative-annuaire/exports/json"),
    "angers": ("Angers Loire Métropole, annuaire des associations (ODbL)",
               "https://data.angers.fr/api/explore/v2.1/catalog/datasets/annuaire_asso_angers/exports/json"),
}

# source, nom exact dans l'annuaire, nom affiché, sports, handicaps, pratique
RETENUS = [
    ("nantes", "Club Sportif des Sourds de Nantes", "Club Sportif des Sourds de Nantes", "multisport", "auditif", "handisport"),
    ("nantes", "Elan Sport Adapté", "Elan Sport Adapté", "multisport", "mental, psychique", "sport adapte"),
    ("nantes", "Nantes Sports de Glace", "Nantes Sports de Glace", "patinage artistique", "", "sport adapte"),
    ("nantes", "Nantes - Foot Fauteuil", "Nantes Foot Fauteuil", "foot fauteuil", "moteur", "handisport"),
    ("nantes", "Racing Club Nantais", "Racing Club Nantais", "athlétisme", "", "les deux"),
    ("nantes", "Ensemble pour le Sport Handisport 44", "Ensemble pour le Sport Handisport 44", "multisport",
     "moteur, visuel, auditif", "handisport"),
    ("nantes", "Rollers Bongo Nantes", "Rollers Bongo Nantes", "roller, danse", "", ""),
    ("nantes", "L'Îlot Familles", "L'Îlot Familles", "cyclisme", "", ""),
    ("orleans", "Inter Omnisports des Sourds d'Orléans", "Inter Omnisports des Sourds d'Orléans", "pétanque", "auditif", "handisport"),
    ("orleans", "L'Etape Solognote", "L'Étape Solognote", "cyclisme", "", ""),
    ("orleans", "NEUVILLE SPORTS", "Neuville Sports", "football", "", ""),
    ("orleans", "Association Handisport Orléanais", "Association Handisport Orléanais", "basket fauteuil, natation, tir à l'arc, tennis",
     "moteur, visuel", "handisport"),
    ("orleans", "Union Sportive Orléanaise Tennis de Table", "Union Sportive Orléanaise Tennis de Table", "tennis de table", "", ""),
    ("orleans", "Orléans Métropole Académie", "Orléans Métropole Académie", "football, futsal", "", "handisport"),
    ("orleans", "Club Handisport Adapté de la Métropole Orléanaise", "Club Handisport Adapté de la Métropole Orléanaise",
     "multisport", "", "les deux"),
    ("orleans", "Aviron Club Orléans Olivet", "Aviron Club Orléans Olivet", "aviron", "", "les deux"),
    ("angers", "ASS. ANGEVINE DU SPORT ADAPTE", "Association Angevine du Sport Adapté", "multisport", "mental", "sport adapte"),
    ("angers", "LES LOUPS D'ANGERS TENNIS DE TABLE", "Les Loups d'Angers Tennis de Table", "tennis de table", "", "handisport"),
    ("angers", "SCO ESCRIME - SECTION JEAN DE MALEZIEU", "SCO Escrime Angers", "escrime", "", "handisport"),
    ("angers", "HANDISPORT ANGERS", "Handisport Angers", "multisport", "moteur, visuel, auditif", "handisport"),
    ("angers", "CLUB DE L'ESPERANCE", "Club de l'Espérance", "multisport", "mental", "sport adapte"),
]
# Siège en boîte postale (Cedex) : on garde la commune du lieu de pratique indiqué par l'association
CORRECTIONS = {"Aviron Club Orléans Olivet": {"cp": "45160", "ville": "Olivet"}}
MAILS_NOMINATIFS = {"patrick.fourastie@gmail.com", "j_boutin@orange.fr"}     # prénom.nom d'une personne


def telecharger(url, essais=5):
    req = urllib.request.Request(url, headers={"User-Agent": "Paralliance (contact@paralliance.org)"})
    for i in range(essais):                                       # les serveurs coupent parfois la connexion
        try:
            with urllib.request.urlopen(req, timeout=120, context=ssl.create_default_context()) as r:
                return json.load(r)
        except OSError:
            if i == essais - 1:
                raise
            time.sleep(5 * (i + 1))


def site(u):
    u = (u or "").strip()
    if not u or " " in u:
        return ""
    return u if u.startswith("http") else "https://" + u


def fiche(source, r):
    if source == "nantes":
        return {"cp": str(r.get("siege_cp") or ""), "ville": (r.get("siege_commune") or "").title(),
                "tel": r.get("tel") or "", "mail": r.get("mail") or "", "site": r.get("lien1") or "", "lieux": ""}
    if source == "orleans":
        adresse = r.get("adresse_complete_pour_geocodage") or ""
        cp = next((m for m in adresse.split() if m.isdigit() and len(m) == 5), "")
        return {"cp": cp, "ville": adresse.split(cp, 1)[1].strip() if cp else "",
                "tel": r.get("siege_social_tel") or "", "mail": r.get("siege_social_email") or "",
                "site": r.get("siege_social_www") or "", "lieux": (r.get("lieux_pratique") or "").replace("\n", " ").strip()}
    return {"cp": r.get("code_postal") or "", "ville": (r.get("ville") or "").title(), "tel": r.get("telephone_1") or "",
            "mail": r.get("mail") or "", "site": r.get("site_web") or "", "lieux": ""}


def fiches():
    if len(sys.argv) > 1:                                         # dossier où les fichiers sont déjà téléchargés
        donnees = {k: json.load(open(f"{sys.argv[1]}/{k}.json", encoding="utf-8")) for k in SOURCES}
    else:
        donnees = {k: telecharger(url) for k, (_, url) in SOURCES.items()}
    for source, cle, nom, sports, handicaps, pratique in RETENUS:
        champ = {"nantes": "nom", "orleans": "nom", "angers": "nom_long"}[source]
        r = next((x for x in donnees[source] if (x.get(champ) or "").strip() == cle), None)
        if r is None:
            print(f"-- introuvable dans l'annuaire {source} : {cle}", file=sys.stderr)
            continue
        f = fiche(source, r) | CORRECTIONS.get(nom, {})
        mail = "" if f["mail"].lower() in MAILS_NOMINATIFS else mail_du_club(f["mail"], nom, "")
        tel = f["tel"].replace(" ", "")
        yield {
            "sport": sports, "nom": nom, "code_postal": f["cp"], "ville": f["ville"], "handicaps": handicaps,
            "pratique": pratique,
            "accessibilite": " ".join(x for x in (
                "" if handicaps else "L'association indique accueillir les personnes en situation de handicap.",
                f"Lieux de pratique : {f['lieux']}" if f["lieux"] else "") if x),
            "telephone": " ".join(tel[i:i + 2] for i in range(0, len(tel), 2)) if len(tel) == 10 else f["tel"],
            "email": mail, "site": site(f["site"]), "source": SOURCES[source][0],
        }


if __name__ == "__main__":
    print(requete(list(fiches()), "annuaires d'associations ouverts (Nantes, Orléans, Angers)"), end="")
