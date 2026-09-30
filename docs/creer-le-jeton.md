# Créer le jeton d'import · KLAXO.ma

À faire depuis `admin.shopify.com/store/6m1kid-eg`.

> **L'ancienne méthode n'existe plus.** Shopify a retiré l'onglet
> « API credentials » de `Paramètres → Applications → Développer des
> applications », celui où l'on révélait un jeton `shpat_` une seule fois.
> La page ne propose plus que **Build apps in Dev Dashboard**. Une app du Dev
> Dashboard ne donne pas de jeton : elle donne un **Client ID** et un
> **Client Secret**, qu'on échange ensuite contre un jeton.

---

## 0. Avant de commencer : en as-tu vraiment besoin ?

Tout ce que fait l'import se fait aussi à la main, en 20 à 25 minutes, sans
jeton et donc sans rien à faire fuiter :

| Objet | Sans API |
|---|---|
| Thème | `bash scripts/build-theme-zip.sh` puis `Boutique en ligne → Thèmes → Ajouter → Importer un fichier zip` |
| Produits | `Produits → Importer → data/klaxo-produits.csv` |
| Pages, collection, menus | à la main — `docs/pages-et-produits.md` détaille chaque écran |

Le jeton vaut le coup si tu comptes rejouer l'import plusieurs fois, ou le
refaire sur une autre boutique. Pour une installation unique, la voie manuelle
est plus courte que ce qui suit.

---

## 1. Créer l'app dans le Dev Dashboard

```
Paramètres → Apps → App development → Build apps in Dev Dashboard
→ Créer une app → nom : « KLAXO Import »
```

## 2. Cocher exactement ces droits

Dans la configuration Admin API de l'app :

| Droit | Sert à |
|---|---|
| `write_themes` | pousser le thème |
| `write_products` | créer les 3 produits et leurs variantes |
| `read_products` | vérifier avant de créer, pour ne rien dupliquer |
| `write_content` | créer les 4 pages |
| `read_content` | idem, contrôle anti-doublon |
| `write_online_store_navigation` | créer les 3 menus |

**Ne coche rien d'autre.** Surtout pas `write_orders`, `read_customers` ni
`write_customers` : l'import n'en a pas besoin, et un jeton qui ne peut pas lire
tes clients ne peut pas fuiter tes clients.

## 3. Installer l'app sur la boutique

L'app doit être **installée sur `6m1kid-eg`**, pas seulement créée. Sans
installation, l'échange de l'étape 5 renvoie une erreur 400 ou 401.

## 4. Récupérer Client ID et Client Secret

Ils sont dans la configuration de l'app. Le **secret** se traite comme un mot de
passe : il vaut le jeton, et il reste valable tant que l'app existe.

## 5. Échanger contre un jeton

```bash
export SHOPIFY_STORE=6m1kid-eg
export SHOPIFY_CLIENT_ID=...
export SHOPIFY_CLIENT_SECRET=...

export SHOPIFY_ADMIN_TOKEN="$(python3 scripts/get_token.py)"
```

Le script affiche à l'écran la durée de validité, les droits obtenus et le
préfixe du jeton — mais **pas le jeton**, qui va directement dans la variable.

`scripts/import-all.sh` fait cet échange tout seul : si `SHOPIFY_ADMIN_TOKEN`
est absent mais que `SHOPIFY_CLIENT_ID` et `SHOPIFY_CLIENT_SECRET` sont là, il
appelle `get_token.py` avant de commencer.

**Ce jeton peut expirer.** Contrairement aux anciens `shpat_` d'app
personnalisée, un jeton de client credentials porte souvent une durée de vie.
Le script te l'annonce. S'il expire en cours de route, relance la commande
ci-dessus : les identifiants d'app, eux, ne bougent pas.

### Pourquoi ça marche ici

Le client credentials grant ne fonctionne que sur les boutiques de **ta propre
organisation Shopify**. KLAXO en fait partie. La même méthode échouerait sur la
boutique d'un client — il faudrait alors un vrai flux OAuth.

---

## Ce que je fais de ces identifiants

- Je les lis **uniquement** depuis les variables d'environnement de ma session.
- Je ne les écris **dans aucun fichier**, et rien de ce que je commite ne les
  contient (`.gitignore` couvre déjà `.env` et `.dev.vars`).
- Je ne les affiche jamais en clair dans une sortie de commande.

## Ce que tu fais après l'import

**Supprime l'application.** Le jeton et le secret meurent avec elle.

C'est la seule façon d'être certain qu'ils ne servent plus à rien, quel que soit
l'endroit où ils ont transité — y compris cette conversation, qui est stockée.
Changer ton mot de passe Shopify ne révoque **pas** un jeton d'app : les deux
sont indépendants.

Tu peux recréer une app le jour où on en a besoin.

---

## Ce que le script va faire

Dans cet ordre, en s'arrêtant à la première erreur :

1. **Vérifier le jeton** — appelle `/shop.json`, affiche le nom de la boutique.
   Si ça échoue, rien d'autre ne part.
2. **Pousser le thème** — sur un thème **non publié**, jamais sur le thème en
   ligne. Tu previsualises, tu publies toi-même. Si la CLI Shopify refuse le
   jeton, le script te renvoie vers le zip et poursuit avec la suite.
3. **Créer les 3 produits** avec les variantes de packs.
4. **Créer la collection** « Nos produits » et y mettre les 3 produits.
5. **Créer les 4 pages** avec les bons handles et les bons gabarits.
6. **Créer les 3 menus** et leurs entrées.

Chaque étape vérifie d'abord si l'objet existe déjà (par son handle) : relancer
le script ne crée pas de doublons.

**Ce que le script ne fera pas :** publier le thème, lancer la boutique, ni
toucher aux commandes ou aux clients.

---

## Si ça bloque

| Symptôme | Cause probable |
|---|---|
| `HTTP 401` à l'échange | app pas installée sur `6m1kid-eg` |
| `HTTP 400` à l'échange | Client Secret erroné, ou boutique hors de ton organisation |
| `HTTP 403` pendant l'import | un droit de l'étape 2 n'est pas coché |
| La CLI refuse le jeton pour le thème | installe le thème par zip, le reste de l'import continue |

Les libellés exacts du Dev Dashboard bougent encore : si un écran ne
correspond pas à ce document, c'est le document qu'il faut corriger.
