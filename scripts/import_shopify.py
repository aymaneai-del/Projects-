#!/usr/bin/env python3
"""
KLAXO — import des produits, collection, pages et menus dans Shopify.

Le jeton est lu UNIQUEMENT depuis l'environnement (SHOPIFY_ADMIN_TOKEN).
Il n'est écrit dans aucun fichier et n'apparaît dans aucune sortie.

Le thème n'est pas géré ici : il est poussé par la CLI Shopify, qui sait
synchroniser un thème entier et gérer les fichiers ignorés.

Chaque étape vérifie l'existence par handle avant de créer : relancer le
script ne produit pas de doublons.

Usage :
    SHOPIFY_STORE=6m1kid-eg SHOPIFY_ADMIN_TOKEN=shpat_... \\
      python3 scripts/import_shopify.py [--dry-run]
"""

import csv
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

API_VERSION = os.environ.get("SHOPIFY_API_VERSION", "2026-07")
RACINE = Path(__file__).resolve().parent.parent

DRY_RUN = "--dry-run" in sys.argv


# ── Sortie ────────────────────────────────────────────────────────────────────

def etape(titre):
    print(f"\n\033[1m{titre}\033[0m")


def ok(msg):
    print(f"  \033[32m✓\033[0m {msg}")


def saute(msg):
    print(f"  \033[33m•\033[0m {msg}")


def echec(msg):
    print(f"  \033[31m✗\033[0m {msg}", file=sys.stderr)


# ── Transport ─────────────────────────────────────────────────────────────────

class Shopify:
    def __init__(self, boutique, jeton):
        self.base = f"https://{boutique}.myshopify.com/admin/api/{API_VERSION}"
        self.jeton = jeton

    def _appel(self, url, methode="GET", corps=None, entetes=None):
        donnees = json.dumps(corps).encode() if corps is not None else None
        req = urllib.request.Request(url, data=donnees, method=methode)
        req.add_header("X-Shopify-Access-Token", self.jeton)
        req.add_header("Content-Type", "application/json")
        req.add_header("Accept", "application/json")
        for k, v in (entetes or {}).items():
            req.add_header(k, v)

        for tentative in range(5):
            try:
                with urllib.request.urlopen(req, timeout=60) as r:
                    return json.loads(r.read().decode() or "{}")
            except urllib.error.HTTPError as e:
                texte = e.read().decode(errors="replace")
                # 429 : quota d'appels dépassé. Shopify indique combien attendre.
                if e.code == 429 and tentative < 4:
                    pause = float(e.headers.get("Retry-After", 2))
                    time.sleep(pause)
                    continue
                if e.code >= 500 and tentative < 4:
                    time.sleep(2 ** tentative)
                    continue
                raise RuntimeError(f"HTTP {e.code} sur {methode} {url.split('/admin')[-1]} — {texte[:400]}")
            except urllib.error.URLError as e:
                if tentative < 4:
                    time.sleep(2 ** tentative)
                    continue
                raise RuntimeError(f"réseau : {e}")
        raise RuntimeError("échec après 5 tentatives")

    def rest(self, chemin, methode="GET", corps=None):
        return self._appel(f"{self.base}/{chemin}", methode, corps)

    def graphql(self, requete, variables=None):
        r = self._appel(
            f"{self.base}/graphql.json", "POST",
            {"query": requete, "variables": variables or {}},
        )
        if r.get("errors"):
            raise RuntimeError(f"GraphQL : {json.dumps(r['errors'])[:400]}")
        return r["data"]


# ── 1. Produits ───────────────────────────────────────────────────────────────

def charger_csv():
    """Regroupe les lignes du CSV par handle : une ligne = une variante."""
    produits = {}
    with open(RACINE / "data" / "klaxo-produits.csv", encoding="utf-8") as f:
        for ligne in csv.DictReader(f):
            h = ligne["Handle"]
            p = produits.setdefault(h, {"handle": h, "variantes": []})
            # Les colonnes de la fiche ne sont remplies que sur la 1re ligne.
            if ligne["Title"]:
                p.update({
                    "title": ligne["Title"],
                    "body_html": ligne["Body (HTML)"],
                    "vendor": ligne["Vendor"],
                    "product_type": ligne["Type"],
                    "tags": ligne["Tags"],
                    "seo_title": ligne["SEO Title"],
                    "seo_description": ligne["SEO Description"],
                    "option_name": ligne["Option1 Name"],
                })
            p["variantes"].append({
                "option1": ligne["Option1 Value"],
                "price": ligne["Variant Price"],
                "sku": ligne["Variant SKU"],
                "grams": int(ligne["Variant Grams"] or 0),
                "inventory_management": "shopify",
                "inventory_policy": "continue",
                "requires_shipping": True,
                "taxable": True,
            })
    return list(produits.values())


def importer_produits(api):
    etape("1. Produits")
    existants = {p["handle"]: p["id"]
                 for p in api.rest("products.json?limit=250&fields=id,handle")["products"]}
    resultat = {}

    for p in charger_csv():
        if p["handle"] in existants:
            saute(f"{p['title']} — existe déjà, non modifié")
            resultat[p["handle"]] = existants[p["handle"]]
            continue

        charge = {"product": {
            "title": p["title"], "handle": p["handle"], "body_html": p["body_html"],
            "vendor": p["vendor"], "product_type": p["product_type"], "tags": p["tags"],
            "status": "active", "published": True,
            "options": [{"name": p["option_name"] or "Title"}],
            "variants": p["variantes"],
            "metafields_global_title_tag": p["seo_title"],
            "metafields_global_description_tag": p["seo_description"],
        }}

        if DRY_RUN:
            saute(f"[essai] créerait {p['title']} ({len(p['variantes'])} variante(s))")
            continue

        cree = api.rest("products.json", "POST", charge)["product"]
        resultat[p["handle"]] = cree["id"]
        prix = " / ".join(v["price"] + " DH" for v in p["variantes"])
        ok(f"{p['title']} — {len(p['variantes'])} variante(s) : {prix}")

    return resultat


# ── 2. Collection ─────────────────────────────────────────────────────────────

def importer_collection(api, ids_produits):
    etape("2. Collection")
    handle = "nos-produits"

    for c in api.rest("custom_collections.json?limit=250&fields=id,handle")["custom_collections"]:
        if c["handle"] == handle:
            saute("« Nos produits » — existe déjà, non modifiée")
            return c["id"]

    if DRY_RUN:
        saute(f"[essai] créerait « Nos produits » avec {len(ids_produits)} produits")
        return None

    col = api.rest("custom_collections.json", "POST", {"custom_collection": {
        "title": "Nos produits", "handle": handle, "published": True,
    }})["custom_collection"]

    for pid in ids_produits.values():
        api.rest("collects.json", "POST",
                 {"collect": {"collection_id": col["id"], "product_id": pid}})

    ok(f"« Nos produits » — {len(ids_produits)} produits rattachés")
    return col["id"]


# ── 3. Pages ──────────────────────────────────────────────────────────────────

# handle → (titre, suffixe de gabarit). Le suffixe pointe le fichier
# templates/page.<suffixe>.json du thème.
PAGES = [
    ("faq",       "FAQ",                   "faq"),
    ("livraison", "Livraison & paiement",  "livraison"),
    ("retour",    "Retour & échange",      "retour"),
    ("contact",   "Contact",               "contact"),
]


def importer_pages(api):
    etape("3. Pages")
    existantes = {p["handle"]: p
                  for p in api.rest("pages.json?limit=250&fields=id,handle,template_suffix")["pages"]}

    for handle, titre, suffixe in PAGES:
        if handle in existantes:
            actuel = existantes[handle].get("template_suffix")
            if actuel == suffixe:
                saute(f"{titre} — existe déjà avec le bon gabarit")
            elif not DRY_RUN:
                # La page existe mais pointe le mauvais gabarit : c'est le cas
                # qui donne une page vide. On corrige plutôt que de recréer.
                api.rest(f"pages/{existantes[handle]['id']}.json", "PUT",
                         {"page": {"id": existantes[handle]["id"], "template_suffix": suffixe}})
                ok(f"{titre} — gabarit corrigé ({actuel or 'aucun'} → page.{suffixe})")
            else:
                saute(f"[essai] corrigerait le gabarit de {titre}")
            continue

        if DRY_RUN:
            saute(f"[essai] créerait /pages/{handle} → page.{suffixe}")
            continue

        api.rest("pages.json", "POST", {"page": {
            "title": titre, "handle": handle, "template_suffix": suffixe,
            "body_html": "", "published": True,
        }})
        ok(f"{titre} — /pages/{handle} → page.{suffixe}")


# ── 4. Menus ──────────────────────────────────────────────────────────────────

MENUS = [
    ("main-menu", "Menu principal", [
        ("Accueil",      "FRONTPAGE",  None),
        ("Nos produits", "COLLECTION", "nos-produits"),
        ("Livraison",    "PAGE",       "livraison"),
        ("FAQ",          "PAGE",       "faq"),
        ("Contact",      "PAGE",       "contact"),
    ]),
    ("aide", "Aide", [
        ("Livraison & paiement", "PAGE", "livraison"),
        ("Retour & échange",     "PAGE", "retour"),
        ("FAQ",                  "PAGE", "faq"),
        ("Contact",              "PAGE", "contact"),
    ]),
    ("legal", "Légal", [
        ("CGV",             "HTTP", "/policies/terms-of-service"),
        ("Confidentialité", "HTTP", "/policies/privacy-policy"),
        ("Retour",          "PAGE", "retour"),
    ]),
]

Q_MENUS = "{ menus(first: 50) { nodes { id handle title } } }"

M_CREER_MENU = """
mutation($handle: String!, $title: String!, $items: [MenuItemCreateInput!]!) {
  menuCreate(handle: $handle, title: $title, items: $items) {
    menu { id handle }
    userErrors { field message }
  }
}
"""


def importer_menus(api, ids_pages_par_handle):
    etape("4. Menus")
    existants = {m["handle"] for m in api.graphql(Q_MENUS)["menus"]["nodes"]}

    for handle, titre, entrees in MENUS:
        if handle in existants:
            saute(f"{titre} — existe déjà, non modifié")
            continue

        items = []
        for libelle, genre, cible in entrees:
            item = {"title": libelle, "type": genre}
            if genre in ("PAGE", "COLLECTION"):
                # menuCreate exige un gid://, jamais un handle : gids() les
                # résout pour les pages comme pour la collection.
                gid = ids_pages_par_handle.get(cible)
                if not gid:
                    echec(f"{titre} : « {cible} » introuvable, entrée ignorée")
                    continue
                item["resourceId"] = gid
            elif genre == "HTTP":
                item["url"] = cible
            items.append(item)

        if DRY_RUN:
            saute(f"[essai] créerait « {titre} » ({len(items)} entrées)")
            continue

        r = api.graphql(M_CREER_MENU, {"handle": handle, "title": titre, "items": items})
        erreurs = r["menuCreate"]["userErrors"]
        if erreurs:
            echec(f"{titre} : {json.dumps(erreurs)[:300]}")
        else:
            ok(f"{titre} — {len(items)} entrées")


def gids(api):
    """Résout les identifiants GraphQL des pages et de la collection.

    Les menus GraphQL exigent des gid://, pas les identifiants REST.
    """
    d = api.graphql("""{
      pages(first: 50) { nodes { id handle } }
      collections(first: 50) { nodes { id handle } }
    }""")
    ids = {n["handle"]: n["id"] for n in d["pages"]["nodes"]}
    ids.update({n["handle"]: n["id"] for n in d["collections"]["nodes"]})
    return ids


# ── Point d'entrée ────────────────────────────────────────────────────────────

def main():
    boutique = os.environ.get("SHOPIFY_STORE")
    jeton = os.environ.get("SHOPIFY_ADMIN_TOKEN")

    if not boutique or not jeton:
        echec("SHOPIFY_STORE et SHOPIFY_ADMIN_TOKEN doivent être dans l'environnement.")
        sys.exit(2)

    api = Shopify(boutique, jeton)

    etape("0. Vérification du jeton")
    try:
        shop = api.rest("shop.json")["shop"]
    except RuntimeError as e:
        echec(str(e))
        echec("Vérifie que l'app est installée et que les droits sont cochés.")
        sys.exit(1)
    ok(f"connecté à « {shop['name'] } » ({shop['domain']}) · devise {shop['currency']}")

    if DRY_RUN:
        print("\n\033[33mMODE ESSAI — rien ne sera créé.\033[0m")

    ids_produits = importer_produits(api)
    importer_collection(api, ids_produits)
    importer_pages(api)

    if not DRY_RUN:
        # Les menus référencent des pages et une collection : elles doivent
        # exister avant, d'où la résolution des gid à ce moment précis.
        importer_menus(api, gids(api))
    else:
        etape("4. Menus")
        saute("[essai] créerait main-menu, aide et legal")

    print("\n\033[1mTerminé.\033[0m")
    print("  Le thème n'est PAS publié : previsualise-le, puis publie-le toi-même.")
    print("  Pense à désinstaller l'app « KLAXO Import » quand tu as fini.")


if __name__ == "__main__":
    main()
