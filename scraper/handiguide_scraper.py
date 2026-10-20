"""
Collecte des fiches du Handiguide des sports pour "Paralliance".

Utilisation :
    python handiguide_scraper.py "URL_DE_RECHERCHE_HANDIGUIDE" --test      (5 fiches pour vérifier)
    python handiguide_scraper.py "URL_DE_RECHERCHE_HANDIGUIDE"             (toutes les fiches)
    python handiguide_scraper.py --aide                                    (toutes les options)

Résultats :
    nouveaux_clubs.sql  à coller dans Supabase (SQL Editor → New query → Run) pour ajouter les clubs
    nouveaux_clubs.csv  même contenu, à ouvrir dans un tableur pour vérifier avant l'import

Si la collecte est interrompue (Ctrl+C, coupure), relance la même commande :
elle reprend là où elle s'était arrêtée grâce au fichier .progression.json.
"""

import argparse
import csv
import json
import os
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request
import urllib.robotparser

# ===== Réglages =====
# Base Supabase de l'appli (clé publique : lecture seule), pour ne pas reprendre les clubs déjà présents
SUPABASE_URL = "https://aogcjrfrfdasxesntlpk.supabase.co"
SUPABASE_KEY = "sb_publishable_ZNohzowK1cNBG_-qukzemQ_KAG9EX-Z"
BASE = "https://www.handiguide.sports.gouv.fr"
# Base Adresse Nationale : géocodeur de l'IGN, et l'ancienne adresse en secours
GEOCODEURS = ["https://data.geopf.fr/geocodage/search?limit=1&q=", "https://api-adresse.data.gouv.fr/search/?limit=1&q="]
USER_AGENT = "MonClubHandi/2.0 (annuaire parasport benevole ; https://monclubhandi.github.io/mon-club-handi/)"
PAUSE = 3  # secondes entre deux fiches (ne pas descendre en dessous)
PROGRESSION = ".progression.json"

# Colonnes produites (titres du fichier CSV) et colonne correspondante dans la table clubs de Supabase
COLONNES = [
    "Sport", "Nom", "Adresse", "Code postal", "Ville", "Handicaps", "Pratique", "Creneaux",
    "Accessibilite", "Telephone", "Email", "Site", "Label", "Para sportifs au club",
    "Encadrant forme", "Verifie le", "Essai", "Latitude", "Longitude", "Source",
]

# Libellés des rubriques d'une fiche, dans l'ordre où ils apparaissent
RUBRIQUES = [
    "Activité sportive", "Description", "Caractéristiques de la structure", "Handicap(s)",
    "Public(s)", "Types de séances", "Organisation de la pratique", "Informations", "Affiliation",
    "Séance d'essai", "Expérience des encadrants", "Labels et programmes spécifiques", "Contact",
    "Téléphone", "Adresse email", "Site internet", "Facebook", "Twitter", "Instagram",
    "Lieu de la pratique", "Mutualisation des ressources", "Aller en haut de la page",
    "Notifier un problème",
]

HANDICAPS = ["visuel", "auditif", "moteur", "mental", "psychique", "autisme", "polyhandicap"]

# Chemins du site qui ne sont pas des fiches de structure
PAS_DES_FICHES = ("recherche-structure", "inscription-structure", "login", "aide", "contact",
                  "mentions-legales", "accessibilite", "plan-du-site", "charte-engagement")


def norm(s):
    s = unicodedata.normalize("NFD", s or "")
    return "".join(c for c in s if unicodedata.category(c) != "Mn").lower().strip()


def cle(s):
    """Clé de comparaison des noms : "Saint-Ouen Handibasket" et "Saint Ouen handibasket" sont le même club."""
    return re.sub(r"[^a-z0-9]", "", norm(s))


def decoller(s, sep=". "):
    """Le site colle les éléments d'une liste : "Handicap auditifHandicap moteur"."""
    return re.sub(r"([a-zà-ÿ\)\.])([A-ZÀ-Ý])", lambda m: m.group(1).rstrip(".") + sep + m.group(2), s or "")


# ===== Lecture d'une fiche (fonctions pures, testées dans tests/) =====
def nettoyer(texte):
    """Retire la syntaxe des liens Markdown, au cas où le texte vient d'un copier-coller."""
    texte = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", texte)
    return [l.strip() for l in texte.splitlines() if l.strip() and l.strip() != "*"]


def nom_structure(lignes):
    for i, l in enumerate(lignes):
        if l.startswith("Retourner aux résultats") and i + 1 < len(lignes):
            return lignes[i + 1]
    for i, l in enumerate(lignes):
        if l.startswith("Activité sportive") and i > 0:
            return lignes[i - 1]
    return ""


def sections(lignes):
    """Découpe les lignes de la fiche en rubriques {libellé: [lignes]}."""
    debut = 0
    for i, l in enumerate(lignes):
        if l.startswith("Activité sportive"):
            debut = i
            break
    res, courant = {}, None
    for l in lignes[debut:]:
        trouve = next((r for r in RUBRIQUES if l == r or l.startswith(r + " ") or l.startswith(r + ":")), None)
        if trouve:
            courant = trouve
            res.setdefault(courant, [])
            reste = l[len(trouve):].strip(" :")
            if reste:
                res[courant].append(reste)
        elif courant:
            res[courant].append(l)
    return res


def decouper_adresse(ligne):
    """'Gymnase X10 rue Y, 93200 Saint-Denis, France' -> (nom du lieu, rue, code postal, ville)."""
    ligne = re.sub(r",?\s*France$", "", ligne.strip())
    m = re.search(r"\b(\d{5})\s+([^,]+)", ligne)
    if m:
        cp, ville = m.group(1), m.group(2).strip()
        avant = ligne[:m.start()].strip(" ,")
    else:
        # Pas de code postal : la ville est le dernier morceau après une virgule
        morceaux = [x.strip() for x in ligne.split(",") if x.strip()]
        cp, ville = "", morceaux[-1] if len(morceaux) > 1 else ""
        avant = ", ".join(morceaux[:-1]) if len(morceaux) > 1 else ligne
    nom_lieu = ""
    # Nom du lieu collé à la rue : "Complexe Sportif du Franc Moisin10/12, Place des sports"
    coupe = re.match(r"^(.*?[a-zà-ÿ\)])(\d+.*)$", avant)
    if coupe:
        nom_lieu, avant = decoller(coupe.group(1).strip(), ", "), coupe.group(2).strip()
    else:
        # "Stade Auguste Delaune, Rue du 19 Mars 1962" ou "Centre équestre la CourneuveAvenue Roger Salengro" :
        # le dernier morceau est la rue, ce qui précède est le lieu
        morceaux = [x.strip() for x in decoller(avant, ", ").split(",") if x.strip()]
        if len(morceaux) > 1 and not re.match(r"^\d", morceaux[-1]) and re.search(r"\b(rue|avenue|boulevard|bd|place|chemin|allée|allee|route|quai|impasse|square|cours|voie)\b", norm(morceaux[-1])):
            nom_lieu, avant = ", ".join(morceaux[:-1]), morceaux[-1]
    avant = re.sub(r"\s+,", ",", avant)
    avant = re.sub(r"(\d+)/(\d+),\s*", r"\1-\2 ", avant)  # "10/12, Place" -> "10-12 Place"
    avant = re.sub(r"^(\d+[a-zA-Z]?),\s*", r"\1 ", avant)  # "2, rue" -> "2 rue"
    ville = re.sub(r"^(st|ste)\b\.?", lambda m: "Saint" if m.group(1).lower() == "st" else "Sainte", ville.strip(), flags=re.I)
    ville = re.sub(r"^(Saint|Sainte)\s+", r"\1-", ville)  # "Saint Denis" -> "Saint-Denis"
    return nom_lieu, avant.strip(" ,"), cp, ville


def lieux(lignes_lieu):
    """Une fiche peut avoir plusieurs lieux de pratique ("Adresse n° 1", "Adresse n° 2"…)."""
    res, courant, zone = [], None, None
    for l in lignes_lieu:
        if l.startswith("Adresse n°"):
            courant = {"adresse": "", "acces": []}
            res.append(courant)
            zone = "adresse"
            continue
        if courant is None:
            courant = {"adresse": "", "acces": []}
            res.append(courant)
            zone = "adresse"
        if l.startswith("Accessibilité du lieu"):
            zone = "acces"
            reste = l[len("Accessibilité du lieu"):].strip(" :")
            if reste:
                courant["acces"].append(reste)
        elif l.startswith("Estimez votre trajet") or l.startswith("Cliquez sur"):
            zone = None
        elif zone == "adresse" and not courant["adresse"]:
            courant["adresse"] = l
        elif zone == "acces":
            courant["acces"].append(l)
    return [x for x in res if x["adresse"]]


def pratique_de(handicaps, affiliation):
    aff = norm(affiliation)
    physique = any(h in handicaps for h in ["visuel", "auditif", "moteur"])
    adapte = any(h in handicaps for h in ["mental", "psychique", "autisme"])
    if ("handisport" in aff and "adapte" in aff) or (physique and adapte):
        return "les deux"
    if "adapte" in aff or adapte:
        return "sport adapte"
    return "handisport"


# Liens d'une fiche qui ne sont pas le site du club
LIENS_IGNORES = ("handiguide", "sports.gouv", "insep", "club-inclusif", "google.", "goo.gl", "twitter.com",
                 "x.com", "openstreetmap", "gouv.fr", "service-public")


def site_web(liens):
    """Le site du club, sinon sa page Facebook ou Instagram."""
    externes = [l for l in liens if re.match(r"^https?://[^\s]+$", l or "", re.I)
                and not any(x in urllib.parse.urlparse(l).netloc.lower() + urllib.parse.urlparse(l).path.lower() for x in LIENS_IGNORES)]
    reseaux = ("facebook.com", "instagram.com")
    propres = [l for l in externes if not any(r in l.lower() for r in reseaux)]
    sociaux = [l for l in externes if any(r in l.lower() for r in reseaux) and "sports.gouv" not in l.lower()]
    return (propres or sociaux or [""])[0]


def parse_fiche(texte, url="", liens=None):
    """Transforme le texte d'une fiche en lignes prêtes pour la base (une par sport et par lieu).
    `liens` : adresses des liens de la fiche (sinon, lues dans le texte s'il vient d'un copier-coller Markdown)."""
    if liens is None:
        liens = re.findall(r"\]\((https?://[^)\s]+)\)", texte) + re.findall(r"(?<!\()\bhttps?://[^\s)\]]+", texte)
    lignes = nettoyer(texte)
    s = sections(lignes)
    g = lambda k: " ".join(s.get(k, [])).strip()

    nom = nom_structure(lignes)
    sports = []
    for x in s.get("Activité sportive", []):
        sports += [y.strip() for y in re.split(r",|;", x) if y.strip()]

    h_txt = norm(g("Handicap(s)"))
    handicaps = [h for h in HANDICAPS if h in h_txt]
    if "intellectuel" in h_txt and "mental" not in handicaps:
        handicaps.append("mental")

    exp = norm(g("Expérience des encadrants"))
    habitude = "oui" if "habitude" in exp else ""
    forme = "oui" if ("habitude" in exp or re.search(r"\bforme", exp)) else ""
    labels = [x for x in s.get("Labels et programmes spécifiques", []) if not x.lower().startswith("site du ")]

    site = site_web(liens)
    tel = " ".join(s.get("Téléphone", [])[:1])
    email = " ".join(s.get("Adresse email", [])[:1])

    base = {
        "Nom": nom, "Handicaps": ", ".join(handicaps), "Pratique": pratique_de(handicaps, g("Affiliation")),
        "Creneaux": "", "Telephone": tel, "Email": email, "Site": site, "Label": ", ".join(labels),
        "Para sportifs au club": habitude, "Encadrant forme": forme, "Verifie le": "",
        "Essai": g("Séance d'essai"), "Latitude": "", "Longitude": "", "Source": url,
    }
    sortie = []
    for lieu in (lieux(s.get("Lieu de la pratique", [])) or [{"adresse": "", "acces": []}]):
        nom_lieu, rue, cp, ville = decouper_adresse(lieu["adresse"]) if lieu["adresse"] else ("", "", "", "")
        acces = ". ".join(x for x in [nom_lieu, decoller(" ".join(lieu["acces"]))] if x).strip()
        for sport in (sports or [""]):
            ligne = dict(base, Sport=sport.lower(), Adresse=rue, **{"Code postal": cp}, Ville=ville, Accessibilite=acces)
            sortie.append([ligne.get(c, "") for c in COLONNES])
    return sortie


# ===== Garde-fous =====
def robots_ok(url):
    rp = urllib.robotparser.RobotFileParser()
    rp.set_url(BASE + "/robots.txt")
    try:
        rp.read()
    except Exception:
        print("Impossible de lire robots.txt : on continue prudemment.")
        return True
    return rp.can_fetch(USER_AGENT, url) and rp.can_fetch("*", url)


def lire_url(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8")


def cles_deja_presentes():
    """Les noms des clubs déjà dans ta base Supabase."""
    noms = set()
    try:
        for debut in range(0, 100000, 1000):
            req = urllib.request.Request(
                f"{SUPABASE_URL}/rest/v1/clubs?select=nom&offset={debut}&limit=1000",
                headers={"apikey": SUPABASE_KEY, "User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=20) as r:
                page = json.loads(r.read().decode("utf-8"))
            noms |= {cle(l["nom"]) for l in page if l.get("nom")}
            if len(page) < 1000:
                break
    except Exception as e:
        print(f"Impossible de lire ta base Supabase ({e}) : aucun doublon ne sera filtré.")
    return noms


def geocoder(rue, cp, ville):
    """Coordonnées via la Base Adresse Nationale (données publiques), pour que la carte s'affiche vite."""
    q = " ".join(x for x in [rue, cp, ville] if x)
    if not q:
        return "", ""
    for geocodeur in GEOCODEURS:
        try:
            data = json.loads(lire_url(geocodeur + urllib.parse.quote(q)))
        except Exception:
            continue
        if not data.get("features"):
            return "", ""
        f = data["features"][0]
        if cp and (f["properties"].get("postcode") or cp)[:2] != cp[:2]:
            return "", ""
        lon, lat = f["geometry"]["coordinates"]
        return f"{lat:.6f}", f"{lon:.6f}"
    return "", ""


# ===== Liste des fiches =====
def est_fiche(url):
    p = urllib.parse.urlparse(url)
    if p.netloc and "handiguide" not in p.netloc:
        return False
    chemin = p.path.lower()
    return "structure" in chemin and not any(x in chemin for x in PAS_DES_FICHES)


def liens_de_la_page(page):
    vus = set()
    for href in page.eval_on_selector_all("a[href]", "els => els.map(e => e.getAttribute('href'))"):
        plein = urllib.parse.urljoin(BASE + "/", href or "").split("#")[0]
        if est_fiche(plein):
            vus.add(plein)
    return vus


def liens_fiches(page, url_recherche, pause, debug=False):
    page.goto(url_recherche, wait_until="networkidle", timeout=90000)
    page.wait_for_timeout(2000)
    vus = liens_de_la_page(page)
    print(f"  {len(vus)} fiches sur la première page…")

    for _ in range(500):
        bouton = None
        for texte in ["Voir plus", "Charger plus", "Afficher plus", "Plus de résultats", "Suivant", "Page suivante"]:
            for b in page.query_selector_all(f"button:has-text('{texte}'), a:has-text('{texte}')"):
                if b.is_visible() and b.is_enabled() and b.get_attribute("aria-disabled") != "true":
                    bouton = b
                    break
            if bouton:
                break
        if not bouton:
            # Pagination par numéros de page ("›", "»" ou aria-label "page suivante")
            bouton = page.query_selector("a[aria-label*='suivante' i], button[aria-label*='suivante' i], a[rel='next']")
            if bouton and not (bouton.is_visible() and bouton.is_enabled()):
                bouton = None
        if not bouton:
            break
        avant = len(vus)
        bouton.click()
        page.wait_for_timeout(pause * 1000)
        try:
            page.wait_for_load_state("networkidle", timeout=30000)
        except Exception:
            pass
        vus |= liens_de_la_page(page)
        if len(vus) == avant:
            break
        print(f"  {len(vus)} fiches trouvées…")

    if debug or not vus:
        with open("debug_recherche.html", "w", encoding="utf-8") as f:
            f.write(page.content())
        print("  Page de recherche enregistrée dans debug_recherche.html (pour ajuster le script).")
    return sorted(vus)


def texte_fiche(page, url):
    page.goto(url, wait_until="networkidle", timeout=60000)
    try:
        page.wait_for_selector("text=Activité sportive", timeout=15000)
    except Exception:
        pass
    zone = "main" if page.query_selector("main") else "body"
    texte = page.inner_text(zone)
    liens = page.eval_on_selector_all(zone + " a[href]", "els => els.map(e => e.href)")
    return texte, liens


# ===== Progression (reprise après interruption) =====
def charger_progression():
    try:
        with open(PROGRESSION, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"faites": [], "lignes": []}


def sauver_progression(p):
    tmp = PROGRESSION + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(p, f, ensure_ascii=False)
    os.replace(tmp, PROGRESSION)


COLONNES_SQL = [
    "sport", "nom", "adresse", "code_postal", "ville", "handicaps", "pratique", "creneaux",
    "accessibilite", "telephone", "email", "site", "label", "para_sportifs",
    "encadrant_forme", "verifie_le", "essai", "latitude", "longitude", "source",
]


def vers_sql(lignes):
    """Lignes du scraper -> requête à coller dans Supabase (SQL Editor → New query → Run)."""
    def val(col, v):
        v = (v or "").strip()
        if col in ("para_sportifs", "encadrant_forme"):
            return "true" if v == "oui" else "false"
        if not v:
            return "null"
        if col in ("latitude", "longitude"):
            return str(float(v))
        if col == "sport":
            v = v.lower()
        return "'" + v.replace("'", "''") + "'"
    if not lignes:
        return "-- aucun nouveau club\n"
    valeurs = ["  (" + ", ".join(val(c, x) for c, x in zip(COLONNES_SQL, l)) + ")" for l in lignes]
    return (f"-- {len(valeurs)} lignes venant du Handiguide des sports\n"
            f"insert into public.clubs ({', '.join(COLONNES_SQL)}) values\n" + ",\n".join(valeurs) + ";\n")


def ecrire_sorties(lignes, base):
    propre = lambda x: (x or "").replace("\t", " ").replace("\r", " ").replace("\n", " ").strip()
    with open(base + ".sql", "w", encoding="utf-8") as f:
        f.write(vers_sql([[propre(x) for x in l] for l in lignes]))
    with open(base + ".csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(COLONNES)
        w.writerows([[propre(x) for x in l] for l in lignes])


def main(argv=None):
    ap = argparse.ArgumentParser(description="Collecte les fiches du Handiguide des sports pour Paralliance.",
                                 add_help=False)
    ap.add_argument("url", nargs="?", help="adresse d'une page de recherche du Handiguide")
    ap.add_argument("--test", action="store_true", help="ne lit que 5 fiches")
    ap.add_argument("--limite", type=int, default=0, help="nombre maximum de fiches à lire")
    ap.add_argument("--pause", type=float, default=PAUSE, help=f"secondes entre deux fiches (minimum {PAUSE})")
    ap.add_argument("--sortie", default="nouveaux_clubs", help="nom des fichiers de sortie (sans extension)")
    ap.add_argument("--sans-geo", action="store_true", help="ne calcule pas Latitude/Longitude")
    ap.add_argument("--recommencer", action="store_true", help="ignore la progression enregistrée")
    ap.add_argument("--visible", action="store_true", help="affiche le navigateur pendant la collecte")
    ap.add_argument("--debug", action="store_true", help="enregistre les pages lues pour diagnostic")
    ap.add_argument("--fichier", help="lit une fiche copiée-collée dans un fichier texte, sans aller sur le site")
    ap.add_argument("-h", "--aide", "--help", action="help", help="affiche cette aide")
    a = ap.parse_args(argv)
    pause = max(a.pause, PAUSE)

    # Mode hors ligne : une fiche copiée-collée depuis le navigateur
    if a.fichier:
        with open(a.fichier, encoding="utf-8") as f:
            blocs = re.split(r"(?im)^fiche\s*\d+\s*[:;]?", f.read())
        lignes = [l for b in blocs if b.strip() for l in parse_fiche(b)]
        deja = cles_deja_presentes()
        avant = len(lignes)
        lignes = [l for l in lignes if l[1] and cle(l[1]) not in deja]
        if avant > len(lignes):
            print(f"{avant - len(lignes)} ligne(s) ignorée(s) : club déjà dans ta base ou fiche illisible.")
        if not a.sans_geo:
            for l in lignes:
                l[17], l[18] = geocoder(l[2], l[3], l[4])
        ecrire_sorties(lignes, a.sortie)
        print(f"{len(lignes)} lignes écrites dans {a.sortie}.sql et {a.sortie}.csv")
        return

    if not a.url:
        print(__doc__)
        return
    if "handiguide.sports.gouv.fr" not in a.url:
        print("L'adresse doit être une page de recherche du Handiguide (handiguide.sports.gouv.fr).")
        return
    if not robots_ok(a.url):
        print("Le fichier robots.txt du site interdit cette collecte. Arrêt.")
        return

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Playwright n'est pas installé. Tape :\n  pip install playwright\n  playwright install chromium")
        return

    deja = cles_deja_presentes()
    print(f"{len(deja)} clubs déjà dans ton tableau.")
    prog = {"faites": [], "lignes": []} if a.recommencer else charger_progression()
    faites = set(prog["faites"])
    if faites:
        print(f"Reprise : {len(faites)} fiches déjà lues lors d'un lancement précédent.")
    noms_lus = {cle(l[1]) for l in prog["lignes"]}
    ignores = 0

    with sync_playwright() as p:
        nav = p.chromium.launch(headless=not a.visible)
        page = nav.new_page(user_agent=USER_AGENT, locale="fr-FR")
        try:
            print("Recherche des fiches…")
            liens = liens_fiches(page, a.url, pause, a.debug)
            print(f"{len(liens)} fiches trouvées.")
            if not liens:
                print("Aucune fiche trouvée : envoie le fichier debug_recherche.html pour ajuster le script.")
                return
            a_lire = [l for l in liens if l not in faites]
            limite = 5 if a.test else a.limite
            if limite:
                a_lire = a_lire[:limite]

            for i, lien in enumerate(a_lire, 1):
                etape = f"[{i}/{len(a_lire)}]"
                try:
                    texte, liens_fiche = texte_fiche(page, lien)
                    if a.debug:
                        os.makedirs("debug_fiches", exist_ok=True)
                        with open(os.path.join("debug_fiches", re.sub(r"\W+", "_", lien)[-80:] + ".txt"), "w", encoding="utf-8") as f:
                            f.write(texte)
                    lignes = parse_fiche(texte, lien, liens_fiche)
                except Exception as e:
                    print(f"{etape} Erreur sur {lien} : {e}")
                    time.sleep(pause)
                    continue
                nom = lignes[0][1] if lignes else ""
                if not nom:
                    print(f"{etape} Fiche illisible : {lien} (relance avec --debug pour voir son texte)")
                elif cle(nom) in deja or cle(nom) in noms_lus:
                    ignores += 1
                    print(f"{etape} Déjà présent : {nom}")
                else:
                    if not a.sans_geo:
                        for l in lignes:
                            l[17], l[18] = geocoder(l[2], l[3], l[4])
                    prog["lignes"].extend(lignes)
                    noms_lus.add(cle(nom))
                    print(f"{etape} OK : {nom} ({len(lignes)} ligne(s))")
                prog["faites"].append(lien)
                sauver_progression(prog)
                ecrire_sorties(prog["lignes"], a.sortie)
                time.sleep(pause)
        except KeyboardInterrupt:
            print("\nInterrompu : relance la même commande pour reprendre.")
        finally:
            nav.close()

    ecrire_sorties(prog["lignes"], a.sortie)
    print(f"\nTerminé : {len(prog['lignes'])} lignes dans {a.sortie}.sql et {a.sortie}.csv ({ignores} clubs déjà présents ignorés).")


if __name__ == "__main__":
    main()
