# UC-08 – Synthèse décisionnelle : constats, limites et recommandations

<p class="meta">Retail Intelligence Platform · TP Jour 4 · 19/11/2026 · Livrable J4-06</p>

Public visé : direction générale, direction commerciale et responsables de magasin (profils de l'UC-01). Les chiffres
viennent de `docs/analytics/business-analysis.md` et du notebook.

> ⚠️ **Données synthétiques** (générateur TPCx-BB), **canal magasin seul**, 12 magasins, du 01/01/2001 au 13/12/2005.
> Ces constats valident une **démarche d'analyse**. Ils ne décrivent pas une entreprise réelle et ne doivent pas être
> présentés comme tels.

## 1. Les trois messages clés

1. **L'activité est stable.** Le CA net est d'environ 233 M$ par an de 2001 à 2004 (±1,1 %), sans saisonnalité.
   L'apparente baisse de 2005 (−6,5 %) se réduit à **−1,5 % à période égale**.
2. **Deux catégories font 72 % du CA**, parce qu'elles ont le plus grand catalogue. À l'intérieur du catalogue,
   **6 % des produits font la moitié du CA**.
3. **Les magasins se ressemblent** : 1,7 % de dispersion, et un classement annuel instable. Seul **Buffalo (KS)** est
   durablement en tête, grâce à son nombre de transactions.

## 2. Constats détaillés

Chaque constat sépare le résultat observé, l'interprétation, la limite et la recommandation.

### C1 – Activité stable, sans saisonnalité ; 2005 n'est pas en chute

| | |
|---|---|
| **Observé** | CA annuel de 230,9 à 234,3 M$ (2001-2004). Évolutions de −0,67 %, +1,14 % et +0,33 %. Indice saisonnier par jour de 98,8 à 101,0. 2005 : −6,48 % sur l'année, **−1,53 % du 01/01 au 13/12**. Décembre 2005 : 621 401 $ par jour, dans la norme |
| **Interprétation possible** | Ni croissance ni crise. Les écarts entre mois viennent du calendrier. La « chute » de fin 2005 est un effet de coupure des données |
| **Limite** | Profil plat produit par le générateur (un vrai commerce aurait un pic en décembre). CA avant retours. Canal web absent |
| **Recommandation** | Comparer **toujours à période égale**. Afficher les indicateurs `mois_complet` / `annee_complete` sur tout tableau de bord. Ne pas communiquer « −6,5 % en 2005 » |

### C2 – Le CA par catégorie suit la taille du catalogue ; il est concentré sur peu de produits

| | |
|---|---|
| **Observé** | Music 45,2 % et Books 26,6 % du CA, pour 45,7 % et 29,9 % des produits. Prix par unité ≈ 34 $ et remise ≈ 50 % dans toutes les catégories. CA par produit plus élevé dans les petites catégories (Clothing : 74 974 $ ; Music : 51 732 $). 1 % des produits font 39,4 % du CA, 6,1 % en font 50 % |
| **Interprétation possible** | La hiérarchie des catégories reflète le **nombre de références**, pas leur attractivité unitaire. Un petit noyau de produits porte le CA |
| **Limite** | Pas de marge exploitable (alerte qualité J3), pas de retours, pas de stock. Analyse non descendue aux classes ni aux marques |
| **Recommandation** | Juger une catégorie au **CA par produit** plutôt qu'au CA total. Suivre en priorité la disponibilité des ~1 100 produits qui font la moitié du CA (à croiser avec `inventory` une fois en Silver) |

### C3 – Magasins homogènes ; seul Buffalo se distingue durablement

| | |
|---|---|
| **Observé** | CA 2001-2004 de 75,9 à 80,8 M$ (coefficient de variation 1,67 %). Panier moyen de 12 745 à 13 072 $. Corrélation du CA avec les transactions : 0,88 ; avec l'effectif : −0,03. Rangs instables (Spearman entre années de −0,42 à 0,52). Buffalo : 3e, puis 1er en 2002, 2003 et 2004, avec +4,1 % de CA et +4,1 % de tickets |
| **Interprétation possible** | Hors Buffalo, les écarts annuels sont des fluctuations. Buffalo attire **plus de transactions**, pas de plus gros paniers |
| **Limite** | 12 magasins seulement. Pas de trafic, pas de zone de chalandise, surface sans unité. **Corrélation ≠ causalité** : on ne sait pas *pourquoi* Buffalo attire plus |
| **Recommandation** | Ne pas déclencher de plan d'action local sur un seul rang annuel : exiger un écart supérieur à 2 % deux années de suite. Étudier Buffalo avec les données clients (Q4), quand la jointure clients sera réparée |

### C4 – Les niveaux absolus ne sont pas réalistes

| | |
|---|---|
| **Observé** | Panier médian de 11 645 $, 372 articles par ticket, remise d'environ 50 % partout, marge négative sur 74 % des lignes |
| **Interprétation possible** | Ce sont des artefacts du générateur synthétique |
| **Limite** | Données synthétiques |
| **Recommandation** | N'utiliser que les **comparaisons relatives** (évolutions, parts, rangs). Ne citer aucun niveau absolu comme référence métier |

## 3. Ce que l'analyse ne permet pas d'affirmer

- Une **cause** : aucun des constats n'explique *pourquoi* (Buffalo, concentration des produits). Ce sont des
  constats statistiques.
- Une **rentabilité** : la marge n'est pas publiée.
- Un **poids des canaux**, un **taux de retour** ou un **niveau de stock** : ces tables ne sont pas en Silver (voir
  `kpi-dictionary.md`, §3).

## 4. Suite proposée

| Priorité | Action | Débloque |
|---|---|---|
| 1 | Ajouter `web_sales` et `store_returns` à la chaîne du J3 | Q2 (canaux), KPI-07 (retours), CA net de retours |
| 2 | Ajouter `inventory` | KPI-08, croisement avec les produits du constat C2 |
| 3 | Réparer la jointure clients (clé à revoir avec la source) | Q4, et l'explication de Buffalo (C3) |
| 4 | Industrialiser `kpi_retail.py` (planification, voir l'architecture UC-07) | Mise à jour régulière des KPI |
