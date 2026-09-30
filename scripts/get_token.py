#!/usr/bin/env python3
"""
KLAXO — échange Client ID / Client Secret contre un jeton Admin API.

Shopify a retiré l'onglet « API credentials » où l'on copiait un jeton
`shpat_` à la main. Une app créée dans le Dev Dashboard ne donne plus qu'un
Client ID et un Client Secret : le jeton s'obtient en les échangeant via le
client credentials grant.

Ce grant ne fonctionne que sur les boutiques de TA propre organisation
Shopify — ce qui est le cas de KLAXO. Il ne marcherait pas sur la boutique
d'un client.

Le jeton part sur la sortie standard, SEUL, pour pouvoir être capturé :

    export SHOPIFY_ADMIN_TOKEN="$(python3 scripts/get_token.py)"

Tout le reste (diagnostic, durée de validité, droits) part sur l'erreur
standard, donc rien de sensible ne se retrouve dans une variable par accident.
Le jeton n'est écrit dans aucun fichier.
"""

import json
import os
import sys
import urllib.error
import urllib.request


def echec(msg):
    print(f"\033[31m✗\033[0m {msg}", file=sys.stderr)


def info(msg):
    print(f"  {msg}", file=sys.stderr)


def main():
    boutique = os.environ.get("SHOPIFY_STORE")
    client_id = os.environ.get("SHOPIFY_CLIENT_ID")
    client_secret = os.environ.get("SHOPIFY_CLIENT_SECRET")

    manquants = [nom for nom, val in (
        ("SHOPIFY_STORE", boutique),
        ("SHOPIFY_CLIENT_ID", client_id),
        ("SHOPIFY_CLIENT_SECRET", client_secret),
    ) if not val]

    if manquants:
        echec(f"variables manquantes : {', '.join(manquants)}")
        info("Elles viennent du Dev Dashboard, onglet « Client credentials ».")
        info("Ne les mets pas dans un fichier du dépôt.")
        sys.exit(2)

    url = f"https://{boutique}.myshopify.com/admin/oauth/access_token"
    corps = json.dumps({
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "client_credentials",
    }).encode()

    req = urllib.request.Request(url, data=corps, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json")

    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            reponse = json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        texte = e.read().decode(errors="replace")
        echec(f"HTTP {e.code} sur /admin/oauth/access_token")
        # Le corps d'erreur de Shopify ne contient pas le secret envoyé.
        info(texte[:400])
        if e.code in (400, 401):
            info("Causes fréquentes : app pas installée sur la boutique,")
            info("secret erroné, ou boutique hors de ton organisation.")
        sys.exit(1)
    except urllib.error.URLError as e:
        echec(f"réseau : {e}")
        sys.exit(1)

    jeton = reponse.get("access_token")
    if not jeton:
        echec("réponse sans access_token")
        info(json.dumps(reponse)[:400])
        sys.exit(1)

    # Diagnostic sur stderr : visible à l'écran, absent de la variable.
    if "expires_in" in reponse:
        heures = reponse["expires_in"] / 3600
        info(f"jeton valide {heures:.0f} h — à régénérer après ce délai")
    else:
        info("jeton sans date d'expiration annoncée")
    if reponse.get("scope"):
        info(f"droits : {reponse['scope']}")
    info(f"préfixe : {jeton.split('_')[0]}_…")

    print(jeton)


if __name__ == "__main__":
    main()
