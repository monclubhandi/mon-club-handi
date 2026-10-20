"""Import de l'« Annuaire des associations et clubs proposant une activité parasportive » (Département du Doubs,
plateforme Oz, data.gouv.fr, licence ODbL) dans la table clubs.

Utilisation : python import_doubs.py annuaire.csv > 04_import_doubs.sql
"""
import csv
import sys

from csv_vers_sql import cle, requete, normaliser_sports

SOURCE = "Annuaire parasport du Doubs, plateforme Oz (data.gouv.fr, ODbL)"


def oui(v):
    return (v or "").strip().lower() == "oui"


def fiche(r):
    handicaps = []
    if oui(r["Handicap moteur"]):
        handicaps.append("moteur")
    if oui(r["Handicap sensoriel"]):
        handicaps += ["visuel", "auditif"]
    if oui(r["Handicap intellectuel"]):
        handicaps.append("mental")
    if oui(r["Handicap psychique"]):
        handicaps.append("psychique")
    if oui(r["Handicap autistique"]):
        handicaps.append("autisme")
    physique = any(h in handicaps for h in ("moteur", "visuel", "auditif"))
    adapte = any(h in handicaps for h in ("mental", "psychique", "autisme"))
    pratique = "les deux" if physique and adapte else "sport adapte" if adapte else "handisport" if physique else ""

    acces = []
    lieu = r["Lieu de pratique"].strip()
    if lieu:
        acces.append("Lieu de pratique : " + lieu)
    niveaux = [n for n, col in (("loisir", "Pratique loisirs"), ("compétition", "Pratique compétition")) if oui(r[col])]
    if niveaux:
        acces.append("Pratique : " + " et ".join(niveaux))
    if oui(r["Intervention à domicile"]):
        acces.append("Intervention à domicile possible")

    lat = lon = ""
    if "," in r["Geo Point"]:
        lat, lon = [x.strip() for x in r["Geo Point"].split(",", 1)]

    # Le nom de la personne de contact n'est pas repris : seuls le téléphone et l'email publiés pour l'annuaire le sont
    return {
        "sport": ", ".join(normaliser_sports(r["Activités proposées"])) or "multisport",
        "nom": r["Nom de l'association"].strip(),
        "adresse": r["Adresse"].strip(), "code_postal": r["Code postal"].strip(), "ville": r["Ville"].strip(),
        "handicaps": ", ".join(dict.fromkeys(handicaps)), "pratique": pratique,
        "accessibilite": ". ".join(acces), "telephone": r["Téléphone"].strip(), "email": r["Mail"].strip(),
        "latitude": lat, "longitude": lon, "source": SOURCE,
    }


def main(chemin):
    with open(chemin, encoding="utf-8-sig") as f:
        lignes = list(csv.DictReader(f, delimiter=";"))
    # Une association présente sur plusieurs lieux (ex. Escapa'd) = une seule fiche : on garde le lieu
    # qui propose le plus d'activités et on y réunit tous ses sports
    par_nom = {}
    for f in (fiche(r) for r in lignes if r["Nom de l'association"].strip()):
        k = cle(f["nom"], "")
        if k not in par_nom:
            par_nom[k] = f
            continue
        g = par_nom[k]
        base, autre = (f, g) if len(f["sport"]) > len(g["sport"]) else (g, f)
        base["sport"] = ", ".join(dict.fromkeys(base["sport"].split(", ") + autre["sport"].split(", ")))
        par_nom[k] = base
    print(requete(list(par_nom.values()), SOURCE), end="")


if __name__ == "__main__":
    main(sys.argv[1])
