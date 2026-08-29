#!/usr/bin/env python3
"""
KLAXO — branche la section COD dans une copie de Dawn.

Trois modifications, toutes idempotentes :

  1. templates/product.json — insère la section KLAXO et RETIRE le bouton
     d'ajout au panier ainsi que le sélecteur de quantité.
  2. layout/theme.liquid    — déclare window.KLAXO_CONFIG (URL du Worker).
  3. config/settings_schema.json — ajoute le réglage WhatsApp utilisé par le
     bloc confiance.

Pourquoi retirer le bouton d'achat : laisser cohabiter « Ajouter au panier » et
le formulaire COD envoie une partie des clients dans le checkout Shopify, que
tout le reste du dispositif contourne. Ces commandes échappent alors au
formulaire, au tracking d'attribution et à la feuille de confirmation — donc au
calcul de CPA. Une page produit COD n'a qu'un seul chemin de sortie.
"""

import json
import sys
from pathlib import Path

MARQUEUR = "KLAXO_CONFIG"

CONFIG_LIQUID = """
  {%- comment -%}
    KLAXO — URL du Worker de tracking (Phase 2).
    Cette URL est publique par nature, ce n'est pas un secret : les jetons Meta,
    TikTok et Shopify restent côté Cloudflare. Remplacer <sous-domaine> par le
    tien après « wrangler deploy ».
  {%- endcomment -%}
  <script>
    window.KLAXO_CONFIG = {
      workerUrl: "https://klaxo-tracking.<sous-domaine>.workers.dev"
    };
  </script>
"""

REGLAGES_KLAXO = {
    "name": "KLAXO",
    "settings": [
        {
            "type": "text",
            "id": "klaxo_whatsapp",
            "label": "Numéro WhatsApp",
            "info": "Format international, ex. +212612345678. Utilisé par le bloc confiance.",
            "default": "",
        }
    ],
}

# Blocs de la page produit Dawn incompatibles avec un parcours COD une-étape.
BLOCS_A_RETIRER = ("buy_buttons", "quantity_selector")


def modifier_product_json(racine: Path) -> None:
    chemin = racine / "templates" / "product.json"
    donnees = json.loads(chemin.read_text(encoding="utf-8"))
    sections = donnees.setdefault("sections", {})

    principal = sections.get("main", {})
    blocs = principal.get("blocks", {})
    retires = [nom for nom in BLOCS_A_RETIRER if nom in blocs]
    for nom in retires:
        del blocs[nom]
    if "block_order" in principal:
        principal["block_order"] = [
            b for b in principal["block_order"] if b not in BLOCS_A_RETIRER
        ]

    sections["klaxo_offer"] = {"type": "klaxo-offer", "settings": {}}

    ordre = donnees.setdefault("order", [])
    if "klaxo_offer" not in ordre:
        # Juste après le bloc produit principal : le client voit le produit,
        # puis immédiatement le choix de pack et le formulaire.
        position = ordre.index("main") + 1 if "main" in ordre else len(ordre)
        ordre.insert(position, "klaxo_offer")

    chemin.write_text(
        json.dumps(donnees, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"  product.json : section ajoutée, blocs retirés = {retires or 'aucun'}")


def modifier_theme_liquid(racine: Path) -> None:
    chemin = racine / "layout" / "theme.liquid"
    contenu = chemin.read_text(encoding="utf-8")

    if MARQUEUR in contenu:
        print("  theme.liquid : déjà branché, ignoré")
        return

    if "</head>" not in contenu:
        raise SystemExit("ERREUR : </head> introuvable dans layout/theme.liquid")

    contenu = contenu.replace("</head>", CONFIG_LIQUID + "</head>", 1)
    chemin.write_text(contenu, encoding="utf-8")
    print("  theme.liquid : window.KLAXO_CONFIG déclaré")


def modifier_settings_schema(racine: Path) -> None:
    chemin = racine / "config" / "settings_schema.json"
    groupes = json.loads(chemin.read_text(encoding="utf-8"))

    if any(g.get("name") == "KLAXO" for g in groupes):
        print("  settings_schema.json : déjà présent, ignoré")
        return

    groupes.append(REGLAGES_KLAXO)
    chemin.write_text(
        json.dumps(groupes, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print("  settings_schema.json : réglage WhatsApp ajouté")


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage : wire_theme.py <racine-du-theme>")

    racine = Path(sys.argv[1])
    if not (racine / "layout" / "theme.liquid").exists():
        raise SystemExit(f"ERREUR : {racine} ne ressemble pas à un thème Shopify")

    modifier_product_json(racine)
    modifier_theme_liquid(racine)
    modifier_settings_schema(racine)


if __name__ == "__main__":
    main()
