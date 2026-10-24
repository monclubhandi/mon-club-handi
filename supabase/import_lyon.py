"""Import des « Structures du réseau Sport-Santé Adapté Handicap » de la Métropole de Lyon dans la table clubs.

Source : data.grandlyon.com (Métropole de Lyon), Licence Ouverte 2.0 : réutilisation libre en citant la source.
Le fichier (GeoJSON) donne pour chaque structure : nom, discipline, publics accueillis, adresse, commune,
mail et position. Le téléchargement se fait par le programme, rien n'est recopié à la main.

Ne sont repris que les structures qui accueillent au moins un handicap (pas celles réservées aux maladies
chroniques). Les comités, districts, ligues et l'antenne nationale de Special Olympics ne sont pas des clubs :
ils sont écartés. Un mail qui contient le nom d'une personne n'est pas repris.

Utilisation : python import_lyon.py > 12_import_lyon.sql            (télécharge le fichier)
              python import_lyon.py fichier.geojson > 12_import_lyon.sql
"""
import json
import re
import ssl
import sys
import urllib.request

from csv_vers_sql import requete
from import_eure import mail_du_club, titre

SOURCE = "Métropole de Lyon, réseau Sport-Santé Adapté Handicap (data.grandlyon.com, Licence Ouverte 2.0)"
URL = ("https://data.grandlyon.com/geoserver/metropole-de-lyon/ows?SERVICE=WFS&VERSION=2.0.0&request=GetFeature"
       "&typename=metropole-de-lyon:sport_nature.sport_adapte&outputFormat=application/json&SRSNAME=EPSG:4326")
PUBLICS = {"handicap moteur": "moteur", "handicap sensoriel (handicap auditif)": "auditif",
           "handicap sensoriel (handical visuel)": "visuel", "handicap mental ou déficience intellectuelle": "mental",
           "handicap cognitif ou psychique": "psychique"}
DISCIPLINES = {"basketball": "basket", "basket-fauteuil": "basket fauteuil", "hand-fauteuil": "hand fauteuil",
               "canoë-kayac": "canoë-kayak", "multiactivités": "multisport", "omnisports": "multisport",
               "volley ball": "volley-ball", "apa": "activités physiques adaptées", "boxe anglaise": "boxe",
               "danse contemporaine": "danse"}
PAS_DES_CLUBS = re.compile(r"^(COMIT|DISTRICT|LIGUE|SPECIAL OLYMPICS)", re.I)
MAILS_NOMINATIFS = {"yassin.arbib@omsvaulxenvelin.com"}     # prénom.nom d'une personne


def sigles(nom):
    """Les sigles restent en majuscules : « Fc Lyon » -> « FC Lyon »."""
    return re.sub(r"\b(Fc|Asul|Algm|Ants|Cro|Gr|Asmc|Lou)\b", lambda m: m.group(1).upper(), nom)


def structures(fichier=None):
    if fichier:
        return json.load(open(fichier, encoding="utf-8"))["features"]
    ctx = ssl.create_default_context()
    req = urllib.request.Request(URL, headers={"User-Agent": "Paralliance (contact@paralliance.org)"})
    with urllib.request.urlopen(req, timeout=60, context=ctx) as r:
        return json.load(r)["features"]


def fiches(features):
    for f in features:
        p = f["properties"]
        publics = p.get("public_cible") or []
        h = [PUBLICS[x] for x in PUBLICS if x in publics]
        sensoriel = "handicap sensoriel" in publics                  # sans préciser visuel ou auditif
        if not (h or sensoriel) or PAS_DES_CLUBS.match(p["nom"]):
            continue
        physique = any(x in h for x in ("moteur", "visuel", "auditif")) or sensoriel
        adapte = any(x in h for x in ("mental", "psychique"))
        discipline = (p.get("discipline") or "").strip()
        mail = (p.get("email") or "").lower()
        lon, lat = f["geometry"]["coordinates"] if f.get("geometry") else (None, None)
        yield {
            "sport": DISCIPLINES.get(discipline.lower(), discipline), "nom": sigles(titre(p["nom"])),
            "adresse": titre(p.get("adresse") or ""), "code_postal": p.get("code_postal"),
            "ville": re.sub(r" (\d+(?:er|e)) Arrondissement$", r" \1", p.get("commune") or ""),
            "handicaps": ", ".join(h),
            "pratique": "les deux" if physique and adapte else "sport adapte" if adapte else "handisport",
            "accessibilite": "Accueille les personnes en situation de handicap sensoriel" if sensoriel else "",
            "email": "" if mail in MAILS_NOMINATIFS else mail_du_club(mail, p["nom"], ""),
            "latitude": str(lat) if lat else "", "longitude": str(lon) if lon else "",
            "label": "Réseau Sport-Santé Adapté Handicap (Métropole de Lyon)", "source": SOURCE,
        }


if __name__ == "__main__":
    print(requete(list(fiches(structures(sys.argv[1] if len(sys.argv) > 1 else None))), SOURCE), end="")
