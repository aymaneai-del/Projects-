#!/usr/bin/env bash
#
# KLAXO — import complet sur la boutique Shopify.
#
#   1. Thème        (CLI Shopify, sur un thème NON PUBLIÉ)
#   2. Le reste     (produits, collection, pages, menus — Admin API)
#
# Le jeton vient de l'environnement, jamais d'un fichier du dépôt.
#
# Usage :
#   export SHOPIFY_STORE=6m1kid-eg
#   export SHOPIFY_ADMIN_TOKEN=shpat_...
#   bash scripts/import-all.sh              # import réel
#   bash scripts/import-all.sh --dry-run    # simulation, ne crée rien

set -euo pipefail

RACINE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DRY=""
[[ "${1:-}" == "--dry-run" ]] && DRY="--dry-run"

: "${SHOPIFY_STORE:?SHOPIFY_STORE manquant (ex. 6m1kid-eg)}"
: "${SHOPIFY_ADMIN_TOKEN:?SHOPIFY_ADMIN_TOKEN manquant}"

# Garde-fou : un jeton d'app personnalisée commence par shpat_.
# Un mot de passe Theme Access (shptka_) ne peut pas créer produits ni pages.
if [[ "$SHOPIFY_ADMIN_TOKEN" != shpat_* ]]; then
  echo "ATTENTION : le jeton ne commence pas par shpat_." >&2
  echo "Un mot de passe Theme Access (shptka_) ne couvre que le thème." >&2
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
  SHOPIFY_CLI_THEME_TOKEN="$SHOPIFY_ADMIN_TOKEN" \
    npx --yes @shopify/cli@latest theme push \
      --path "$TRAVAIL/theme" \
      --store "$SHOPIFY_STORE" \
      --unpublished \
      --theme "KLAXO $(date +%Y-%m-%d)" \
      --json
fi

echo
echo "════ 2. Produits, collection, pages, menus ════"
python3 "$RACINE/scripts/import_shopify.py" $DRY
