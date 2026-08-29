---
name: cod-store-build
description: Use this skill to build, instrument and validate a Moroccan COD e-commerce store (Shopify) on a 10 000 DH budget, extensible to 15 000 DH. Covers store setup, server-side tracking (Meta CAPI + TikTok Events API), courier integration, and the GO/NO-GO decision loop. Do not use for brand naming, creative writing, or ad copy.
origin: ECC
---

# COD Store Build — Accessoires auto, Maroc

## Contexte projet (ne jamais redemander)

| Élément | Valeur |
|---|---|
| Niche | Accessoires & gadgets automobiles |
| Marché | Maroc, Casablanca en priorité, livraison nationale |
| Modèle | COD dominant + carte bancaire marocaine en option |
| Sourcing | Derb Omar, Casablanca — stock physique, réappro 3-5 jours |
| Plateforme | Shopify (à contester si friction paiement/courrier trop forte) |
| Budget total | **10 000 DH**, extension max **15 000 DH** |
| Trafic | Meta Ads + TikTok Ads |
| Compte Meta | Business Manager **ancien, AUCUN pixel existant** — signal publicitaire à zéro |
| Langue store | Français primaire, darija dans les créatives, AR optionnel |
| Panier moyen cible | 300-500 DH |

Le budget de référence pour **tout** calcul de ratio (part du budget consommée, seuil de kill,
sortie du script KPI) est **10 000 DH**. Les 5 000 DH d'extension sont une réserve, pas une
ligne de dépense planifiable : ne jamais construire un plan qui n'est viable qu'en les
consommant.

**Contrainte structurante :** Shopify Payments n'existe pas au Maroc. Le paiement carte passe
obligatoirement par une passerelle tierce (CMI via banque, PayZone, Chari Pay), ce qui déclenche
en plus les frais de transaction Shopify (2 % sur le plan Basic). Le COD via méthode de paiement
manuelle n'est pas soumis à ces 2 %. **Conclusion : lancer 100 % COD, ajouter la carte seulement
une fois le contrat passerelle signé.** Ne pas bloquer le lancement sur ce point.

## Règle #1 — Discipline budgétaire

Le budget total ≈ le budget pub d'un seul test de produit chez un concurrent établi.
Chaque heure de dev qui ne sert pas à valider le produit #1 est du budget brûlé.

**Interdit tant que le produit #1 n'a pas atteint 20 commandes livrées :**
- App payante > 10 $/mois — **une seule exception : l'app de formulaire COD** (voir décision d'architecture)
- Thème premium
- Multi-langue, multi-devise, wishlist, programme de fidélité, blog, compte client
- Plus de 3 produits publiés
- Toute automatisation qui remplace une tâche prenant moins de 15 min/jour à la main

## Phase 0 — Blocages à lever avant tout code

À vérifier et signaler à l'utilisateur avant d'écrire une ligne :

```
1. Statut légal actif ? (auto-entrepreneur / société — requis pour contrat courrier + CMI)
2. Contrat courrier COD signé ? (Ozonexpress, Sendit, Cathedis, Speedaf)
   → tarif livraison, tarif retour, délai de versement (J+7 à J+15)
   → ACCÈS API inclus dans le contrat ? Certains courriers ne l'ouvrent qu'au-dessus
     d'un volume mensuel. Vérifier AVANT de planifier la Phase 3, pas pendant.
3. Produit #1 choisi + prix d'achat Derb Omar confirmé + 5 échantillons testés
   → poids et dimensions du colis relevés, tarif courrier confirmé POUR CE GABARIT
   → housses de siège, tapis de coffre, kits volumineux sortent du colis standard :
     si le surcoût dépasse 15 DH, recalculer la marge avant de commander du stock
4. Nom de marque validé (.ma + .com + @IG + @TikTok libres)
5. Compte Meta Business accessible + pixel : EXISTANT ou À CRÉER ?
   → un pixel neuf = zéro historique. Voir « Démarrage à froid » ci-dessous.
6. HÉBERGEMENT du backend tracking choisi — voir « Infrastructure serveur ».
   Sans hôte défini, les Phases 2 et 3 ne sont pas implémentables.
7. DÉCISION D'ARCHITECTURE du formulaire COD — voir section dédiée. À trancher avec
   l'utilisateur avant la Phase 1. C'est la décision la plus structurante du projet.
```

Si un point manque, dire lequel et s'arrêter. Ne pas construire par-dessus une hypothèse.

### Ce qui est réellement bloquant, et ce qui ne l'est pas

Tous les points de la Phase 0 ne bloquent pas la même chose. Ne pas geler le projet entier
pour un point qui ne bloque qu'une phase :

| Point manquant | Bloque | Ne bloque PAS |
|---|---|---|
| Statut légal | contrat courrier, CMI, versement des encaissements | maquettage de la page produit |
| Contrat courrier | tout lancement réel (livraison + tarif de marge) | dev du thème |
| Produit #1 | contenu, prix, marge, commande de stock | squelette du template COD |
| Nom de marque | domaine, comptes sociaux, mise en ligne | dev en local sur le store de test |
| Pixel Meta | Phase 2 | Phase 1 |
| Hébergement | Phases 2 et 3 | Phase 1 |
| Décision formulaire | **la Phase 1 entière** | rien — la trancher en premier |

**Ordre de déblocage recommandé :** statut légal → contrat courrier (avec tarifs et gabarit) →
produit #1 → décision formulaire → marque → pixel + hébergement.

Le statut légal est en tête parce qu'il est le prérequis du contrat courrier, qui est lui-même
le prérequis du calcul de marge — donc du choix du produit. Sans tarif courrier confirmé pour
le gabarit réel, toute marge calculée est une supposition, et le seuil de kill ne veut rien dire.

### Démarrage à froid — pixel neuf

Si le compte Meta n'a **pas** de pixel avec historique, la mention « compte warm » ne
s'applique pas et les hypothèses de coût changent :

```
- Aucune audience de retargeting, aucun lookalike au départ. Prospection froide uniquement.
- Le pixel doit accumuler des conversions avant que la diffusion se stabilise :
  prévoir un CPA plus élevé sur les premiers jours et NE PAS killer un produit
  sur les 48 premières heures. Le seuil de kill reste 1 500 DH dépensés, pas 3 jours.
- Vérifier le domaine dans le Business Manager AVANT la première diffusion
  (obligatoire pour l'attribution, et impossible à rattraper proprement après).
- Un compte ancien sans historique de dépense n'est pas un compte de confiance :
  monter le budget progressivement. Un premier jour à 500 DH sur un compte dormant
  est un motif classique de restriction. Commencer bas, augmenter par paliers.
- Une restriction de compte pendant le test = budget bloqué et projet à l'arrêt.
  C'est le risque non-technique le plus coûteux du projet.
```

## Infrastructure serveur

Les Phases 2 et 3 exigent du code côté serveur : envoi CAPI/Events API, réception du webhook
`orders/create`, push vers l'API courrier. Le thème Shopify ne peut pas héberger ça — il est
public, et y mettre un token revient à le publier.

**À trancher en Phase 0, pas en Phase 2.** Contrainte : coût 0 DH/mois au démarrage, sinon
la ligne rentre dans le budget et doit être justifiée.

| Option | Coût | Convient si |
|---|---|---|
| Cloudflare Workers | 0 DH (offre gratuite) | défaut recommandé — latence faible, secrets natifs |
| Vercel / Netlify Functions | 0 DH (offre gratuite) | déjà familier avec l'un des deux |
| Google Apps Script | 0 DH | uniquement le webhook → Sheet, pas le CAPI |
| VPS | ~50-100 DH/mois | à éviter à ce budget : coût récurrent + maintenance |

Règles, quelle que soit l'option :

```
1. Les secrets vivent dans le gestionnaire de secrets de la plateforme, jamais dans le repo.
2. Un endpoint = une responsabilité. Ne pas empiler CAPI, webhook et courrier dans un fichier.
3. Le webhook Shopify doit vérifier la signature HMAC. Un endpoint ouvert reçoit du faux trafic.
4. Toute erreur d'envoi est journalisée avec l'order_id. Un événement perdu en silence,
   c'est un CPA faux, donc une décision de kill fausse.
```

## Décision d'architecture — formulaire COD

Un formulaire de commande sur la page produit **contourne le checkout Shopify**. Trois voies,
à trancher explicitement, jamais à deviner :

| | App COD éprouvée | Formulaire custom | Checkout Shopify natif |
|---|---|---|---|
| Coût | ~10-20 $/mois | 0 $/mois, mais du temps de dev | 0 $/mois |
| Délai | 1 heure | 2-5 jours + debug | 30 min |
| Création de commande | gérée par l'app | via App Proxy ou Storefront API | native |
| Risque | faible | commandes perdues si l'API échoue silencieusement | friction du parcours multi-étapes |
| Maintenance | l'éditeur | toi | Shopify |

**Le calcul, pas l'intuition.** Avec une marge nette cible de 100 DH par commande livrée et une
app à ~150 DH/mois :

```
Seuil de rentabilité de l'app = 150 / 100 = 1,5 commande livrée supplémentaire par mois.
```

Si le formulaire une-étape sur la page produit apporte plus d'une commande livrée par mois
qu'un checkout multi-étapes, l'app est rentable. Sur du trafic payant mobile marocain, c'est
un seuil bas.

Le coût d'une commande perdue par un formulaire maison qui échoue en silence :

```
marge perdue (100 DH) + CPA confirmé déjà payé (~80 DH) = ~180 DH par commande perdue.
5 commandes perdues ≈ 900 DH ≈ 6 mois d'abonnement app.
```

Et une commande perdue en silence ne se voit pas dans le Sheet : elle dégrade le CPA mesuré
sans laisser de trace, ce qui peut déclencher un kill sur un produit qui marchait.

**Défaut recommandé à ce budget : l'app.** Ne partir en custom que si l'utilisateur le demande
explicitement en connaissant ce compromis.

Si custom malgré tout : passer par un App Proxy avec création de Draft Order côté serveur,
jamais par un appel API depuis le navigateur — le token serait exposé dans le code de la page.
Et instrumenter l'échec : tout POST qui n'aboutit pas doit être journalisé et alerter, sinon
le risque ci-dessus est invisible.

## Garde-fous techniques (non négociables)

```
1. Dupliquer le thème avant TOUTE modification. Travailler sur la copie, publier après QA.
   Ne jamais éditer le thème publié en direct.
2. Aucun secret dans le thème ni dans le repo : token CAPI Meta, token TikTok Events API,
   clé API courrier, credentials Google Sheets.
   → variables d'environnement côté serveur uniquement.
   → un token collé dans un fichier .liquid est public et permet d'écrire dans le compte pub.
3. Ajouter .env, credentials.json et tout export de commandes au .gitignore.
   Les commandes contiennent des noms, téléphones et adresses de clients.
4. Toute modification touchant le formulaire de commande est testée par une commande
   réelle de bout en bout avant mise en ligne.
```

## Phase 1 — Store minimum viable

Objectif : une page produit qui convertit en COD. Rien d'autre.

```
1. Thème gratuit (Dawn) — pas de thème payant
2. Page produit unique optimisée COD :
   - Formulaire de commande directement sur la page (nom, tél, ville, adresse)
   - Pas de compte client, pas de panier multi-étapes
   - Champ téléphone : accepter 06XXXXXXXX, 07XXXXXXXX, 05XXXXXXXX, +212XXXXXXXXX
     et 212XXXXXXXXX, puis NORMALISER en un seul format avant enregistrement.
     Ne pas rejeter une saisie valide sur un problème de préfixe : chaque rejet
     de formulaire est une commande perdue et un CPA gaspillé.
   - Prix affiché TTC, livraison affichée AVANT le formulaire
3. Bloc confiance au-dessus du formulaire : paiement à la livraison, retour 7 jours,
   numéro WhatsApp cliquable
4. Sticky "Commander" mobile — 85 %+ du trafic sera mobile
5. Vitesse : LCP < 2,5 s sur 4G marocaine. Compresser toutes les images en WebP,
   supprimer tout script non essentiel. Vérifier avec un throttling réseau réel.
6. Version RTL de la page produit uniquement si l'utilisateur le demande explicitement
```

Livrer les modifications en Liquid + CSS dans le thème. Exception assumée : le formulaire
de commande COD, où une app éprouvée est le choix par défaut (voir décision d'architecture).
Aucune autre app sans validation explicite de l'utilisateur.

**Ce qui est faisable sans produit #1 confirmé :** la structure du template (sections, bloc
confiance, sticky mobile, normalisation du téléphone, budget de performance). Tout ce qui
touche au prix, à la marge, aux visuels ou au texte de vente attend le produit réel. Ne pas
remplir de faux prix « provisoires » : ils survivent jusqu'à la mise en ligne.

## Phase 2 — Tracking server-side

C'est ici que le travail de dev a le meilleur retour. Un CPA mal mesuré fait perdre
plus d'argent que n'importe quel bug de layout.

```
1. Pixel Meta + Conversions API (CAPI) avec déduplication par event_id
   - Events : ViewContent, InitiateCheckout, Purchase
   - Hasher email/téléphone en SHA-256 avant envoi
2. TikTok Pixel + Events API, même logique de déduplication
3. Distinguer trois événements métier distincts, jamais confondus :
   - order_placed      (commande passée sur le site)      → mappé sur Purchase
   - order_confirmed   (confirmée par téléphone)          → événement personnalisé
   - order_delivered   (payée à la livraison = seul CA réel) → événement personnalisé
4. UTM + identifiant de créative persistés dans la commande Shopify (note attributes)
```

**Règle d'optimisation — lire avant de coder :**

Optimiser les campagnes Meta sur `order_confirmed` est la bonne pratique en théorie et
**inapplicable à ce budget**. Meta exige de l'ordre de 50 conversions par semaine et par
ad set pour sortir de la phase d'apprentissage. Avec ~7 000 DH de pub au total, le volume
de commandes confirmées ne l'atteindra jamais : l'algorithme resterait bloqué en
apprentissage et le coût par résultat exploserait.

```
Règle applicable :
  - Meta optimise sur Purchase (= order_placed). C'est le seul événement avec assez de volume.
  - order_confirmed et order_delivered sont envoyés mais servent à la MESURE, pas à
    l'optimisation. Ils vivent dans le Sheet.
  - Le tri des créatives se fait à la main sur le CPA CONFIRMÉ, pas sur ce
    qu'affiche le gestionnaire de publicités.
  - Rebascule l'optimisation sur order_confirmed uniquement si le volume dépasse
    50 confirmations/semaine par ad set. Signaler à l'utilisateur quand ce seuil est franchi.
```

**Le piège réel :** croire le ROAS affiché par Meta. Il compte des commandes dont 30 à 45 %
ne se confirmeront jamais. Le tableau de bord Meta surévalue systématiquement la
performance en COD marocain — la source de vérité est le Sheet, jamais l'interface Meta.

## Phase 3 — Ops (seulement après 20 commandes livrées)

```
1. Webhook Shopify orders/create → Google Sheet (feuille de confirmation call center)
   → vérifier la signature HMAC du webhook avant tout traitement
2. Push des commandes confirmées vers l'API du courrier (Ozonexpress / Sendit)
   → dépend de l'accès API confirmé en Phase 0 point 2. Si le courrier n'ouvre pas
     l'API à ce volume, rester en export CSV manuel : 15 min/jour, coût de dev nul.
3. Import quotidien des statuts de livraison → mise à jour du Sheet
4. Script KPI journalier (voir métriques ci-dessous), sortie en une seule ligne par produit
```

## Métriques — seuils de décision

| Métrique | Seuil viable | Seuil kill |
|---|---|---|
| Taux de confirmation | > 60 % | < 45 % |
| Taux de livraison (sur confirmées) | > 65 % | < 50 % |
| CPA confirmé | < 80 DH | > 120 DH |
| Coût par commande livrée | < 120 DH | > 180 DH |
| Marge nette / commande livrée | > 100 DH | < 50 DH |

**Règle de kill :** après 1 500 DH dépensés sur un produit, si le CPA confirmé dépasse
120 DH, couper. Ne pas "laisser tourner encore un peu". Avec ce budget, deux produits
morts consommés jusqu'au bout = fin du projet.

Le seuil est en **dirhams dépensés**, jamais en jours écoulés. Avec un pixel neuf, les
premiers jours sont mécaniquement mauvais : couper sur une durée revient à tuer un produit
avant que la diffusion se stabilise.

**Formule marge nette réelle (à coder telle quelle, pas d'approximation) :**
```
marge_nette = (prix_vente - cout_achat - frais_livraison - frais_call_center)
            - (nb_refusees / nb_livrees) * frais_retour
            - cout_pub_par_livree
```

## Output Format

```markdown
## Build Report — [phase] — [date]

### Fait
- [✓] ...

### Bloqué
- [✗] ... — raison, et ce qu'il faut de l'utilisateur

### Budget consommé
- Abonnements : X DH/mois | Apps : X DH/mois | Cumul setup : X DH
- Part du budget de référence (10 000 DH) : X %

### Prochaine action unique
- ...
```

## Ce que ce skill ne fait pas

- Brainstorming de nom, identité visuelle, copywriting d'annonces → hors périmètre
- Scraping de sites concurrents
- Conseil juridique ou fiscal : le skill signale qu'un statut légal est requis et pourquoi,
  il ne choisit pas la forme juridique et ne se prononce pas sur la fiscalité
- Toute promesse de chiffre d'affaires : ce skill construit et mesure, il ne prédit pas

Pair with `/browser-qa` avant chaque mise en ligne de la page produit.
