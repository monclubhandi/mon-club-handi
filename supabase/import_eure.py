"""Import de la « Liste des clubs labellisés Sport et Handicap » du CDOS de l'Eure (6 février 2025) dans la table clubs.

Le PDF est un tableau : date du label, discipline, nom du club, commune de pratique, EPCI, référent handicap,
téléphone, mail, étoiles, puis 4 colonnes de pictogrammes (1 moteur, 2 visuel, 3 auditif, 4 mental) qui disent
quels handicaps le club accueille. On lit la position des textes et des pictogrammes (pdftohtml -xml) et on
rattache chaque élément à la ligne du tableau la plus proche.

Le nom du référent n'est pas repris, ni une adresse mail qui contient son nom (adresse personnelle) : seuls le
téléphone et une adresse mail du club le sont. Un club noté « en sommeil » n'est pas importé. Le guide ne donne
que la commune : le code postal est remplacé par le numéro du département (27).

Utilisation : python import_eure.py liste.pdf > 08_import_eure.sql   (nécessite pdftohtml)
"""
import html
import os
import re
import subprocess
import sys
import tempfile

from csv_vers_sql import norm, normaliser_sports, requete

SOURCE = "Clubs labellisés Sport et Handicap de l'Eure, CDOS 27 (février 2025)"
COLONNES = {"date": 50, "discipline": 157, "nom": 307, "commune": 457, "epci": 608, "referent": 738,
            "telephone": 833, "mail": 953, "etoiles": 1053}
PICTOS = [(1077, 1090, "moteur"), (1110, 1122, "visuel"), (1142, 1156, "auditif"), (1179, 1192, "mental")]
DISCIPLINES = {"cyclotourisme": "cyclisme", "cyclotourisme (tandem)": "cyclisme", "cyclotourisme - vtt": "cyclisme, vtt",
               "voile aviron": "voile, aviron", "boxe educative": "boxe", "basket-fauteuil": "basket fauteuil",
               "tir sportif": "tir sportif", "tir a l'arc": "tir à l'arc", "canoe-kayak": "canoë-kayak",
               "foot-fauteuil": "foot fauteuil", "handball - hand'fauteuil": "handball, hand fauteuil",
               "handensemble": "handball", "tennis - padel": "tennis, padel", "judo ju-jitsu": "judo, jujitsu",
               "judo, jiu-jitsu": "judo, jujitsu", "judo, jujitsu-self defense, taiso": "judo, jujitsu, self-défense, taïso",
               "karate": "karaté", "muay thai, boxe, disciplines associees": "muay-thaï, boxe",
               "plongee sous marine": "plongée", "parapente vol libre": "parapente",
               "comite departemental de petanque et jeux provencaux": "pétanque",
               "karate & disciplines associees": "karaté",
               "muay thai, kick boxing et disciplines associees": "muay-thaï, boxe",
               "kayak, escalade, speleologie, vtt, randonnee- orientation": "canoë-kayak, escalade, spéléologie, vtt, randonnée-orientation"}


def elements(pdf):
    with tempfile.TemporaryDirectory() as d:
        subprocess.run(["pdftohtml", "-xml", "-q", pdf, os.path.join(d, "t")], capture_output=True)
        xml = open(os.path.join(d, "t.xml"), encoding="utf-8").read()
    for num, page in enumerate(xml.split("<page ")[1:]):
        for top, left, width, height, txt in re.findall(r'<text top="(\d+)" left="(\d+)" width="(\d+)" height="(\d+)"[^>]*>(.*?)</text>', page, re.S):
            txt = html.unescape(re.sub(r"<[^>]+>", "", txt)).strip()
            if txt:
                yield num, "texte", int(top) + int(height) / 2, int(left) + int(width) / 2, int(left), txt
        for top, left, height in re.findall(r'<image top="(\d+)" left="(\d+)" width="\d+" height="(\d+)"', page):
            yield num, "picto", int(top) + int(height) / 2, int(left), int(left), ""


def lignes(pdf):
    # Le PDF contient certains textes en double, superposés au même endroit : on n'en garde qu'un
    vus, elems = set(), []
    for e in elements(pdf):
        cle = (e[0], e[1], round(e[2]), round(e[4]), e[5])
        entete = e[0] == 0 and e[2] < 32                                    # en-tête du tableau (page 1)
        if not entete and cle not in vus:
            vus.add(cle)
            elems.append(e)
    fin = {}                                                              # la légende commence après le tableau
    for e in elems:
        if e[5].startswith("Légende"):
            fin[e[0]] = e[2]
    elems = [e for e in elems if e[2] < fin.get(e[0], 1e9) - 5]
    ancres = []
    for e in sorted(elems, key=lambda e: (e[0], e[2])):
        if e[1] == "texte" and e[3] < 100:                                  # une ligne = une date de label
            if not ancres or ancres[-1][0] != e[0] or e[2] - ancres[-1][1] > 4:
                ancres.append((e[0], e[2]))
    rangs = {a: {"pictos": set()} for a in ancres}
    for page, genre, y, x, left, txt in elems:
        candidats = [a for a in ancres if a[0] == page]
        if not candidats:
            continue
        a = min(candidats, key=lambda a: abs(a[1] - y))
        if genre == "picto":
            rangs[a]["pictos"].update(h for x0, x1, h in PICTOS if x0 <= x <= x1)
            continue
        col = min(COLONNES, key=lambda c: abs(COLONNES[c] - x))
        rangs[a].setdefault(col, []).append((y, left, txt))
    for a in ancres:
        r = rangs[a]
        yield {c: " ".join(dict.fromkeys(t for _, _, t in sorted(v))) if c != "pictos" else v for c, v in r.items()}


FAI = ("gmail.", "orange.", "wanadoo.", "free.", "sfr.", "hotmail.", "yahoo.", "laposte.", "outlook.", "neuf.",
       "club-internet.", "bbox.", "netcourrier.", "cegetel.", "live.", "aol.", "icloud.")
GENERIQUES = ("contact", "club", "asso", "secretariat", "president", "info", "sport", "administration", "bienvenue",
              "stade", "codep", "comite")


def mail_du_club(texte, nom, referent):
    """Garde une adresse du club, jamais une adresse personnelle : on écarte celle qui contient le nom du référent,
    et chez un fournisseur grand public (gmail, orange…) on ne garde que celle qui rappelle le nom du club."""
    personne = {norm(w) for w in re.findall(r"[A-Za-zÀ-ÿ]{3,}", referent)}
    mots_club = {norm(w)[:5] for w in re.findall(r"[A-Za-zÀ-ÿ]{4,}", nom)} | set(GENERIQUES)
    for m in re.findall(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", texte):
        local, domaine = norm(m).split("@")
        if any(w in local for w in personne):
            continue
        if not domaine.startswith(FAI) or any(w in local for w in mots_club):
            return m
    return ""


def titre(s):
    if s != s.upper():
        return s
    petits = {"de", "du", "des", "la", "le", "les", "et", "sur", "en", "d", "l", "sous"}
    parts = re.split(r"(\s+|-|'|’)", s.lower())
    out, premier = [], True
    for m in parts:
        if not m.strip() or m in "-'’":
            out.append(m)
            continue
        out.append(m if (m in petits and not premier) else m[:1].upper() + m[1:])
        premier = False
    return "".join(out)


def fiches(pdf):
    par_nom = {}
    for r in lignes(pdf):
        nom = r.get("nom", "")
        if re.search(r"sommeil", nom, re.I):                                # club en sommeil : pas importé
            continue
        nom = re.sub(r"\s*\((?:ex|Ex)\b[^)]*\)", "", nom).strip()            # « (ex Centre équestre…) » : ancien nom
        if not nom:
            continue
        discipline = r.get("discipline", "")
        sports = DISCIPLINES.get(re.sub(r"\s+", " ", norm(discipline)), discipline)
        communes = [titre(c.strip().upper()) if re.search(r"\b[A-Z]{3,}\b", c) else c.strip() for c in re.split(r"\s*\(?&\s*|\)", r.get("commune", "")) if c.strip()]
        mail = mail_du_club(r.get("mail", ""), nom, r.get("referent", ""))
        tel = re.findall(r"0\d(?: ?\d\d){4}", r.get("telephone", ""))
        k = norm(nom)
        f = par_nom.setdefault(k, {"nom": nom, "sports": [], "communes": [], "handicaps": set(), "tel": "", "mail": ""})
        f["sports"] += [s for s in normaliser_sports(sports) if s not in f["sports"]]
        f["communes"] += [c for c in communes if c not in f["communes"]]
        f["handicaps"] |= r["pictos"]
        f["tel"] = f["tel"] or (tel[0] if tel else "")
        f["mail"] = f["mail"] or mail
    ordre = ["moteur", "visuel", "auditif", "mental"]
    for f in par_nom.values():
        h = [x for x in ordre if x in f["handicaps"]]
        physique, adapte = any(x in h for x in ("moteur", "visuel", "auditif")), "mental" in h
        yield {
            "sport": ", ".join(f["sports"]), "nom": f["nom"], "code_postal": "27",
            "ville": f["communes"][0] if f["communes"] else "",
            "handicaps": ", ".join(h),
            "pratique": "les deux" if physique and adapte else "sport adapte" if adapte else "handisport" if physique else "",
            "accessibilite": ("Lieux de pratique : " + ", ".join(f["communes"])) if len(f["communes"]) > 1 else "",
            "telephone": f["tel"], "email": f["mail"], "label": "Label Sport et Handicap (Eure)", "source": SOURCE,
        }


if __name__ == "__main__":
    print(requete(list(fiches(sys.argv[1])), SOURCE), end="")
