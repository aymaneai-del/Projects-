# Runbook — Phases 1 et 2 · KLAXO.ma

Ordre d'exécution du déploiement. Chaque étape est vérifiable ; ne pas passer à
la suivante sans le contrôle qui la termine.

---

## Avant tout

**Duplique le thème.** Garde-fou non négociable du projet : on ne modifie jamais
le thème publié en direct.

```
Boutique → Thèmes → Dawn → … → Dupliquer
Renommer la copie : "KLAXO — travail"
```

Tout ce qui suit se fait sur la copie. La publication vient à la fin, après QA.

---

## Phase 1 — Thème

### 1. Déposer les fichiers

| Fichier du repo | Destination Shopify |
|---|---|
| `theme/assets/klaxo-cod.css` | `assets/` |
| `theme/assets/klaxo-phone.js` | `assets/` |
| `theme/assets/klaxo-track.js` | `assets/` |
| `theme/assets/klaxo-offer.js` | `assets/` |
| `theme/sections/klaxo-offer.liquid` | `sections/` |
| `theme/snippets/klaxo-trust.liquid` | `snippets/` |
| `theme/snippets/klaxo-sticky-cta.liquid` | `snippets/` |

### 2. Déclarer l'URL du Worker

Dans `layout/theme.liquid`, avant `</head>` :

```liquid
<script>
  window.KLAXO_CONFIG = { workerUrl: "https://klaxo-tracking.<ton-sous-domaine>.workers.dev" };
</script>
```

Cette URL est publique par nature — ce n'est pas un secret. Les secrets restent
côté Cloudflare.

### 3. Ajouter la section

Éditeur de thème → page produit → Ajouter une section → **KLAXO — Offre COD**.
Renseigner les trois paliers, la ligne de livraison et le numéro WhatsApp.

### 4. Coller le formulaire de l'app

Le code d'intégration de l'app COD va dans le réglage **« Code d'intégration de
l'app COD »**. Ne jamais coller de clé ni de token dans ce champ : le thème est
servi publiquement.

### Contrôles de fin de Phase 1

- [ ] Les trois paliers s'affichent, **Duo présélectionné**
- [ ] Changer de palier met à jour le prix affiché **et** celui de la barre mobile
- [ ] La barre mobile disparaît quand le formulaire est à l'écran
- [ ] Le champ téléphone accepte `0612345678`, `+212612345678`, `06 12 34 56 78`
      et les réécrit en `+212612345678` au blur
- [ ] Aucun champ n'est refusé par notre code — seule l'app valide
- [ ] LCP < 2,5 s avec un bridage réseau **4G réel**, pas en simulation de bureau

---

## Phase 2 — Worker

### 1. Déployer

```bash
cd worker
npx wrangler deploy
```

### 2. Poser les secrets

Jamais dans `wrangler.toml`, qui est versionné :

```bash
npx wrangler secret put META_PIXEL_ID
npx wrangler secret put META_CAPI_TOKEN
npx wrangler secret put TIKTOK_PIXEL_CODE
npx wrangler secret put TIKTOK_ACCESS_TOKEN
npx wrangler secret put SHOPIFY_WEBHOOK_SECRET
npx wrangler secret put LIFECYCLE_TOKEN     # invente une chaîne longue et aléatoire
```

Contrôle — aucune valeur n'est renvoyée, seulement leur présence :

```bash
curl https://klaxo-tracking.<sous-domaine>.workers.dev/health
# {"ok":true,"configured":{"meta":true,"tiktok":true,"webhook":true,"lifecycle":true}}
```

### 3. Brancher le webhook Shopify

```
Paramètres → Notifications → Webhooks → Créer
Événement : Création de commande
Format    : JSON
URL       : https://klaxo-tracking.<sous-domaine>.workers.dev/webhooks/shopify/orders-create
```

Shopify affiche alors une **clé secrète** : c'est elle qui va dans
`SHOPIFY_WEBHOOK_SECRET`.

### 4. Recette avant production

Renseigner `META_TEST_EVENT_CODE` et `TIKTOK_TEST_EVENT_CODE`, passer une
commande réelle de bout en bout, vérifier dans le gestionnaire d'événements Meta
que le Purchase apparaît **une seule fois** (navigateur et serveur dédupliqués).

**Puis vider les deux codes de test.** Un événement portant un code de test
n'alimente pas l'optimisation des campagnes : l'oublier revient à diffuser à
l'aveugle.

### Contrôles de fin de Phase 2

- [ ] `/health` renvoie `true` partout
- [ ] Une commande réelle produit **un seul** Purchase côté Meta
- [ ] Le même Purchase apparaît côté TikTok
- [ ] Les `note_attributes` de la commande contiennent les UTM et `klaxo_fbc` / `klaxo_fbp`
- [ ] Un POST non signé sur le webhook renvoie **401**
- [ ] Un POST `Purchase` sur `/collect` renvoie **400**
- [ ] Les codes de test sont vidés

---

## Architecture de sécurité — pourquoi c'est fait ainsi

**`Purchase` ne vient jamais du navigateur.** `/collect` est une route publique :
elle est visible dans le code de la page, donc n'importe qui peut lui envoyer ce
qu'il veut. Si elle acceptait `Purchase`, un tiers pourrait injecter de fausses
conversions, ce qui empoisonnerait l'optimisation des campagnes et fausserait le
CPA — donc les décisions de kill.

`Purchase` provient donc exclusivement du webhook Shopify, dont la signature HMAC
prouve l'origine. `/collect` ne porte que `ViewContent` et `InitiateCheckout` :
sans valeur monétaire, sans conséquence s'ils sont bruités.

**Chaîne d'attribution :** le navigateur génère un `event_id` → `klaxo-track.js`
le dépose en champ caché → il devient une `note_attribute` de la commande → le
webhook le relit → Meta et TikTok dédupliquent. C'est ce qui relie une vente à la
créative qui l'a produite.

---

## Les trois événements métier

| Événement | Origine | Usage |
|---|---|---|
| `order_placed` | webhook Shopify → `Purchase` | **optimisation** des campagnes |
| `order_confirmed` | `POST /lifecycle` | mesure seulement |
| `order_delivered` | `POST /lifecycle` | mesure seulement — seul CA réel |

```bash
curl -X POST https://klaxo-tracking.<sous-domaine>.workers.dev/lifecycle \
  -H "X-Klaxo-Token: <LIFECYCLE_TOKEN>" \
  -H "content-type: application/json" \
  -d '{"event_name":"order_confirmed","order_id":"1234","phone":"+212612345678","value":349}'
```

**Meta optimise sur `Purchase`, jamais sur `order_confirmed`.** Meta demande de
l'ordre de 50 conversions par semaine et par ad set pour sortir de la phase
d'apprentissage ; au budget du projet, les confirmations ne l'atteindront pas.
Optimiser dessus bloquerait l'algorithme en apprentissage et ferait exploser le
coût par résultat.

Rebasculer uniquement au-delà de 50 confirmations/semaine/ad set.

**Et le ROAS affiché par Meta compte des commandes dont 30 à 45 % ne se
confirmeront jamais.** La source de vérité est le Sheet, jamais l'interface Meta.

---

## Tests

```bash
npm test    # 19 tests : normalisation téléphone, hachage, HMAC, routes
```

À relancer avant tout déploiement touchant le Worker ou la normalisation.

---

## Hors périmètre à ce stade

**La Phase 3 (ops) n'est pas construite** : le skill la conditionne à 20 commandes
livrées, il y en a 0. Elle couvrira le webhook → Google Sheet, le push vers l'API
courrier et le script KPI journalier.

Jusque-là, la confirmation et le suivi se font à la main. Le seuil des 15 min/jour
de la règle de discipline budgétaire n'est pas atteint : automatiser maintenant
serait du budget brûlé sur ce qui ne valide pas le produit.
