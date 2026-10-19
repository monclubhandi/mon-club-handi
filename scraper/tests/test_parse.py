"""Tests du découpage des fiches, sur 5 vraies fiches du Handiguide (contacts anonymisés).

Lancer : python -m pytest tests   (ou : python tests/test_parse.py)
"""
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import handiguide_scraper as hs  # noqa: E402

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "fiches_exemple.txt")


def fiches():
    with open(FIXTURE, encoding="utf-8") as f:
        blocs = re.split(r"(?im)^fiche\s*\d+\s*[:;]?", f.read())
    res = []
    for b in blocs:
        if b.strip():
            res += [dict(zip(hs.COLONNES, l)) for l in hs.parse_fiche(b)]
    return res


def test_cinq_fiches_lues():
    assert len(fiches()) == 5


def test_muay_thai():
    c = fiches()[0]
    assert c["Nom"] == "Muay Thaï Lumpini"
    assert c["Sport"] == "muay-thaï"
    assert c["Adresse"] == "10-12 Place des sports"
    assert (c["Code postal"], c["Ville"]) == ("93200", "Saint-Denis")
    assert c["Handicaps"] == "auditif, moteur, autisme"
    assert c["Pratique"] == "les deux"
    assert c["Accessibilite"].startswith("Complexe Sportif du Franc Moisin. Lieu accessible")
    assert c["Site"].startswith("https://www.facebook.com/Groupe")
    # "encadrants motivés et à l'écoute" ne suffit pas pour le badge
    assert c["Para sportifs au club"] == "" and c["Encadrant forme"] == ""
    assert c["Essai"].startswith("Les participants peuvent effectuer un cours d'essai gratuit")
    assert len(hs.COLONNES) == 20 and len(c) == 20


def test_randonnee_club_inclusif():
    c = fiches()[1]
    assert c["Nom"] == "Saint-Denis Union Sport Verts Sentiers"
    assert c["Handicaps"] == "visuel, auditif, psychique"
    assert c["Label"] == "Club inclusif"
    assert c["Para sportifs au club"] == "oui" and c["Encadrant forme"] == "oui"
    assert c["Site"] == ""  # le lien "Site du club inclusif" n'est pas le site du club


def test_lieu_sans_code_postal():
    c = fiches()[2]
    assert c["Adresse"] == "Rue du 19 Mars 1962"
    assert c["Ville"] == "Saint-Denis"
    assert c["Accessibilite"].startswith("la Raquette, Stade Auguste Delaune.")
    assert c["Site"] == "https://www.facebook.com/sdtt93/"


def test_lieu_colle_a_la_rue_sans_numero():
    c = fiches()[3]
    assert c["Adresse"] == "Avenue Roger Salengro"
    assert (c["Code postal"], c["Ville"]) == ("93120", "La Courneuve")
    assert "polyhandicap" in c["Handicaps"]


def test_basket():
    c = fiches()[4]
    assert c["Nom"] == "Saint Ouen Handibasket"
    assert (c["Adresse"], c["Code postal"], c["Ville"]) == ("2 Rue Pierre Curie", "93400", "Saint-Ouen")
    assert c["Pratique"] == "handisport"


def test_plusieurs_lieux_et_sports():
    texte = """Retourner aux résultats
Club Test
Activité sportive :
Natation, Tir à l'arc
Handicap(s)
Handicap moteur
Lieu de la pratique
Adresse n° 1
Piscine Oberkampf12 rue de Paris, 75011 Paris
Accessibilité du lieu
Rampe d'accès
Adresse n° 2
Gymnase Jean Bouin3 avenue Foch, 92100 Boulogne-Billancourt, France
Accessibilité du lieu
Ascenseur
Aller en haut de la page"""
    lignes = [dict(zip(hs.COLONNES, l)) for l in hs.parse_fiche(texte)]
    assert [(l["Sport"], l["Code postal"]) for l in lignes] == [
        ("natation", "75011"), ("tir à l'arc", "75011"), ("natation", "92100"), ("tir à l'arc", "92100")]
    assert lignes[2]["Accessibilite"] == "Gymnase Jean Bouin. Ascenseur"
    assert lignes[2]["Ville"] == "Boulogne-Billancourt"


def test_est_fiche():
    assert hs.est_fiche("https://www.handiguide.sports.gouv.fr/structure/1234")
    assert not hs.est_fiche("https://www.handiguide.sports.gouv.fr/recherche-structure?x=2")
    assert not hs.est_fiche("https://www.handiguide.sports.gouv.fr/inscription-structure")


if __name__ == "__main__":
    for nom, f in list(globals().items()):
        if nom.startswith("test_"):
            f()
            print("OK", nom)
