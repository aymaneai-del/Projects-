#!/usr/bin/env python3
"""
KLAXO — branche la marque et le dispositif COD dans une copie de Dawn.

Toutes les modifications sont idempotentes : relancer le script sur un thème
déjà branché ne le casse pas et ne duplique rien.

  1. layout/theme.liquid          polices, CSS/JS de marque, config du Worker,
                                  bouton WhatsApp flottant
  2. sections/header-group.json   barre d'annonce + en-tête KLAXO
  3. sections/footer-group.json   pied de page KLAXO
  4. templates/product.json       section offre COD, sans bouton panier
  5. config/settings_schema.json  WhatsApp et réseaux sociaux

Les autres templates (index, collection, pages) sont versionnés dans
theme/templates/ et simplement copiés par le script de build : les générer
ici les écraserait à chaque construction.

Pourquoi retirer le bouton d'achat de la page produit : laisser cohabiter
« Ajouter au panier » et le formulaire COD envoie une partie des clients dans
le checkout Shopify, que tout le reste du dispositif contourne. Ces commandes
échappent alors au formulaire, au tracking d'attribution et à la feuille de
confirmation — donc au calcul de CPA. Une page produit COD n'a qu'un seul
chemin de sortie.
"""

import json
import sys
from pathlib import Path

MARQUEUR = "KLAXO_CONFIG"

TETE_LIQUID = """
  {%- comment -%} KLAXO — marque et tracking {%- endcomment -%}
  {%- comment -%}
    KLAXO — polices auto-hébergées.

    Servies par le CDN Shopify plutôt que par Google Fonts. Sur de la 4G
    marocaine, passer par fonts.googleapis.com puis fonts.gstatic.com coûte
    deux résolutions DNS et deux poignées de main TLS avant le premier octet
    de police — plusieurs centaines de millisecondes sur le budget LCP.

    Seuls les sous-ensembles latin et latin-ext sont embarqués. Grâce à
    unicode-range, latin-ext n'est téléchargé que si un caractère de sa plage
    apparaît réellement : sur un site en français, il ne se charge jamais.
    Charge réelle : latin uniquement.
  {%- endcomment -%}
  {%- comment -%}
    Pas de preload volontairement. Avec font-display: swap, le texte s'affiche
    tout de suite en police de repli : précharger ne gagne pas de LCP, ça met
    47 Ko en concurrence avec l'image produit — qui est, elle, le vrai élément
    LCP — sur une bande passante 4G limitée.
  {%- endcomment -%}
  <style>
    @font-face {
      font-family: 'Bricolage Grotesque';
      font-style: normal;
      /* Police variable : un seul fichier couvre toute la plage de graisses. */
      font-weight: 600 800;
      font-display: swap;
      src: url({{ 'klaxo-bricolage-grotesque-latin.woff2' | asset_url }}) format('woff2');
      unicode-range: U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, U+02DC, U+0304, U+0308, U+0329, U+2000-206F, U+20AC, U+2122, U+2191, U+2193, U+2212, U+2215, U+FEFF, U+FFFD;
    }
    @font-face {
      font-family: 'Bricolage Grotesque';
      font-style: normal;
      /* Police variable : un seul fichier couvre toute la plage de graisses. */
      font-weight: 600 800;
      font-display: swap;
      src: url({{ 'klaxo-bricolage-grotesque-latin-ext.woff2' | asset_url }}) format('woff2');
      unicode-range: U+0100-02BA, U+02BD-02C5, U+02C7-02CC, U+02CE-02D7, U+02DD-02FF, U+0304, U+0308, U+0329, U+1D00-1DBF, U+1E00-1E9F, U+1EF2-1EFF, U+2020, U+20A0-20AB, U+20AD-20C0, U+2113, U+2C60-2C7F, U+A720-A7FF;
    }
    @font-face {
      font-family: 'Inter';
      font-style: normal;
      /* Police variable : un seul fichier couvre toute la plage de graisses. */
      font-weight: 400 700;
      font-display: swap;
      src: url({{ 'klaxo-inter-latin.woff2' | asset_url }}) format('woff2');
      unicode-range: U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, U+02DC, U+0304, U+0308, U+0329, U+2000-206F, U+20AC, U+2122, U+2191, U+2193, U+2212, U+2215, U+FEFF, U+FFFD;
    }
    @font-face {
      font-family: 'Inter';
      font-style: normal;
      /* Police variable : un seul fichier couvre toute la plage de graisses. */
      font-weight: 400 700;
      font-display: swap;
      src: url({{ 'klaxo-inter-latin-ext.woff2' | asset_url }}) format('woff2');
      unicode-range: U+0100-02BA, U+02BD-02C5, U+02C7-02CC, U+02CE-02D7, U+02DD-02FF, U+0304, U+0308, U+0329, U+1D00-1DBF, U+1E00-1E9F, U+1EF2-1EFF, U+2020, U+20A0-20AB, U+20AD-20C0, U+2113, U+2C60-2C7F, U+A720-A7FF;
    }
  </style>
  {{ 'klaxo-brand.css' | asset_url | stylesheet_tag }}

  {%- comment -%}
    URL du Worker de tracking (Phase 2). Publique par nature, ce n'est pas un
    secret : les jetons Meta, TikTok et Shopify restent côté Cloudflare.
    Remplacer <sous-domaine> par le tien après « wrangler deploy ».
  {%- endcomment -%}
  <script>
    window.KLAXO_CONFIG = {
      workerUrl: "https://klaxo-tracking.<sous-domaine>.workers.dev"
    };
  </script>
"""

PIED_LIQUID = """
  {%- render 'klaxo-whatsapp-float' -%}
  <script src="{{ 'klaxo-brand.js' | asset_url }}" defer></script>
"""

REGLAGES_KLAXO = {
    "name": "KLAXO",
    "settings": [
        {
            "type": "text",
            "id": "klaxo_whatsapp",
            "label": "Numéro WhatsApp",
            "info": "Format international, ex. +212612345678.",
            "default": "",
        },
        {
            "type": "text",
            "id": "klaxo_whatsapp_message",
            "label": "Message pré-rempli WhatsApp",
            "default": "Salam ! J'ai une question sur ma commande.",
        },
        {"type": "header", "content": "Réseaux sociaux"},
        {"type": "url", "id": "social_instagram", "label": "Instagram"},
        {"type": "url", "id": "social_tiktok", "label": "TikTok"},
        {"type": "url", "id": "social_facebook", "label": "Facebook"},
    ],
}

# Blocs Dawn de la page produit incompatibles avec un parcours COD une-étape.
BLOCS_A_RETIRER = ("buy_buttons", "quantity_selector")


def _ecrire_json(chemin: Path, donnees) -> None:
    chemin.write_text(
        json.dumps(donnees, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def brancher_layout(racine: Path) -> None:
    chemin = racine / "layout" / "theme.liquid"
    contenu = chemin.read_text(encoding="utf-8")

    if MARQUEUR in contenu:
        print("  theme.liquid          déjà branché, ignoré")
        return

    for balise, ajout in (("</head>", TETE_LIQUID), ("</body>", PIED_LIQUID)):
        if balise not in contenu:
            raise SystemExit(f"ERREUR : {balise} introuvable dans layout/theme.liquid")
        contenu = contenu.replace(balise, ajout + balise, 1)

    chemin.write_text(contenu, encoding="utf-8")
    print("  theme.liquid          polices, marque, Worker, WhatsApp")


def brancher_groupe(racine: Path, fichier: str, sections: dict, ordre: list) -> None:
    """Remplace le contenu d'un groupe de sections (en-tête ou pied de page)."""
    chemin = racine / "sections" / fichier
    donnees = json.loads(chemin.read_text(encoding="utf-8"))
    # Le champ "type" identifie le groupe pour Shopify : il doit survivre.
    donnees["sections"] = sections
    donnees["order"] = ordre
    _ecrire_json(chemin, donnees)
    print(f"  {fichier:<21} {', '.join(ordre)}")


def brancher_produit(racine: Path) -> None:
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
        # Juste après le bloc produit : le client voit le produit, puis
        # immédiatement le choix de pack et le formulaire.
        position = ordre.index("main") + 1 if "main" in ordre else len(ordre)
        ordre.insert(position, "klaxo_offer")

    _ecrire_json(chemin, donnees)
    print(f"  product.json          offre COD ajoutée, retirés : {retires or 'aucun'}")


def brancher_reglages(racine: Path) -> None:
    chemin = racine / "config" / "settings_schema.json"
    groupes = json.loads(chemin.read_text(encoding="utf-8"))

    if any(g.get("name") == "KLAXO" for g in groupes):
        print("  settings_schema.json  déjà présent, ignoré")
        return

    groupes.append(REGLAGES_KLAXO)
    _ecrire_json(chemin, groupes)
    print("  settings_schema.json  WhatsApp + réseaux sociaux")


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage : wire_theme.py <racine-du-theme>")

    racine = Path(sys.argv[1])
    if not (racine / "layout" / "theme.liquid").exists():
        raise SystemExit(f"ERREUR : {racine} ne ressemble pas à un thème Shopify")

    brancher_layout(racine)
    brancher_groupe(
        racine,
        "header-group.json",
        {
            "klaxo_announcement": {
                "type": "klaxo-announcement",
                "blocks": {
                    "m1": {"type": "message", "settings": {"text": "<p>🚚 <strong>Livraison gratuite</strong> partout au Maroc</p>"}},
                    "m2": {"type": "message", "settings": {"text": "<p>💵 Paiement à la livraison</p>"}},
                    "m3": {"type": "message", "settings": {"text": "<p>↩️ Échange gratuit 7 jours</p>"}},
                },
                "block_order": ["m1", "m2", "m3"],
                "settings": {},
            },
            "klaxo_header": {"type": "klaxo-header", "settings": {}},
        },
        ["klaxo_announcement", "klaxo_header"],
    )
    brancher_groupe(
        racine,
        "footer-group.json",
        {
            "klaxo_footer": {
                "type": "klaxo-footer",
                "blocks": {
                    "c1": {"type": "menu", "settings": {"title": "Aide"}},
                    "c2": {"type": "menu", "settings": {"title": "Légal"}},
                },
                "block_order": ["c1", "c2"],
                "settings": {},
            }
        },
        ["klaxo_footer"],
    )
    brancher_produit(racine)
    brancher_reglages(racine)


if __name__ == "__main__":
    main()
