"""Import de la « Liste des 204 clubs labellisés Sport et Handicap » du Département des Bouches-du-Rhône
(mise à jour avril 2026) dans la table clubs.

Le PDF est un tableau : association, mail du club, lieux de pratique, 4 colonnes de croix (mentale et/ou,
visuelle, auditive, motrice), âge accueilli, activités proposées. Le tableau est lu case par case avec ses
bordures (pdfplumber).

Les activités et les lieux sont écrits en texte libre (« entraînements collectifs », « Gymnase »…). Les sports et
la commune de chaque club ont donc été relus ligne par ligne (table LECTURE ci-dessous), uniquement à partir de
ce qui est écrit dans la ligne : activités, lieux de pratique ou nom du club (« JUDO CLUB VENELLOIS » -> judo,
Venelles). Une ligne qui n'indique aucun sport n'est pas importée (EXCLUES), ni une ligne sans nom de club. Le
texte d'origine des lieux, de l'âge et des activités est repris tel quel dans l'accès.

Utilisation : python import_bouches_du_rhone.py liste.pdf > 09_import_bouches_du_rhone.sql   (nécessite pdfplumber)
"""
import re
import sys

import pdfplumber

from csv_vers_sql import norm, requete
from import_eure import mail_du_club

SOURCE = "Clubs labellisés Sport et Handicap, Département des Bouches-du-Rhône (avril 2026)"
LABEL = "Label Sport et Handicap (Bouches-du-Rhône)"

# Numéro de ligne (ordre du PDF, de 1 à 204) -> (sports, commune, code postal si écrit dans la ligne)
LECTURE = {
    1: ("escalade", "Simiane-Collongue", ""), 2: ("tir à l'arc", "", ""), 3: ("gymnastique", "Grans", ""),
    4: ("aïkido", "Miramas", ""), 5: ("plongée", "Aix-en-Provence", ""), 6: ("tennis de table", "Aix-en-Provence", ""),
    7: ("natation, multisport", "Aix-en-Provence", ""), 8: ("escalade, marche nordique, ultimate", "Aix-en-Provence", ""),
    9: ("judo, remise en forme, boxe, marche nordique, pétanque, self-défense, football, rugby, bowling", "", ""),
    10: ("football, natation, pétanque, judo, vtt, ski, athlétisme, randonnée, danse", "", ""),
    11: ("yoga, gymnastique", "La Ciotat", ""), 12: ("judo", "Marseille", "13008"),
    13: ("cyclisme, athlétisme, roller, natation, escalade, badminton, randonnée, basket, marche nordique, golf, musculation", "", ""),
    14: ("tir à l'arc", "Marseille", "13012"), 15: ("tir à l'arc, sarbacane", "Les Pennes-Mirabeau", ""),
    16: ("danse, tennis de table, remise en forme, badminton", "Martigues", "13500"),
    17: ("athlétisme, natation, judo, torball, goalball, tir à l'arc, remise en forme", "Marseille", "13007"),
    18: ("tennis de table", "Marseille", "13013"), 19: ("ski de fond, biathlon, marche à pied, aquagym, cyclisme, natation", "", ""),
    20: ("longe-côte", "Marseille", "13008"), 21: ("natation, duathlon, longe-côte, multisport", "Marseille", "13008"),
    22: ("natation, marche à pied, boxe, basket fauteuil, rugby fauteuil, volley assis, musculation", "Salon-de-Provence", ""),
    23: ("échecs", "Plan-de-Cuques", ""), 24: ("aviron, voile", "", ""), 25: ("randonnée", "La Penne-sur-Huveaune", ""),
    26: ("multisport", "", ""), 27: ("équitation", "", ""),
    28: ("handball, boxe, capoeira, rugby, équitation, volley-ball, basket, pétanque, danse, escalade", "Arles", ""),
    29: ("tennis de table", "Miramas", ""), 30: ("athlétisme", "Miramas", ""), 31: ("athlétisme", "Miramas", "13140"),
    32: ("athlétisme", "Marseille", "13015"), 33: ("sambo", "Marseille", "13010"), 34: ("taekwondo", "Marseille", ""),
    35: ("tennis de table", "Aubagne", "13400"), 36: ("volley assis", "Aix-en-Provence", ""),
    37: ("badminton", "Aix-en-Provence", "13090"), 38: ("gymnastique, marche nordique, pilates, multisport", "Aix-en-Provence", ""),
    39: ("football", "Les Pennes-Mirabeau", "13170"), 40: ("badminton", "Fos-sur-Mer", "13270"),
    41: ("badminton", "Salon-de-Provence", ""), 42: ("tennis", "Berre-l'Étang", ""), 43: ("badminton", "Marseille", "13013"),
    44: ("escalade", "Marseille", "13008"), 45: ("boxe", "La Fare-les-Oliviers", "13580"), 46: ("football", "Marseille", "13013"),
    47: ("plongée, apnée", "Aix-en-Provence", ""), 48: ("échecs", "Cassis", "13260"), 49: ("rugby", "Cassis", "13260"),
    50: ("remise en forme, danse", "", ""), 51: ("basket", "Marseille", "13005"), 52: ("pétanque", "", ""),
    53: ("tennis de table", "", ""), 54: ("cécifoot, boccia, multisport", "", ""), 55: ("spéléologie", "", ""),
    56: ("escrime", "Arles", "13200"), 57: ("voile", "Rognac", ""), 58: ("tennis", "Marseille", "13008"),
    59: ("aéromodélisme", "Berre-l'Étang", ""), 60: ("danse", "Miramas", ""), 61: ("tir sportif", "Salon-de-Provence", ""),
    62: ("natation, tennis de table, handbike", "Aix-en-Provence", ""), 63: ("aviron", "Marignane", "13700"),
    64: ("voile, wingfoil", "Berre-l'Étang", "13130"), 65: ("handball", "Châteaurenard", ""), 66: ("karaté", "Marseille", "13012"),
    67: ("rugby, ultimate, multisport", "Berre-l'Étang", ""), 68: ("badminton", "", ""), 69: ("multisport", "", ""),
    72: ("multisport", "Marseille", "13012"), 73: ("voile, canoë-kayak, paddle", "Martigues", ""), 74: ("karaté", "Marseille", ""),
    75: ("tennis, judo, randonnée, vtt, escalade, bowling, cirque, natation, athlétisme, musculation", "", ""),
    76: ("natation, sauvetage sportif", "Marseille", ""), 78: ("multisport", "", ""), 79: ("équitation", "Marseille", ""),
    80: ("équitation", "Puyricard", ""), 81: ("football", "Fos-sur-Mer", ""), 82: ("danse", "Aubagne", ""),
    83: ("football", "Rousset", ""), 84: ("football", "Saint-Mitre-les-Remparts", "13920"),
    85: ("football", "Septèmes-les-Vallons", ""),
    86: ("badminton, danse, marche à pied", "", ""),
    87: ("football, badminton, gymnastique, remise en forme, zumba", "Marseille", "13012"),
    88: ("gymnastique", "Salon-de-Provence", ""), 89: ("gymnastique", "Lambesc", ""), 90: ("haltérophilie", "Marseille", "13011"),
    91: ("handball", "Ensuès-la-Redonne", ""), 92: ("handball, boccia", "Plan-de-Cuques", ""),
    93: ("ski", "La Salle-les-Alpes", "05240"), 94: ("natation, tennis de table, boccia", "Marseille", ""),
    95: ("basket fauteuil", "Marseille", "13015"), 96: ("échecs", "Allauch", ""), 97: ("tennis", "Istres", ""),
    98: ("vtt, cyclisme", "Istres", ""), 99: ("athlétisme", "Istres", ""), 100: ("tennis de table", "Istres", ""),
    101: ("danse", "Miramas", ""), 103: ("judo", "", ""), 104: ("judo", "Venelles", ""), 105: ("judo", "Marseille", ""),
    106: ("karaté", "Vitrolles", ""), 107: ("aviron", "", ""), 108: ("pétanque", "Salon-de-Provence", ""),
    109: ("longe-côte", "La Ciotat", ""), 110: ("natation, aquagym, musculation, randonnée, judo", "Salon-de-Provence", ""),
    112: ("remise en forme, boxe", "Le Tholonet", ""), 113: ("plongée", "Vitrolles", ""), 114: ("tir à l'arc", "Miramas", ""),
    115: ("tir à l'arc", "Fos-sur-Mer", ""), 116: ("tir à l'arc", "Saint-Martin-de-Crau", ""), 117: ("pétanque", "Miramas", ""),
    118: ("aviron", "Istres", ""), 119: ("rugby fauteuil", "", ""), 120: ("rugby", "", ""), 121: ("randonnée, multisport", "", ""),
    122: ("football", "Luynes", ""), 125: ("football", "Gignac-la-Nerthe", ""), 126: ("cécifoot, boccia, multisport", "", ""),
    127: ("escrime", "Marseille", "13005"), 128: ("canoë-kayak", "Marseille", "13008"), 129: ("natation", "Marseille", "13003"),
    130: ("apnée", "Marseille", "13008"), 131: ("tennis de table", "Marseille", ""), 132: ("boules", "Martigues", ""),
    133: ("tir à l'arc", "Marseille", ""), 134: ("hockey", "Marseille", "13010"),
    135: ("natation, aquagym, sauvetage sportif, water-polo", "", ""), 136: ("badminton", "Miramas", ""),
    137: ("escalade", "Miramas", ""), 138: ("voile", "Marseille", "13007"),
    139: ("gymnastique, remise en forme, musculation, danse", "Salon-de-Provence", ""),
    140: ("aéromodélisme", "Aix-en-Provence", "13090"), 141: ("plongée", "", ""), 142: ("aquagym", "Arles", "13200"),
    143: ("parkour", "Marseille", "13009"), 144: ("pilates, aquagym, randonnée, escrime, tennis de table", "Arles", ""),
    145: ("gymnastique", "Gardanne", ""), 146: ("taekwondo", "Marseille", ""), 147: ("athlétisme", "Marseille", ""),
    148: ("tennis de table, roller, escalade, danse, multisport", "Aubagne", ""), 149: ("cécifoot, boccia, multisport", "Istres", ""),
    152: ("tennis, padel, ski, snowboard, vtt", "Fuveau", "13710"), 154: ("basket, football, pétanque, randonnée", "Aubagne", ""),
    155: ("hand fauteuil", "Aubagne", ""), 156: ("pentathlon, tir sportif, course à pied, natation, escrime", "Les Pennes-Mirabeau", "13170"),
    157: ("muay-thaï", "Trets", "13530"), 158: ("tennis de table", "Venelles", "13770"), 160: ("taekwondo", "Salon-de-Provence", ""),
    161: ("cyclisme", "Sausset-les-Pins", ""), 162: ("karting", "Martigues", ""), 163: ("aviron", "Marseille", ""),
    164: ("rugby", "Châteaurenard", ""), 165: ("rugby", "Marseille", "13015"), 166: ("rugby", "Port-de-Bouc", ""),
    167: ("rugby", "Miramas", ""), 168: ("football", "Marseille", ""), 169: ("rugby fauteuil", "Saint-Martin-de-Crau", ""),
    170: ("voile", "Marseille", "13016"), 171: ("remise en forme, savate", "Marseille", "13011"), 173: ("ski", "Vars", "05"),
    174: ("tennis, badminton, basket, escalade, volley-ball, handball, gymnastique, golf, judo, rugby, pétanque, athlétisme", "Marseille", "13008"),
    175: ("voile", "Marseille", ""), 176: ("voile, aviron", "La Ciotat", ""), 177: ("bowling", "Salon-de-Provence", ""),
    178: ("multisport, athlétisme, padel, natation, plongée, voile, randonnée, danse, ski, boxe, football, basket, aviron", "", ""),
    179: ("athlétisme", "Marseille", ""), 180: ("natation", "Miramas", ""), 181: ("plongée", "Miramas", "13140"),
    182: ("tennis", "Les Pennes-Mirabeau", ""), 183: ("boxe", "Istres", ""), 184: ("tennis fauteuil, tennis", "Marseille", "13013"),
    185: ("tennis", "Carry-le-Rouet", "13620"), 186: ("tennis", "Marseille", "13015"), 187: ("tennis, padel", "Fuveau", "13710"),
    188: ("tennis fauteuil", "Marseille", "13012"), 189: ("tennis", "Miramas", "13140"),
    190: ("tennis", "Roquefort-la-Bédoule", ""), 191: ("tennis", "Velaux", "13880"), 192: ("tennis", "Vitrolles", "13127"),
    193: ("tennis, padel", "Marseille", "13014"), 194: ("hand fauteuil, handball", "Coudoux", ""),
    195: ("cyclisme", "Aix-en-Provence", ""), 196: ("multisport", "Gardanne", "13120"),
    197: ("football, marche à pied, tchoukball, athlétisme", "Eguilles", ""), 199: ("cyclisme", "Fos-sur-Mer", ""),
    200: ("cyclisme", "", ""), 201: ("basket, baskin", "Venelles", "13770"), 202: ("badminton", "Vitrolles", ""),
    203: ("voile", "La Ciotat", ""), 204: ("volley-ball", "Arles", ""),
}
# Lignes non importées, avec la raison
EXCLUES = {
    70: "Comité Handisport : ni activité ni handicap indiqués", 71: "Comité Sport Adapté : ni activité ni handicap indiqués",
    77: "nom du club absent", 102: "aucun sport indiqué (« Entrainement collectifs »)",
    111: "aucun sport indiqué (activité physique adaptée)", 123: "projet en cours de faisabilité",
    124: "aucun sport indiqué (visites médicales, bilan, APA)", 150: "office des sports : orientation, aucun sport",
    151: "office des sports : orientation, aucun sport", 153: "aucun sport indiqué", 159: "aucun sport indiqué",
    172: "aucun sport indiqué (« loisir encadré »)", 198: "aucun sport indiqué (interventions ULIS)",
}
# Même association écrite deux fois, avec une faute de frappe : une seule fiche
MEME_CLUB = {181: 180}            # « SPRTS LOISIRS ET CULTURE DE MIRAMAS » = « SPORTS LOISIRS CULTURE » (Miramas)
CROIX = ["mental", "visuel", "auditif", "moteur"]           # ordre des 4 colonnes du PDF


def lignes(pdf):
    with pdfplumber.open(pdf) as doc:
        for page in doc.pages:
            for table in page.extract_tables():
                for r in table:
                    if r[0] != "Association":
                        yield [re.sub(r"\s+", " ", c or "").strip() for c in r]


def fiches(pdf):
    par_nom, cles = {}, {}
    for n, r in enumerate(lignes(pdf), 1):
        if n in EXCLUES:
            continue
        sports, ville, cp = LECTURE[n]
        nom = re.sub(r"\s+con$", "", r[0]).rstrip(".").strip()
        handicaps = [h for h, case in zip(CROIX, r[3:7]) if case]
        acces = [x for x in (("Lieu de pratique : " + r[2]) if r[2] else "", ("Public : " + r[7]) if r[7] else "",
                             ("Activités : " + r[8]) if r[8] else "") if x]
        k = cles.get(MEME_CLUB.get(n)) or re.sub(r"[^a-z0-9]", "", norm(nom))   # « FIT Z FORM » et « Fit’Z Form » : un seul club
        cles[n] = k
        f = par_nom.get(k)
        if f:                                                  # même club sur deux lignes : on réunit
            f["handicaps"] |= set(handicaps)
            f["sports"] += [s for s in sports.split(", ") if s not in f["sports"]]
            f["acces"] += [a for a in acces if a not in f["acces"]]
            f["ville"], f["cp"] = f["ville"] or ville, f["cp"] or cp
            f["email"] = f["email"] or mail_du_club(r[1], nom, "")
            continue
        par_nom[k] = {"nom": nom, "sports": sports.split(", "), "ville": ville, "cp": cp, "handicaps": set(handicaps),
                      "acces": acces, "email": mail_du_club(r[1], nom, "")}
    for f in par_nom.values():
        h = [x for x in ["moteur", "visuel", "auditif", "mental"] if x in f["handicaps"]]
        physique, adapte = any(x in h for x in ("moteur", "visuel", "auditif")), "mental" in h
        yield {
            "sport": ", ".join(f["sports"]), "nom": f["nom"], "code_postal": f["cp"] or "13", "ville": f["ville"],
            "handicaps": ", ".join(h),
            "pratique": "les deux" if physique and adapte else "sport adapte" if adapte else "handisport" if physique else "",
            "accessibilite": ". ".join(f["acces"])[:1000], "email": f["email"], "label": LABEL, "source": SOURCE,
        }


if __name__ == "__main__":
    print(requete(list(fiches(sys.argv[1])), SOURCE), end="")
