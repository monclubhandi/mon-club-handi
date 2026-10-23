"""Import de l'« Annuaire Sport & Handicap Calvados 2025 » (CDOS 14) dans la table clubs.

L'annuaire présente les clubs par discipline. Pour chaque club : nom, référent handicap (nom, téléphone, mail),
adresse du lieu de pratique, site et page Facebook, puis des pictogrammes : type de handicap accueilli (moteur,
mental, auditif, visuel) et label ou affiliation (Norm'Handi, Handisport, Sport adapté, Handiguide). On lit la
position des textes et des images (pdftohtml -xml) ; chaque pictogramme est reconnu par son dessin.

Le nom des personnes n'est pas repris, ni une adresse mail qui contient leur nom (adresse personnelle).

Utilisation : python import_calvados.py annuaire.pdf > 10_import_calvados.sql   (nécessite pdftohtml)
"""
import hashlib
import html
import os
import re
import subprocess
import sys
import tempfile

from PIL import Image

from csv_vers_sql import norm, requete
from import_eure import mail_du_club

SOURCE = "Annuaire Sport & Handicap Calvados 2025, CDOS 14"
# Empreinte du dessin (image réduite à 16x16) -> sens du pictogramme
PICTOS = {"7bb015a3": "mental", "159ae57b": "moteur", "9956a7d8": "auditif", "f65c09ef": "visuel",
          "a85141a8": "normhandi", "cd83af71": "ffh", "cfe937d5": "ffsa", "2f706bcd": "handiguide"}
DISCIPLINES = {
    "aeromodelisme": "aéromodélisme", "aeronautique": "aéronautique", "athletisme": "athlétisme", "aviron": "aviron",
    "badminton": "badminton", "basketball": "basket", "boccia": "boccia", "canoe-kayak": "canoë-kayak",
    "char a voile": "char à voile", "cyclisme": "cyclisme", "echecs": "échecs", "equitation": "équitation",
    "escalade": "escalade", "escrime": "escrime", "football": "football", "golf": "golf", "gymnastique": "gymnastique",
    "halterophilie musculation": "haltérophilie, musculation", "handball": "handball", "handbike": "handbike",
    "judo": "judo", "karate": "karaté", "longe-cote": "longe-côte", "multiactivites": "multisport", "natation": "natation",
    "parapente": "parapente", "petanque": "pétanque", "qi gong": "qi-gong", "rugby": "rugby",
    "savate et boxe francaise": "savate", "sarbacane": "sarbacane", "sports boules": "boules",
    "tai chi chuan": "taï chi chuan", "tennis": "tennis", "tennis de table": "tennis de table",
    "tir a l'arc": "tir à l'arc", "tir sportif": "tir sportif", "volleyball": "volley-ball", "voile": "voile",
}
PHONE = re.compile(r"^0\d(?: \d\d){4}$")
EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
POSTAL = re.compile(r"^(\d{4,5})\s+(.+)$")     # « 1400 CAEN » (code mal écrit dans l'annuaire) : on garde la commune


def pages(pdf):
    with tempfile.TemporaryDirectory() as d:
        subprocess.run(["pdftohtml", "-xml", "-q", pdf, os.path.join(d, "c")], capture_output=True)
        xml = open(os.path.join(d, "c.xml"), encoding="utf-8").read()
        for page in xml.split("<page ")[1:]:
            num = int(re.search(r'number="(\d+)"', page).group(1))
            textes = []
            for top, left, width, height, inner in re.findall(r'<text top="(\d+)" left="(\d+)" width="(\d+)" height="(\d+)"[^>]*>(.*?)</text>', page, re.S):
                lien = re.search(r'href="([^"]+)"', inner)
                txt = html.unescape(re.sub(r"<[^>]+>", "", inner)).strip()
                if txt:
                    textes.append({"y": int(top), "x": int(left), "h": int(height), "gras": "<b>" in inner,
                                   "txt": txt, "lien": html.unescape(lien.group(1)) if lien else ""})
            images = []
            for top, left, src in re.findall(r'<image top="(\d+)" left="(\d+)" width="\d+" height="\d+" src="([^"]+)"', page):
                chemin = os.path.join(d, os.path.basename(src))
                if os.path.exists(chemin):
                    im = Image.open(chemin).convert("RGB").resize((16, 16))
                    sens = PICTOS.get(hashlib.md5(im.tobytes()).hexdigest()[:8])
                    if sens:
                        images.append({"y": int(top), "sens": sens})
            yield num, textes, images


def fiches(pdf):
    clubs, discipline = [], ""
    for num, textes, images in pages(pdf):
        if num < 11 or num > 36:                       # les clubs sont pages 11 à 36
            continue
        textes = [t for t in textes if t["y"] > 50 and not re.fullmatch(r"\d+", t["txt"])]   # en-tête, n° de page
        titres = [t for t in textes if t["gras"] and t["h"] >= 30]                          # disciplines
        noms = [t for t in textes if t["gras"] and t["h"] < 30 and t["x"] < 90 and not t["txt"].startswith("→")]
        bornes = sorted([n["y"] for n in noms] + [t["y"] for t in titres] + [10 ** 6])
        for n in sorted(noms, key=lambda n: n["y"]):
            avant = [t for t in titres if t["y"] < n["y"]]
            if avant:
                discipline = re.sub(r"\s*\(suite\)", "", max(avant, key=lambda t: t["y"])["txt"], flags=re.I)
            fin = min(b for b in bornes if b > n["y"])
            bloc = sorted((t for t in textes if n["y"] < t["y"] < fin - 5 and t is not n), key=lambda t: (t["y"], t["x"]))
            gauche = [t for t in bloc if t["x"] < 450]
            droite = [t for t in bloc if t["x"] >= 450]
            # Référents : « → Prénom NOM », ou nom en gras à côté de la flèche (jamais repris, sert à écarter leur mail)
            personnes = [t["txt"].lstrip("→ ").strip() for t in gauche if t["txt"].startswith("→") or (t["gras"] and t["x"] >= 90)]
            tels = [t["txt"] for t in gauche if PHONE.match(t["txt"])]
            mails = [t["txt"] for t in gauche if EMAIL.search(t["txt"])]
            postal = next((t for t in gauche if POSTAL.match(t["txt"])), None)
            # Adresse : les lignes entre le dernier téléphone ou mail et la ligne « code postal commune »
            adresse = []
            if postal:
                derniere = max([t["y"] for t in gauche if PHONE.match(t["txt"]) or EMAIL.search(t["txt"]) or t["txt"].startswith("→")
                                or t["gras"]] or [n["y"]])
                adresse = [t["txt"] for t in gauche if derniere < t["y"] < postal["y"]]
            # Adresse affichée quand c'est une adresse web (le lien caché du PDF est parfois faux), sinon le lien
            liens = [("https://" + t["txt"] if t["txt"].startswith("www.") else t["txt"]) if re.match(r"(https?://|www\.)", t["txt"])
                     else t["lien"] for t in droite if t["lien"]]
            site = next((l for l in liens if "facebook" not in l), "") or next(iter(liens), "")
            pictos = {i["sens"] for i in images if n["y"] - 10 < i["y"] < fin - 5}
            clubs.append({"nom": n["txt"], "discipline": discipline, "tels": tels, "mails": mails, "personnes": personnes,
                          "cp": (lambda cp: cp if len(cp) == 5 else "14")(POSTAL.match(postal["txt"]).group(1)) if postal else "",
                          "ville": POSTAL.match(postal["txt"]).group(2) if postal else "",
                          "adresse": ", ".join(adresse), "site": site, "pictos": pictos})

    par_club = {}
    for c in clubs:
        k = (re.sub(r"[^a-z0-9]", "", norm(c["nom"])), c["cp"])
        f = par_club.setdefault(k, {**c, "sports": [], "pictos": set()})
        sport = DISCIPLINES.get(norm(c["discipline"]).replace("’", "'"), c["discipline"].lower())
        f["sports"] += [s for s in sport.split(", ") if s not in f["sports"]]
        f["pictos"] |= c["pictos"]
    for f in par_club.values():
        h = [x for x in ("moteur", "visuel", "auditif", "mental") if x in f["pictos"]]
        physique, adapte = any(x in h for x in ("moteur", "visuel", "auditif")), "mental" in h
        if "ffh" in f["pictos"] and "ffsa" in f["pictos"]:
            pratique = "les deux"
        elif "ffh" in f["pictos"] or "ffsa" in f["pictos"]:
            pratique = "handisport" if "ffh" in f["pictos"] else "sport adapte"
        else:
            pratique = "les deux" if physique and adapte else "sport adapte" if adapte else "handisport" if physique else ""
        yield {
            "sport": ", ".join(f["sports"]), "nom": f["nom"], "adresse": f["adresse"][:200], "code_postal": f["cp"],
            "ville": ville(f["ville"]), "handicaps": ", ".join(h), "pratique": pratique,
            "telephone": " / ".join(f["tels"][:2])[:60],
            "email": mail_du_club(" ".join(f["mails"]), f["nom"], " ".join(f["personnes"])),
            "site": f["site"], "label": "Label Norm'Handi" if "normhandi" in f["pictos"] else "", "source": SOURCE,
        }


def ville(s):
    """« HEROUVILLE-SAINT-CLAIR » -> « Herouville-Saint-Clair »."""
    petits = {"de", "du", "des", "la", "le", "les", "sur", "en", "d", "l", "et", "sous"}
    parts = re.split(r"(\s+|-|'|’)", s.lower())
    out, premier = [], True
    for m in parts:
        if not m.strip() or m in "-'’":
            out.append(m)
            continue
        out.append(m if (m in petits and not premier) else m[:1].upper() + m[1:])
        premier = False
    return "".join(out)


if __name__ == "__main__":
    print(requete(list(fiches(sys.argv[1])), SOURCE), end="")
