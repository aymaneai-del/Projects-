# Créer le jeton d'import · KLAXO.ma

Trois minutes. À faire depuis `admin.shopify.com/store/6m1kid-eg`.

---

## 1. Créer l'app personnalisée

```
Paramètres → Applications et canaux de vente → Développer des applications
→ Autoriser le développement d'applications personnalisées   (une seule fois)
→ Créer une application → nom : « KLAXO Import »
```

## 2. Cocher exactement ces droits

`Configuration → Admin API integration → Configurer`

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

## 3. Installer et copier le jeton

```
Enregistrer → Installer l'application → Révéler le jeton une seule fois
```

Il commence par `shpat_`. **Shopify ne te le remontrera jamais** : copie-le tout
de suite.

---

## Ce que je fais de ce jeton

- Je le lis **uniquement** depuis une variable d'environnement de ma session.
- Je ne l'écris **dans aucun fichier**, et rien de ce que je commite ne le contient
  (`.gitignore` couvre déjà `.env` et `.dev.vars`).
- Je ne l'affiche jamais en clair dans une sortie de commande.

## Ce que tu fais après l'import

**Supprime l'application.** `Paramètres → Applications → KLAXO Import → Désinstaller`.

Le jeton devient mort. C'est la seule façon d'être certain qu'il ne sert plus à
rien, quel que soit l'endroit où il a transité — y compris cette conversation,
qui est stockée.

Tu peux en recréer un en trois minutes le jour où on en a besoin.

---

## Ce que le script va faire

Dans cet ordre, en s'arrêtant à la première erreur :

1. **Vérifier le jeton** — appelle `/shop.json`, affiche le nom de la boutique.
   Si ça échoue, rien d'autre ne part.
2. **Pousser le thème** — sur un thème **non publié**, jamais sur le thème en
   ligne. Tu previsualises, tu publies toi-même.
3. **Créer les 3 produits** avec les variantes de packs.
4. **Créer la collection** « Nos produits » et y mettre les 3 produits.
5. **Créer les 4 pages** avec les bons handles et les bons gabarits.
6. **Créer les 3 menus** et leurs entrées.

Chaque étape vérifie d'abord si l'objet existe déjà (par son handle) : relancer
le script ne crée pas de doublons.

**Ce que le script ne fera pas :** publier le thème, lancer la boutique, ni
toucher aux commandes ou aux clients.
