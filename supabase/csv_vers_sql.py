"""Convertit un export CSV (Google Sheets ou scraper) en requête SQL à coller dans Supabase (SQL Editor).

Utilisation : python csv_vers_sql.py clubs.csv > import.sql
"""
import csv
import re
import sys
import unicodedata


def norm(s):
    s = unicodedata.normalize("NFD", s or "")
    return "".join(c for c in s if unicodedata.category(c) != "Mn").lower().strip()


# Titre de colonne du CSV (sans accents ni majuscules) -> colonne de la table clubs
COLONNES = {
    "sport": "sport", "nom": "nom", "adresse": "adresse", "code postal": "code_postal", "ville": "ville",
    "handicaps": "handicaps", "pratique": "pratique", "creneaux": "creneaux", "accessibilite": "accessibilite",
    "telephone": "telephone", "email": "email", "site": "site", "label": "label",
    "para sportifs au club": "para_sportifs", "encadrant forme": "encadrant_forme", "verifie le": "verifie_le",
    "essai": "essai", "latitude": "latitude", "longitude": "longitude", "source": "source",
}
BOOLEENS = {"para_sportifs", "encadrant_forme"}
NOMBRES = {"latitude", "longitude"}
# Même sport écrit de deux façons -> une seule orthographe
SPORTS = {"athletisme": "athlétisme", "equitation": "équitation", "cecifoot": "cécifoot", "randonnee": "randonnée"}


def sql(col, v):
    v = (v or "").strip()
    if col in BOOLEENS:
        return "true" if norm(v) in ("oui", "yes", "x", "1", "vrai", "true") else "false"
    if not v:
        return "null"
    if col in NOMBRES:
        return str(float(v.replace(",", ".")))
    if col == "verifie_le":
        m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})$", v)
        v = f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}" if m else v
    if col == "sport":
        v = SPORTS.get(norm(v), v.lower())
    if col == "site" and not re.match(r"^https?://", v, re.I):
        v = "https://" + v
    return "'" + v.replace("'", "''") + "'"


def convertir(lignes, nom_source=""):
    """Liste de dictionnaires {titre de colonne: valeur} -> requête SQL d'import dans la table clubs."""
    if not lignes:
        return "-- aucune ligne à importer\n"
    titres = {t: COLONNES[norm(t)] for t in lignes[0] if t and norm(t) in COLONNES}
    cols = list(titres.values())
    valeurs = []
    for l in lignes:
        if not (l.get("Nom") or l.get("nom") or "").strip():
            continue
        valeurs.append("  (" + ", ".join(sql(c, l.get(t)) for t, c in titres.items()) + ")")
    return (f"-- {len(valeurs)} lignes importées depuis {nom_source}\n"
            f"insert into public.clubs ({', '.join(cols)}) values\n" + ",\n".join(valeurs) + ";\n")


def main(chemin):
    with open(chemin, encoding="utf-8-sig") as f:
        print(convertir(list(csv.DictReader(f)), chemin.replace("\\", "/").split("/")[-1]), end="")


if __name__ == "__main__":
    main(sys.argv[1])
