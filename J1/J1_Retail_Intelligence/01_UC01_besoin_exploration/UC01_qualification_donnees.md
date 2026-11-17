# UC-01 – Qualification des données

<p class="meta">Retail Intelligence Platform · TP Jour 1 · 16/11/2026</p>

Les contrôles sont faits par un script Python (`scripts/profile_sources.py`). Les résultats bruts sont dans `preuves/` et dans `UC01_inventaire_sources.xlsx`.

## 1. Inventaire (lot principal `data/`)

| Fichier | Domaine | Taille | Lignes | Col. | 1 ligne = |
|---|---|---|---|---|---|
| store_sales | Ventes magasin | 88,5 Mo | 667 579 | 23 | 1 article d'un ticket |
| web_sales | Ventes web | 127,6 Mo | 668 052 | 34 | 1 article d'une commande |
| store_returns / web_returns | Retours | 4,1 / 5,1 Mo | 37 902 / 38 487 | 20 / 24 | 1 article retourné |
| inventory | Stocks | 405,3 Mo | 23 255 100 | 4 | article × entrepôt × semaine |
| web_clickstreams | Navigation | 170,4 Mo | 6 770 550 | 6 | 1 clic |
| item | Produits | 6,5 Mo | 17 820 | 22 | 1 article |
| customer_demographics | Démographie | 74,2 Mo | 1 920 800 | 9 | 1 profil |
| store / warehouse | Magasins / Entrepôts | 3 Ko / 1 Ko | 12 / 5 | 29 / 14 | 1 lieu |
| date_dim / time_dim | Calendrier | 14,7 / 4,9 Mo | 109 573 / 86 400 | 28 / 10 | 1 jour / 1 seconde |
| Autres (promotion, reason, product_reviews…) | – | – | – | – | voir xlsx |

`data_refresh/` contient 12 fichiers (9,2 Mo), dont `customer` (1 000 lignes) et `customer_address` (500 lignes), **absents de `data/`**.

## 2. Format et structure

- Texte délimité par `|`, **sans en-tête**, UTF-8 valide. Le nombre de champs est constant dans chaque fichier.
- Les noms de colonnes sont **déduits** du schéma TPCx-BB : le nombre de champs correspond pour 32 fichiers sur 32, et les montants se recalculent exactement (`ext_sales_price = sales_price × quantity`).
- Les dates des tables de faits sont des **clés entières** (`*_date_sk`), ce qui impose une jointure avec `date_dim`.

## 3. Qualité

| Constat | Mesure | Impact |
|---|---|---|
| Clés étrangères vides dans les ventes | < 0,2 % | Faible : prévoir une valeur « Inconnu » |
| Quantités ≤ 0, montants incohérents | 0 | Les faits sont cohérents |
| Clics sans utilisateur | 42 % | Visiteurs anonymes |
| `s_closed_date_sk` (magasins) | dates de 1917 à 2141 | Champ inexploitable |
| Dates de promotion | de 1901 à 2199 | Champ inexploitable |
| Marge nette négative | 74 % des lignes magasin | Marge non fiable (artefact synthétique) |
| Doublons (ticket, article) | 0,6 % | Pas une clé stricte ; lignes différentes, à conserver |

## 4. Relations vérifiées

| Relation | Résultat | Statut |
|---|---|---|
| Ventes → date, heure, produit, magasin, promotion, démographie | 0 % de valeurs sans correspondance | Vérifiée |
| Ventes → client (`customer`) | **100 % sans correspondance** | Non disponible |
| Retours → vente (ticket + article) | 0 % orphelins dans `data/`, 93 à 96 % dans `data_refresh/` | Vérifiée (`data/`) |
| Stock → produit, entrepôt, date | 0 % de valeurs sans correspondance | Vérifiée |
| Clics → vente web (`wcs_sales_sk` → `ws_order_number`) | 100 % de correspondance | Déduite |
| 1 ticket = 1 transaction (1 magasin, 1 date, 1 client) | 0 exception sur 89 100 tickets | Vérifiée |
| Clés de `data/` et `data_refresh/` | Aucun chevauchement (le refresh prolonge les plages) | Vérifiée |
