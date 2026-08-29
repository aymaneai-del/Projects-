# Pages, produits et menus · KLAXO.ma

Le thème contient les **gabarits**. Shopify garde les **pages**, les **produits**
et les **menus** dans l'admin. Un gabarit seul ne crée rien : il attend qu'une
page lui soit rattachée.

Compter 20 minutes pour tout brancher, dans cet ordre.

---

## 1. Les produits — un seul import

`data/klaxo-produits.csv` crée les trois fiches d'un coup, descriptions et SEO
compris.

```
Produits → Importer → choisir data/klaxo-produits.csv → Importer
```

| Produit | Prix du CSV | Poids | SKU |
|---|---|---|---|
| Organisateur entre-sièges | 199 DH | 320 g | KLX-ORG-01 |
| Support téléphone magnétique | 149 DH | 140 g | KLX-SUP-01 |
| Caméra de recul sans fil | 399 DH | 480 g | KLX-CAM-01 |

**Les prix et les poids sont des hypothèses de travail.** Remplace-les par tes
vrais chiffres dès que tu as les prix d'achat de Derb Omar et les tarifs
courrier pour chaque gabarit. Le poids sert au calcul du tarif de livraison :
un poids faux fausse la marge.

Le CSV n'embarque aucune image — Shopify ne peut importer que des images déjà
en ligne. Ajoute-les à la main après l'import, en WebP, une fois les produits
photographiés.

L'inventaire est réglé sur `continue` : une rupture n'empêche pas de commander.
Avec un réassort Derb Omar en 3-5 jours, bloquer la commande coûte plus cher
que de faire patienter un client.

### Après l'import

Crée une collection qui contient les trois produits — c'est elle que la page
« Nos produits » affiche :

```
Produits → Collections → Créer → nom « Nos produits »
→ Type : manuelle → ajouter les 3 produits
```

---

## 2. Les pages — créer, puis assigner le gabarit

Pour **chacune** des quatre pages : `Boutique en ligne → Pages → Ajouter`.

Laisse le contenu vide, tout le texte est dans le gabarit. Ce qui compte, ce
sont le titre, le **handle** et le **modèle**.

| Titre | Handle (exact) | Modèle à choisir |
|---|---|---|
| FAQ | `faq` | `page.faq` |
| Livraison & paiement | `livraison` | `page.livraison` |
| Retour & échange | `retour` | `page.retour` |
| Contact | `contact` | `page.contact` |

Le **handle** doit être exactement celui du tableau : les pages se lient entre
elles par ces adresses. Un handle `livraison-paiement` casse le lien depuis la FAQ.

> Le sélecteur de modèle est en bas à droite de l'éditeur de page, sous
> « Modèle de thème ». S'il n'affiche pas `page.faq`, c'est que le thème
> KLAXO n'est pas le thème publié — sélectionne-le d'abord.

---

## 3. Les menus — la garantie anti-lien mort

Le pied de page ne rend **que** les colonnes auxquelles un menu est réellement
rattaché. Une colonne sans menu disparaît au lieu d'afficher un titre vide.

```
Boutique en ligne → Navigation → Ajouter un menu
```

| Menu | Handle | Entrées |
|---|---|---|
| Aide | `aide` | Livraison & paiement · Retour & échange · FAQ · Contact |
| Légal | `legal` | CGV · Confidentialité · Mentions légales |
| Menu principal | `main-menu` | Accueil · Nos produits · Livraison · FAQ · Contact |

Puis dans l'éditeur de thème : section **KLAXO — Pied de page** → chaque colonne
→ choisir son menu. Et **KLAXO — En-tête** → Menu → `main-menu`.

Ne mets dans un menu que des pages qui existent. Le CGV, la confidentialité et
les mentions légales se génèrent depuis `Paramètres → Politiques`.

---

## 4. Réglages du thème

`Éditeur de thème → Paramètres → KLAXO`

- **Numéro WhatsApp** — format international, ex. `+212612345678`. Il alimente
  le bouton flottant, le pied de page, le bloc confiance et la page Contact.
  Écrit une seule fois, utilisé partout.
- **Message pré-rempli WhatsApp**
- **Instagram / TikTok / Facebook** — une icône n'apparaît que si son lien est renseigné.

---

## Ce que j'ai retiré de l'inspiration, et pourquoi

Trois éléments ne pouvaient pas partir en ligne tels quels.

### Les taux de livraison des transporteurs

L'inspiration présentait quatre transporteurs comme « nos partenaires
logistiques », avec des taux de livraison chiffrés (88 %, 85 %).

Deux problèmes distincts : **aucun contrat courrier n'est signé**, donc ce ne
sont pas tes partenaires ; et ces pourcentages sont des **statistiques inventées
attribuées à des entreprises réelles**. Publier ça t'expose, et le premier client
qui compare le délai annoncé au délai réel ne revient pas.

La page Livraison ne nomme donc aucun transporteur. Tu pourras en ajouter un
quand tu auras signé — avec les délais de ton contrat, pas des chiffres inventés.

### La garantie 12 mois

« Garantie 12 mois sur tous les produits » est un engagement que tu ne peux pas
tenir sur du sourcing Derb Omar sans garantie fournisseur. Un client qui revient
au dixième mois avec une caméra en panne aura raison, et tu payeras.

Remplacé par ce qui est vrai et déjà solide : **retour 7 jours**, et prise en
charge complète d'un produit défectueux à l'arrivée. Si un fournisseur te donne
une vraie garantie écrite, ajoute-la à ce moment-là.

### Les délais de réponse chiffrés

« Réponse en moins d'1h », « rappel dans les 2h », « 45 minutes en moyenne »,
« 7j/7 de 9h à 20h ». Tu es seul. Une promesse de délai non tenue produit
exactement le client qui refuse le colis.

Les textes disent maintenant « on te répond au plus vite ». Tous sont modifiables :
le jour où tu as un call center, mets les vrais chiffres.

---

## Deux réserves sur la gamme

### La caméra de recul reprend le risque de l'aspirateur

Sortir l'aspirateur était la bonne décision. La caméra de recul rouvre
malheureusement le même dossier, en pire sur un point :

- **coût d'achat élevé** — elle pèse sur la marge comme l'aspirateur ;
- **produit électronique** — taux de refus supérieur au reste de la gamme ;
- **elle demande une installation.** L'aspirateur, on l'allume. Une caméra, il
  faut la fixer, l'alimenter et l'appairer. Chaque étape est une occasion de
  « ça ne marche pas » — donc un retour, sur le produit le plus cher de la gamme.

Ce n'est pas un veto : c'est le produit à la plus forte valeur perçue, donc le
meilleur pour monter le panier. Mais **teste-le sur quelques unités avant
d'engager du stock**, et surveille son taux de refus séparément. S'il dépasse
celui de l'organisateur de plus de 10 points, sors-le.

Une notice d'installation claire dans le colis, en darija et en français, est
le meilleur investissement anti-retour sur ce produit.

### Les prix ne sont pas validés

199 / 149 / 399 DH sont des points de départ cohérents entre eux, pas des prix
calculés. Rappel du modèle : le héros vendu seul est en marge négative sous
~320 DH de panier une fois le coût pub par livrée pris en compte.

Passe les trois produits dans le calculateur du kit de lancement dès que tu as
les prix d'achat réels.

---

## Contrôle final avant publication

- [ ] 3 produits importés, images ajoutées
- [ ] Collection « Nos produits » créée avec les 3 produits
- [ ] 4 pages créées, handles exacts, modèles assignés
- [ ] 3 menus créés et rattachés aux sections
- [ ] Numéro WhatsApp renseigné dans les réglages
- [ ] Un clic sur chaque lien du pied de page — aucun 404
- [ ] Formulaire de contact testé : le message arrive bien dans la boîte mail
- [ ] `<sous-domaine>` remplacé dans `layout/theme.liquid`
- [ ] Code de l'app COD collé dans la section Offre
