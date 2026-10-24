"""Vérifie chaque mois les liens vers les sites des clubs et écrit la liste des liens à revoir dans LIENS_A_VERIFIER.md.

Un lien est signalé quand le site ne répond plus, renvoie une erreur (404…), ou affiche un contenu suspect :
un nom de domaine abandonné est souvent racheté par un site de casino ou de paris en ligne.
Le fichier est réécrit à chaque passage ; il est vide de signalements quand tout va bien.

Utilisation : python3 scripts/verifier_liens.py
"""
import concurrent.futures
import datetime
import html
import json
import os
import re
import urllib.request

from generer_pages import SUPABASE_KEY, SUPABASE_URL

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SUSPECT = re.compile(r"\b(casino|slot|gacor|togel|judi|poker|betting|viagra|cialis|porn|escort|forex|bandar|"
                     r"domain (?:is )?for sale|buy this domain|ce domaine est (?:à vendre|en vente)|this domain has expired)\b", re.I)


def clubs():
    lignes = []
    while True:
        url = f"{SUPABASE_URL}/rest/v1/clubs?select=id,nom,ville,site&site=not.is.null&order=id.asc&offset={len(lignes)}&limit=1000"
        with urllib.request.urlopen(urllib.request.Request(url, headers={"apikey": SUPABASE_KEY}), timeout=60) as r:
            page = json.load(r)
        lignes += page
        if len(page) < 1000:
            return [c for c in lignes if (c.get("site") or "").strip()]


def verifier(site):
    url = site if site.startswith("http") else "https://" + site
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Paralliance, verification des liens; contact@paralliance.org)"})
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            page = r.read(400000).decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return None if e.code in (401, 403, 429) else f"erreur {e.code}"     # 403 : site qui bloque les robots, pas un lien mort
    except Exception:
        return "le site ne répond pas"
    titre = re.search(r"<title[^>]*>(.*?)</title>", page, re.S | re.I)
    texte = html.unescape(re.sub(r"<[^>]+>", " ", re.sub(r"<script.*?</script>|<style.*?</style>", "", page, flags=re.S)))
    m = SUSPECT.search(texte[:20000]) or SUSPECT.search(titre.group(1) if titre else "")
    return f"contenu suspect (« {m.group(0)} »)" if m else None


def main():
    liste = clubs()
    sites = sorted({c["site"].strip() for c in liste})
    with concurrent.futures.ThreadPoolExecutor(8) as ex:
        resultats = dict(zip(sites, ex.map(verifier, sites)))
    problemes = [(c, resultats[c["site"].strip()]) for c in liste if resultats[c["site"].strip()]]
    lignes = [f"# Liens à vérifier ({datetime.date.today().isoformat()})", "",
              f"{len(sites)} sites contrôlés, {len(problemes)} à revoir.", ""]
    if problemes:
        lignes += ["Ouvre chaque lien dans ton navigateur. S'il est mort ou suspect, vide la case « site » du club dans Supabase.", "",
                   "| Club | Ville | Lien | Problème |", "|---|---|---|---|"]
        lignes += [f"| {c['nom']} | {c['ville'] or ''} | {c['site']} | {p} |" for c, p in problemes]
    with open(os.path.join(RACINE, "LIENS_A_VERIFIER.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lignes) + "\n")
    print(f"{len(sites)} sites contrôlés, {len(problemes)} à revoir.")


if __name__ == "__main__":
    main()
