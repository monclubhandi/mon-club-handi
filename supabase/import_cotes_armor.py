"""Import du « Guide des associations accueillantes – activités physiques adaptées en Côtes d'Armor 2019-2021 »
(Département des Côtes-d'Armor, partie 1 : handicap) dans la table clubs.

Le guide présente 4 activités par page dans des tableaux (commune, discipline, âge, déficiences, structure,
contact, infos). On lit la position de chaque ligne de texte (pdftotext -bbox-layout) pour reconstituer les
tableaux, y compris les cases fusionnées sur plusieurs colonnes. Une structure = une fiche : ses activités
sont réunies, ses autres communes de pratique sont indiquées dans l'accès.

Le guide ne donne que la commune : le code postal est remplacé par le numéro du département (22, ou 35… quand
le guide l'indique), l'appli place le club sur la carte à partir du nom de la commune.

Utilisation : python import_cotes_armor.py guide.pdf > 05_import_cotes_armor.sql   (nécessite pdftotext)
"""
import html
import re
import subprocess
import sys

from csv_vers_sql import cle, normaliser_sports, requete

SOURCE = "Guide des associations accueillantes 2019-2021, Département des Côtes-d'Armor"
PAGES = (11, 51)                           # partie 1 : handicap (la partie 2 concerne les troubles de santé)
COLONNES = [(174, 326), (326, 480), (480, 633), (633, 790)]
LIBELLES = {"Communes": "commune", "Disciplines": "discipline", "Catégorie": "age", "Type de": "deficience",
            "Structures": "structure", "Contact": "contact", "Informations": "infos"}
DEFICIENCES = {"motrice": "moteur", "visuelle": "visuel", "auditive": "auditif", "mentale": "mental", "psychique": "psychique"}
PHONE = re.compile(r"0\d(?:\s?\d\d){4}")
EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
# Mots qui appartiennent forcément à la ligne « âge » ou « déficience » (cases hautes qui débordent)
MOTS_AGE = re.compile(r"^(enfants|adolescents|adultes|seniors|tout âge|tous âges)\b", re.I)
MOTS_DEFICIENCE = re.compile(r"^(motrice|visuelle|auditive|mentale|psychique|contacter le club)\b", re.I)


def lignes_par_page(pdf):
    xml = subprocess.run(["pdftotext", "-f", str(PAGES[0]), "-l", str(PAGES[1]), "-bbox-layout", pdf, "-"],
                         capture_output=True, text=True, check=True).stdout
    for page in xml.split("<page ")[1:]:
        lignes = []
        for m in re.finditer(r'<line xMin="[\d.]+" yMin="([\d.]+)" xMax="[\d.]+" yMax="([\d.]+)">(.*?)</line>', page, re.S):
            y = (float(m.group(1)) + float(m.group(2))) / 2
            mots = [(float(a), float(b), html.unescape(w)) for a, b, w in
                    re.findall(r'<word xMin="([\d.]+)" yMin="[\d.]+" xMax="([\d.]+)" yMax="[\d.]+">([^<]+)</word>', m.group(3))]
            # pdftotext colle parfois sur une même ligne les textes de colonnes voisines : on coupe aux grands espaces
            morceau = []
            for mot in mots:
                if morceau and mot[0] - morceau[-1][1] > 12:
                    lignes.append((morceau[0][0], y, morceau[-1][1], " ".join(w for _, _, w in morceau)))
                    morceau = []
                morceau.append(mot)
            if morceau:
                lignes.append((morceau[0][0], y, morceau[-1][1], " ".join(w for _, _, w in morceau)))
        yield lignes


def tableau(lignes):
    """-> liste de 4 dictionnaires {champ: [lignes de texte]} (une par colonne)."""
    rangs = {}
    for x0, y, x1, txt in lignes:
        if x0 < 80:
            for lib, champ in LIBELLES.items():
                if txt.startswith(lib):
                    rangs[champ] = y
    if "commune" not in rangs or "structure" not in rangs:
        return []
    cols = [{} for _ in COLONNES]
    for x0, y, x1, txt in sorted(lignes, key=lambda l: (l[1], l[0])):
        if x0 < 160 or y > 540:
            continue
        champ = min(rangs, key=lambda c: abs(rangs[c] - y))
        if MOTS_DEFICIENCE.match(txt.strip()) and champ in ("age", "structure"):
            champ = "deficience"
        elif MOTS_AGE.match(txt.strip()) and champ in ("deficience", "discipline"):
            champ = "age"
        largeur = max(x1 - x0, 1)
        for i, (a, b) in enumerate(COLONNES):
            if (min(x1, b) - max(x0, a)) / largeur >= 0.25:     # case fusionnée : la ligne couvre plusieurs colonnes
                cols[i].setdefault(champ, []).append(txt)
    return [c for c in cols if c.get("commune") and c.get("structure")]


def recoller(lignes):
    """Lignes d'une case -> texte, en recollant les mots coupés en fin de ligne par un tiret."""
    return re.sub(r"-\s+", "-", re.sub(r"\s+", " ", " ".join(lignes))).strip()


def titre(commune):
    commune = re.sub(r"\s*\(\d{2,3}\)\s*|commune nouvelle", " ", commune, flags=re.I)
    commune = re.sub(r"\s*-\s*", "-", re.sub(r"\s+", " ", commune)).strip()
    petits = ("sur", "de", "du", "des", "la", "le", "les", "en", "lès")
    def mot(w, premier):
        return w.lower() if (w.lower() in petits and not premier) else w[:1].upper() + w[1:].lower()
    out, premier = [], True
    for part in re.split(r"([- ()])", commune):
        if part and part not in "- ()":
            out.append(mot(part, premier)); premier = False
        else:
            out.append(part)
    return "".join(out)


def activite(col):
    commune_brute = recoller(col["commune"])
    dep = re.search(r"\((\d{2,3})\)", commune_brute)
    contact = " ".join(col.get("contact", []))
    emails = EMAIL.findall(re.sub(r"\s*@\s*", "@", re.sub(r"-\s+", "-", contact)))
    deficiences = " ".join(col.get("deficience", [])).lower()
    return {
        "commune": titre(commune_brute), "dep": dep.group(1) if dep else "22",
        "sports": normaliser_sports(", ".join(x.strip() for x in re.sub(r"\([^)]*\)", "", recoller(col.get("discipline", [])))
                                              .replace("Randonnée Course d’orientation Pêche", "Randonnée / Course d’orientation / Pêche").split("/"))),
        "handicaps": [v for k, v in DEFICIENCES.items() if k in deficiences],
        "age": ", ".join(col.get("age", [])),
        "structure": recoller(col["structure"]),
        "telephone": " / ".join(dict.fromkeys(p.replace(" ", "") for p in PHONE.findall(contact)))[:60],
        "email": emails[0] if emails else "",
        "infos": " ".join(col.get("infos", [])).strip(),
    }


def fiches(pdf):
    par_structure = {}
    for lignes in lignes_par_page(pdf):
        for col in tableau(lignes):
            a = activite(col)
            k = cle(a["structure"], "")
            f = par_structure.setdefault(k, {"a": a, "sports": [], "handicaps": [], "communes": [], "ages": [], "infos": []})
            for champ, val in (("sports", a["sports"]), ("handicaps", a["handicaps"]), ("communes", [a["commune"]]),
                               ("ages", a["age"].split(", ")), ("infos", [a["infos"]])):
                f[champ] += [v for v in val if v and v not in f[champ]]
            for champ in ("telephone", "email"):
                if not f["a"][champ]:
                    f["a"][champ] = a[champ]
    for f in par_structure.values():
        a, handicaps = f["a"], f["handicaps"]
        physique = any(h in handicaps for h in ("moteur", "visuel", "auditif"))
        adapte = any(h in handicaps for h in ("mental", "psychique"))
        acces = []
        if len(f["communes"]) > 1:
            acces.append("Lieux de pratique : " + ", ".join(f["communes"]))
        if f["ages"]:
            acces.append("Public : " + ", ".join(x.lower() for x in f["ages"]))
        acces += f["infos"]
        yield {
            "sport": ", ".join(f["sports"]) or "multisport", "nom": a["structure"],
            "code_postal": a["dep"], "ville": f["communes"][0],
            "handicaps": ", ".join(handicaps),
            "pratique": "les deux" if physique and adapte else "sport adapte" if adapte else "handisport" if physique else "",
            "accessibilite": ". ".join(acces), "telephone": a["telephone"], "email": a["email"], "source": SOURCE,
        }


if __name__ == "__main__":
    print(requete(list(fiches(sys.argv[1])), SOURCE), end="")
