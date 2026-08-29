#!/usr/bin/env bash
#
# KLAXO — fabrique les deux livrables de thème.
#
#   dist/klaxo-theme-complet.zip   Dawn 16 + KLAXO, installable tel quel dans Shopify
#   dist/klaxo-fichiers-seuls.zip  uniquement les fichiers KLAXO, à déposer dans
#                                  un thème existant déjà personnalisé
#
# Reproductible : relancer le script régénère les deux zips à l'identique
# depuis theme/. Ne jamais éditer un zip à la main.
#
# Usage :  bash scripts/build-theme-zip.sh

set -euo pipefail

RACINE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TRAVAIL="$(mktemp -d)"
DIST="$RACINE/dist"
DAWN_REF="${DAWN_REF:-main}"

trap 'rm -rf "$TRAVAIL"' EXIT

mkdir -p "$DIST"
rm -f "$DIST/klaxo-theme-complet.zip" "$DIST/klaxo-fichiers-seuls.zip"

echo "→ Récupération de Dawn ($DAWN_REF)"
git clone --depth 1 --branch "$DAWN_REF" --quiet \
  https://github.com/Shopify/dawn.git "$TRAVAIL/dawn"
rm -rf "$TRAVAIL/dawn/.git" "$TRAVAIL/dawn/.github"

VERSION_DAWN="$(python3 -c "
import json
with open('$TRAVAIL/dawn/config/settings_schema.json', encoding='utf-8') as f:
    print(next(g.get('theme_version','?') for g in json.load(f) if 'theme_version' in g))
")"
echo "  Dawn $VERSION_DAWN"

echo "→ Copie des fichiers KLAXO"
for dossier in assets sections snippets; do
  cp "$RACINE/theme/$dossier"/* "$TRAVAIL/dawn/$dossier/"
done

echo "→ Branchement dans le thème"
python3 "$RACINE/scripts/wire_theme.py" "$TRAVAIL/dawn"

echo "→ Zip 1/2 : thème complet"
# -x : ne jamais embarquer d'artefacts macOS, Shopify les refuse.
( cd "$TRAVAIL/dawn" && zip -qr "$DIST/klaxo-theme-complet.zip" . -x '.*' '__MACOSX/*' '*/.DS_Store' )

echo "→ Zip 2/2 : fichiers KLAXO seuls"
mkdir -p "$TRAVAIL/seuls"
cp -r "$RACINE/theme/." "$TRAVAIL/seuls/"
cp "$RACINE/docs/runbook-phase-1-2.md" "$TRAVAIL/seuls/INSTALLATION.md"
( cd "$TRAVAIL/seuls" && zip -qr "$DIST/klaxo-fichiers-seuls.zip" . -x '.*' '__MACOSX/*' '*/.DS_Store' )

echo
echo "Fait :"
ls -lh "$DIST" | tail -n +2 | awk '{printf "  %-32s %s\n", $9, $5}'
