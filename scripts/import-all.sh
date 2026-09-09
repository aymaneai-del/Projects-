#!/usr/bin/env bash
#
# KLAXO — import complet sur la boutique Shopify.
#
#   1. Thème        (CLI Shopify, sur un thème NON PUBLIÉ)
#   2. Le reste     (produits, collection, pages, menus — Admin API)
#
# Le jeton vient de l'environnement, jamais d'un fichier du dépôt.
#
# Deux façons de le fournir :
#
#   a) tu as déjà un jeton
#      export SHOPIFY_STORE=6m1kid-eg
#      export SHOPIFY_ADMIN_TOKEN=shpat_...
#
#   b) tu as une app du Dev Dashboard (Client ID + Client Secret) — le script
#      fait l'échange lui-même
#      export SHOPIFY_STORE=6m1kid-eg
#      export SHOPIFY_CLIENT_ID=...
#      export SHOPIFY_CLIENT_SECRET=...
#
# Usage :
#   bash scripts/import-all.sh              # import réel
#   bash scripts/import-all.sh --dry-run    # simulation, ne crée rien

set -euo pipefail

RACINE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DRY=""
[[ "${1:-}" == "--dry-run" ]] && DRY="--dry-run"

: "${SHOPIFY_STORE:?SHOPIFY_STORE manquant (ex. 6m1kid-eg)}"

# Pas de jeton mais des identifiants d'app : on l'obtient par le client
# credentials grant. get_token.py n'écrit le jeton nulle part — il le rend
# sur sa sortie standard et rien d'autre.
if [[ -z "${SHOPIFY_ADMIN_TOKEN:-}" && -n "${SHOPIFY_CLIENT_ID:-}" ]]; then
  echo "════ 0. Échange Client ID/Secret contre un jeton ════"
  SHOPIFY_ADMIN_TOKEN="$(python3 "$RACINE/scripts/get_token.py")"
  export SHOPIFY_ADMIN_TOKEN
  echo
fi

: "${SHOPIFY_ADMIN_TOKEN:?SHOPIFY_ADMIN_TOKEN manquant (ou SHOPIFY_CLIENT_ID + SHOPIFY_CLIENT_SECRET)}"

# Garde-fou : un mot de passe Theme Access ne couvre que le thème, il échouera
# à créer produits et pages. Les autres préfixes (shpat_, shpca_, shpua_…)
# viennent tous d'une app installée et conviennent.
if [[ "$SHOPIFY_ADMIN_TOKEN" == shptka_* ]]; then
  echo "ATTENTION : jeton Theme Access (shptka_)." >&2
  echo "Il pousse le thème mais ne peut créer ni produits, ni pages, ni menus." >&2
fi

echo "════ 1. Thème ════"
if [[ -n "$DRY" ]]; then
  echo "  [essai] pousserait le thème sur un emplacement non publié"
else
  # Le thème complet est reconstruit à partir des sources, jamais depuis dist/
  # qui pourrait être périmé.
  bash "$RACINE/scripts/build-theme-zip.sh" >/dev/null
  TRAVAIL="$(mktemp -d)"
  trap 'rm -rf "$TRAVAIL"' EXIT
  unzip -q "$RACINE/dist/klaxo-theme-complet.zip" -d "$TRAVAIL/theme"

  # --unpublished : crée un NOUVEAU thème non publié. La boutique en ligne
  # n'est jamais modifiée ; la publication reste une décision manuelle.
  #
  # La CLI n'accepte pas tous les types de jetons. Si elle refuse celui-ci,
  # ce n'est pas bloquant : le zip est déjà construit et s'installe à la main.
  # On continue donc vers l'étape 2 au lieu de tout arrêter.
  if SHOPIFY_CLI_THEME_TOKEN="$SHOPIFY_ADMIN_TOKEN" \
    npx --yes @shopify/cli@latest theme push \
      --path "$TRAVAIL/theme" \
      --store "$SHOPIFY_STORE" \
      --unpublished \
      --theme "KLAXO $(date +%Y-%m-%d)" \
      --json
  then
    :
  else
    echo >&2
    echo "La CLI n'a pas pu pousser le thème avec ce jeton." >&2
    echo "Replis : dist/klaxo-theme-complet.zip est prêt." >&2
    echo "  Boutique en ligne → Thèmes → Ajouter → Importer un fichier zip" >&2
    echo "On poursuit avec les produits, pages et menus." >&2
    echo >&2
  fi
fi

echo
echo "════ 2. Produits, collection, pages, menus ════"
python3 "$RACINE/scripts/import_shopify.py" $DRY
