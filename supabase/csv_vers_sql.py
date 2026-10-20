"""Convertit un export CSV (Google Sheets, scraper…) en requête SQL à coller dans Supabase (SQL Editor).

Un club = une fiche : les lignes d'un même club (même nom et même code postal) sont regroupées,
avec tous ses sports dans la colonne sport. Les clubs déjà présents dans la base sont ignorés
(la base refuse les doublons, voir 03_un_club_une_fiche.sql).

Utilisation : python csv_vers_sql.py clubs.csv > import.sql
"""
import csv
import re
import sys
import unicodedata


def norm(s):
    s = unicodedata.normalize("NFD", s or "")
    return "".join(c for c in s if unicodedata.category(c) != "Mn").lower().strip()


def cle(nom, cp):
    """Même règle que l'index anti-doublon de la base."""
    return re.sub(r"[^a-z0-9]", "", (nom or "").lower()), (cp or "").strip()


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

# Une seule orthographe par sport (clé : écriture sans accents ni majuscules)
SPORTS = {
    "athletisme": "athlétisme", "equitation": "équitation", "cecifoot": "cécifoot", "ceci foot": "cécifoot",
    "randonnee": "randonnée", "randonnee pedestre": "randonnée", "randonnees pedestres": "randonnée", "randnnee": "randonnée",
    "randonnee avec anes": "randonnée", "ping-pong": "tennis de table", "ping pong": "tennis de table",
    "sarbacanne": "sarbacane", "handi basketball": "basket fauteuil", "basketball fauteuil": "basket fauteuil",
    "basket-fauteuil": "basket fauteuil", "basketball": "basket", "goal-ball": "goalball",
    "blind tennis (deficient visuel)": "tennis", "tennis sante": "tennis", "tennis sourd": "tennis",
    "course a pieds": "course à pied", "joelette": "joëlette", "joellette": "joëlette",
    "velo": "cyclisme", "velo rpl": "cyclisme", "velo tandem": "cyclisme", "cyclisme tandem": "cyclisme", "vtt handbike": "vtt",
    "foot": "football", "football en salle": "football", "futsal": "football", "foot adapte": "football",
    "footfauteuil": "foot fauteuil", "hand'fauteuil": "hand fauteuil", "hand’fauteuil": "hand fauteuil",
    "handball fauteuil": "hand fauteuil", "hand'adapte": "handball", "hand’adapte": "handball", "parahandball adapte": "handball",
    "tir carabine": "tir sportif", "tir pistolet": "tir sportif", "tir": "tir sportif",
    "judo 6-13 ans": "judo", "rugby 15 ans": "rugby", "muay-thai": "muay-thaï",
    "hip-hop": "danse", "breack dance": "danse", "dancehall": "danse", "afro": "danse", "danse contemporaine": "danse",
    "danse urbaine": "danse", "street danse": "danse", "danse rythmique": "danse", "danse adapte": "danse", "danse therapie": "danse",
    "gym douce": "remise en forme", "gymnastique douce": "remise en forme", "gymnastique abdominal": "remise en forme",
    "gym obesite": "remise en forme", "swissball": "remise en forme", "step": "remise en forme", "stretching": "remise en forme",
    "etirements": "remise en forme", "equilibre": "remise en forme", "recuperation": "remise en forme", "cardio": "remise en forme",
    "circuit training": "remise en forme", "cross training": "remise en forme", "fitness": "remise en forme",
    "renforcement musculaire": "remise en forme", "endurance": "remise en forme", "salle de sport": "remise en forme",
    "cours collectifs": "remise en forme", "boxe sante": "boxe", "sport pour tous": "multisport",
    "multiactivite apa": "multisport", "ecole des sports": "multisport", "ecole d'activites parasportives": "multisport",
    "travail individuel": "remise en forme", "bien-etre": "remise en forme", "gymnastique au sol": "gymnastique",
    "gymnastique corporelle": "gymnastique", "gymnastique artistique": "gymnastique", "grs": "gymnastique",
    "yoga aerien": "yoga", "sophrologie": "yoga", "catamaran": "voile", "planche a voile": "voile",
    "vol d'initiation planeur": "vol à voile", "aquajump": "aquagym", "boules lyonnaises": "boule lyonnaise",
    "raffa volo": "boccia", "grimpe dans les arbres": "grimpe d'arbres", "grimpe d'arbre": "grimpe d'arbres", "grappeling": "grappling", "kick boxing": "boxe",
    "boxe francaise": "boxe", "ski alpin": "ski", "marche": "marche nordique", "marche nordique douce": "marche nordique",
    "natation perfectionnement": "natation", "natation apprentissage": "natation", "perfectionnement": "natation",
    "balade equitherapie": "équitation", "equitation sur poney shetland": "équitation", "equitation adaptee": "équitation",
    "readaptation par l'equitation": "équitation", "readaptation par l’equitation": "équitation",
    "bapteme": "karting", "initiation conduite de kart": "karting", "vols": "montgolfière",
    "baptemes de montgolfiere": "montgolfière", "simulation de vol": "montgolfière",
    "stand up paddle paddle geant": "paddle", "stand up paddle": "paddle", "kayak de mer": "canoë-kayak",
    "canoe kayak": "canoë-kayak", "kayak": "canoë-kayak", "voile sur deriveur": "voile", "bateau collectif": "voile",
    "multisports": "multisport", "multisports sante": "multisport", "multisports jeunes": "multisport",
    "gymnastique douce adaptee": "gymnastique", "gymnastique adaptee": "gymnastique", "gymnastique douce": "gymnastique",
    "marche aquatique sante": "marche aquatique", "atelier equilibre": "remise en forme", "self defense": "self-défense",
    "basket adapte": "basket", "glisse sur glace": "patinage", "peche au coup": "pêche", "tir sportif a la carabine": "tir sportif",
    "volley-ball assis": "volley assis", "volley-ball": "volley-ball", "taiso": "taïso", "aquaforme": "aquagym",
    "balade": "randonnée", "balade nature": "randonnée", "randonnee pedestre/": "randonnée", "echecs": "échecs",
    "decouverte de l'environnement": "découverte de la nature", "decouverte de l’environnement": "découverte de la nature",
    "natation apprentissage, perfectionnement": "natation",
}
# Ce qui n'est pas un sport
PAS_DES_SPORTS = {"intervention a domicile", "jeux de societe", "conference", "visite culturelle", "ateliers cuisine",
                  "chant", "plus", "fft", "12 km par sortie"}


def normaliser_sports(texte):
    """'Hand’Fauteuil, Ping-pong et Foot.' -> ['hand fauteuil', 'tennis de table', 'football'] (sans doublon)."""
    sports = []
    texte = texte.replace("Sarbacane Boccia", "sarbacane, boccia").replace("sarbacane boccia", "sarbacane, boccia")
    for morceau in re.split(r"[,;/\n]|\s+et\s+|\s+ou\s+", texte or ""):
        m = re.sub(r"\s+et$", "", morceau.replace("’", "'").strip().strip(".").strip())
        n = norm(m)
        if not n or n in PAS_DES_SPORTS or len(n) > 40 or n.startswith(("ou ", "le comite", "inclusive")):
            continue
        if n.startswith("randonnee pedestre inclusive"):
            n = "randonnee"
        s = SPORTS.get(n, m.lower())
        if s not in sports:
            sports.append(s)
    return sports


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
    if col == "site" and not re.match(r"^https?://", v, re.I):
        v = "https://" + v
    return "'" + v.replace("'", "''") + "'"


def regrouper(fiches):
    """Fusionne les fiches d'un même club (nom + code postal) : sports réunis, premier champ non vide gardé."""
    par_cle, ordre = {}, []
    for f in fiches:
        k = cle(f.get("nom"), f.get("code_postal"))
        if not k[0]:
            continue
        if k not in par_cle:
            par_cle[k] = dict(f, sport=", ".join(normaliser_sports(f.get("sport", ""))))
            ordre.append(k)
            continue
        g = par_cle[k]
        sports = normaliser_sports(g["sport"]) + [s for s in normaliser_sports(f.get("sport", "")) if s not in normaliser_sports(g["sport"])]
        g["sport"] = ", ".join(sports)
        for col, val in f.items():
            if col != "sport" and val and not g.get(col):
                g[col] = val
    return [par_cle[k] for k in ordre]


def requete(fiches, nom_source=""):
    """Fiches {colonne de la table: valeur} -> requête SQL qui ignore les clubs déjà présents."""
    fiches = [f for f in regrouper(fiches) if f.get("sport")]
    if not fiches:
        return "-- aucun club à importer\n"
    cols = [c for c in dict.fromkeys(c for f in fiches for c in f) if c in COLONNES.values()]
    valeurs = ["  (" + ", ".join(sql(c, f.get(c)) for c in cols) + ")" for f in fiches]
    return (f"-- {len(valeurs)} clubs depuis {nom_source} (les clubs déjà présents sont ignorés)\n"
            f"insert into public.clubs ({', '.join(cols)}) values\n" + ",\n".join(valeurs) + "\n"
            "on conflict ((regexp_replace(lower(nom), '[^a-z0-9]', '', 'g')), (coalesce(code_postal, ''))) do nothing;\n")


def convertir(lignes, nom_source=""):
    """Liste de dictionnaires {titre de colonne du CSV: valeur} -> requête SQL d'import."""
    fiches = []
    for l in lignes:
        f = {COLONNES[norm(t)]: v for t, v in l.items() if t and norm(t) in COLONNES}
        if (f.get("nom") or "").strip():
            fiches.append(f)
    return requete(fiches, nom_source)


def main(chemin):
    with open(chemin, encoding="utf-8-sig") as f:
        print(convertir(list(csv.DictReader(f)), chemin.replace("\\", "/").split("/")[-1]), end="")


if __name__ == "__main__":
    main(sys.argv[1])
