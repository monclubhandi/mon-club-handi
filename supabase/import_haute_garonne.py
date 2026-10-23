"""Import de l'« Annuaire des clubs handisport 2025-2026 » du Comité départemental Handisport de la Haute-Garonne
dans la table clubs.

Le PDF présente chaque club sur deux lignes : « NOM DU CLUB - COMMUNE » puis la liste des sports, avec le
téléphone du club à droite. La page 1 a deux colonnes, la page 2 une seule. On lit la position de chaque ligne
(pdftotext -bbox-layout) et on rattache chaque téléphone au titre de club le plus proche dans sa colonne.

Le guide ne donne que la commune : le code postal est remplacé par le numéro du département (31), l'appli place
le club sur la carte à partir du nom de la commune. Seul le handicap écrit dans l'annuaire est repris
(« sourds » -> auditif, « DV » -> visuel).

Utilisation : python import_haute_garonne.py annuaire.pdf > 07_import_haute_garonne.sql   (nécessite pdftotext)
"""
import html
import re
import subprocess
import sys

from csv_vers_sql import normaliser_sports, requete

SOURCE = "Annuaire des clubs handisport 2025-2026, Comité départemental Handisport de la Haute-Garonne"
PHONE = re.compile(r"0\d(?: \d\d){4}")


def lignes(pdf):
    xml = subprocess.run(["pdftotext", "-bbox-layout", pdf, "-"], capture_output=True, text=True).stdout
    for num, page in enumerate(xml.split("<page ")[1:]):
        for m in re.finditer(r'<line xMin="([\d.]+)" yMin="([\d.]+)"[^>]*>(.*?)</line>', page, re.S):
            txt = " ".join(html.unescape(w) for w in re.findall(r">([^<]+)</word>", m.group(3)))
            yield num, float(m.group(1)), float(m.group(2)), txt



def fiches(pdf):
    clubs, tels = [], []
    for page, x, y, txt in lignes(pdf):
        if page == 1 and y > 590:              # pied de page : coordonnées du comité, pas un club
            continue
        col = (page, 0 if page == 1 or x < 300 else 1)
        lettres = [c for c in txt if c.isalpha()]
        majuscules = sum(c.isupper() for c in lettres) / max(len(lettres), 1)
        tel = PHONE.search(txt)
        if tel and not txt.replace(tel.group(), "").strip():
            tels.append((col, y, tel.group()))
            continue
        if majuscules > 0.8 and re.search(r"\s-\s|-\s|\s-$", txt) and not txt.startswith("SPORTS"):
            if tel:                            # téléphone sur la même ligne que le nom
                tels.append((col, y, tel.group()))
                txt = txt.replace(tel.group(), "").strip()
            nom, ville = txt.rsplit(" - ", 1) if " - " in txt else txt.split("- ", 1)
            clubs.append({"col": col, "y": y, "nom": nom.strip(), "ville": ville.strip(), "sports": []})
        elif majuscules < 0.8 and clubs:
            # Ligne de sports : elle appartient au dernier club de la même colonne
            dernier = [c for c in clubs if c["col"] == col]
            if dernier:
                dernier[-1]["sports"].append(txt)
    for col, y, tel in tels:                   # chaque téléphone va au club le plus proche dans sa colonne
        proches = [c for c in clubs if c["col"] == col]
        min(proches, key=lambda c: abs(c["y"] - y))["telephone"] = tel
    for c in clubs:
        texte_sports = " ".join(c["sports"])
        handicaps = (["auditif"] if re.search(r"sourd", texte_sports, re.I) else []) + (["visuel"] if re.search(r"\bDV\b", texte_sports) else [])
        villes = [v.strip() for v in re.split(r"\s*&\s*", c["ville"])]
        yield {
            "sport": ", ".join(normaliser_sports(texte_sports.replace(" Randonnée pédestre", ", Randonnée pédestre"))),
            "nom": titre(c["nom"]), "code_postal": "31", "ville": titre(villes[0]),
            "handicaps": ", ".join(handicaps), "pratique": "handisport",
            "accessibilite": "Lieux de pratique : " + ", ".join(titre(v) for v in villes) if len(villes) > 1 else "",
            "telephone": c.get("telephone", ""), "source": SOURCE,
        }


def titre(s):
    """« TOULOUSE UNIVERSITE CLUB » -> « Toulouse Universite Club » (petits mots en minuscules)."""
    petits = {"de", "du", "des", "la", "le", "les", "et", "sur", "en", "d", "l"}
    mots = re.split(r"(\s+|-|'|’)", s.lower())
    out, premier = [], True
    for m in mots:
        if not m.strip() or m in "-'’":
            out.append(m)
            continue
        out.append(m if (m in petits and not premier) else m[:1].upper() + m[1:])
        premier = False
    res = "".join(out)
    res = res.replace("A.s.e.i.", "A.S.E.I.")
    return re.sub(r"\b(Asptt|Apf|Saa|Xv|Tag|Unadev|Cesdda|Toac)\b", lambda m: m.group(1).upper(), res)


if __name__ == "__main__":
    print(requete(list(fiches(sys.argv[1])), SOURCE), end="")
