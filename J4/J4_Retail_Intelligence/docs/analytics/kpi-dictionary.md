# UC-08 – Dictionnaire des KPI (mise à jour du J1)

<p class="meta">Retail Intelligence Platform · TP Jour 4 · 19/11/2026 · Livrable J4-02</p>

Source unique des formules : `analytics/scripts/kpi_retail.py` (fonction `kpis`). Le notebook et la ligne de
commande l'importent tous les deux, donc une formule n'est écrite qu'une fois. Valeurs : `analytics/outputs/kpi.csv`.

**Changements par rapport au J1** (`UC01_dictionnaire_KPI.xlsx`) :
- le périmètre est réduit au **canal magasin**, le seul transformé en Silver ;
- KPI-01 est dédoublé en CA brut et **CA net payé**, la mesure du Gold ;
- le panier moyen est donné en net et en brut ;
- KPI-06 ajoute une variante **à période égale** ;
- KPI-07 et KPI-08 sont **suspendus**.

**Filtres communs** : canal magasin ; lot `initial` ; aucune ligne exclue (quarantaine vide au J3) ; ventes à 0 $
incluses (elles comptent dans les quantités, pas dans le CA).

**Unité monétaire** : notée « $ ». C'est la convention TPC-DS, mais la source ne documente pas la devise. Tous les
montants sont **hors taxes et avant retours**.

## 1. KPI calculés

| Code | Nom | Définition métier | Formule (Spark) | Champs | Granularité de calcul | Unité | Valeur 2004 | Limites d'interprétation |
|---|---|---|---|---|---|---|---:|---|
| KPI-01a | CA brut | Ventes après remise, avant coupons | `SUM(ss_ext_sales_price)` | `ss_ext_sales_price` | Ligne → année, mois, magasin, catégorie | $ | 260 029 656,73 | Définition du J1. Avant retours |
| KPI-01b | **CA net payé** | Ce que le client a payé, hors taxes | `SUM(ss_net_paid)` (= CA brut − coupons) | `ss_net_paid` | idem | $ | **234 344 934,29** | Mesure de référence du Gold. Avant retours |
| KPI-02 | Nombre de transactions | Tickets de caisse distincts | `COUNT(DISTINCT ss_store_sk, ss_ticket_number)` | `ss_store_sk`, `ss_ticket_number` | Ticket | tickets | 18 039 | Vérifié : 1 ticket = 1 magasin, 1 date, 1 client. **≠ nombre de lignes** (136 014, soit 7,5 fois plus) |
| KPI-03 | Panier moyen | CA moyen par transaction | KPI-01b / KPI-02 (net) et KPI-01a / KPI-02 (brut) | – | Ticket | $ par ticket | 12 991,02 (net), 14 414,86 (brut) | Moyenne tirée vers le haut (médiane : 11 645 $). Niveau **irréaliste** (372 articles par ticket), donc seules les comparaisons relatives ont un sens |
| KPI-04 | Quantités vendues | Unités vendues | `SUM(ss_quantity)` | `ss_quantity` | Ligne | unités | 6 887 086 | Additionne des produits différents : utile en relatif |
| KPI-05 | Taux de remise | Part du prix catalogue accordée en remise | `SUM(ss_ext_discount_amt) / SUM(ss_ext_list_price)` | 2 champs | Ligne → agrégat | % | 50,03 | Environ 50 % partout (artefact du générateur) : non discriminant |
| KPI-06 | Évolution du CA N/N-1 | Variation du CA net d'une année à l'autre | `(CA_N − CA_N-1) / CA_N-1`, **sur années complètes** ou **à période égale** (01/01 → 13/12) | KPI-01b, `sold_date` | Année | % | +0,33 (année) ; +0,18 (période égale) | 2005 : −6,48 % sur l'année, mais **−1,53 % à période égale**. Ne jamais comparer 2005 entière aux autres années |

## 2. Indicateurs d'analyse dérivés (UC-08)

| Indicateur | Formule | Source | Granularité | Unité | Usage |
|---|---|---|---|---|---|
| CA par jour | CA net du mois / jours vendus du mois (13 pour 12/2005) | Gold G1 | Mois | $ par jour | Neutraliser la longueur des mois (Analyse 1) |
| Indice saisonnier | CA moyen du mois (ou par jour) / moyenne générale × 100, sur 2001-2004 | Gold G1 | Mois de l'année | base 100 | Détecter une saisonnalité (Analyse 1) |
| Part du CA d'une catégorie | CA catégorie / CA total × 100 | Gold G1 | Catégorie, 2001-2004 | % | Analyse 2 |
| CA par produit | CA catégorie / nombre de produits de la catégorie | Gold G1 + Silver `item` | Catégorie | $ par produit | Séparer l'effet « taille du catalogue » (Analyse 2) |
| Concentration | Part du CA faite par les x % de produits qui vendent le plus | Silver `store_sales` | Produit | % | Analyse 2 |
| Écart au magasin moyen | CA magasin / CA moyen d'un magasin − 1 | Gold G2 | Magasin, 2001-2004 | % | Analyse 3 |
| Stabilité du classement | Corrélation de Spearman des rangs entre deux années | Gold G2 | Magasin × année | sans unité, −1 à 1 | Analyse 3 |

## 3. KPI suspendus ou non calculables au J4

| Code | KPI | Raison | Ce qu'il faudrait |
|---|---|---|---|
| KPI-01 et 02 (web) | CA et transactions du canal web, poids des canaux (Q2) | `web_sales` n'est pas en Silver | Ajouter `web_sales` à la chaîne du J3 (mêmes règles R01-R10) |
| KPI-07 | Taux de retour | `store_returns` n'est pas en Silver. Les retours sont datés au retour (jusqu'en 2008) | Transformer `store_returns`. Définir numérateur, dénominateur et période (date de vente ou de retour) |
| KPI-08 | Stock moyen | `inventory` n'est pas en Silver | Transformer `inventory` (photos hebdomadaires par entrepôt) |
| – | Marge | 74,3 % de lignes à marge négative (alerte qualité J3) : coûts non qualifiés | Ne pas publier tant que les coûts ne sont pas validés par la source |

## 4. Contrôles de cohérence des KPI

1. **J1 = J4** : 39 valeurs comparées (8 KPI × 5 années, sans l'évolution de 2001), **0 écart**. Le J1 calculait avec
   Pandas sur les `.dat` bruts, le J4 avec Spark sur le Silver (`analytics/outputs/reconciliation_j1_j4.csv`).
2. **Gold = Silver** : CA net 1 150 529 586,37 $ et quantités 33 755 474, identiques dans le Silver, G1 et G2.
3. **Notebook = ligne de commande** : 40 valeurs identiques (`tests/test_kpi_cli.py`, `preuves/logs/03_test_kpi_cli.log`).

## Captures (19/11/2026, Edge piloté par script, bandeau date et URL)

![Réconciliation J1 = J4 : 39 comparaisons, écart maximal 0,0. Le notebook s'arrête (`assert`) s'il y a un écart.](../../preuves/captures/uc08_04_reconciliation_j1_j4.png)

*Réconciliation J1 = J4 : 39 comparaisons, écart maximal 0,0. Le notebook s'arrête (`assert`) s'il y a un écart.*

![Test de reproductibilité : la ligne de commande `kpi_retail.py` redonne les 40 valeurs du notebook, avec un écart nul.](../../preuves/captures/uc08_14_test_reproductibilite.png)

*Test de reproductibilité : la ligne de commande `kpi_retail.py` redonne les 40 valeurs du notebook, avec un écart nul.*
