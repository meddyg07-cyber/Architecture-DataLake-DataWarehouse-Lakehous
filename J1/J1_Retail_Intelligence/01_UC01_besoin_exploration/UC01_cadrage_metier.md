# UC-01 – Cadrage métier

<p class="meta">Retail Intelligence Platform · TP Jour 1 · 16/11/2026</p>

## 1. Contexte et objectifs

Retail Intelligence vend en **magasin** et sur le **web**. La direction veut des indicateurs fiables pour suivre le CA, comparer les magasins et les canaux, et comprendre l'évolution de l'activité.

| # | Objectif | Mesure du succès |
|---|---|---|
| O1 | Un CA unique et partagé par toutes les directions | Définition documentée dans le dictionnaire KPI |
| O2 | Comparer magasins, canaux et catégories | Indicateurs sur un périmètre identique |
| O3 | Suivre l'évolution dans le temps | Évolution N/N-1 sur des périodes complètes |
| O4 | Suivre les retours et les stocks | Taux de retour, stock hebdomadaire |

> Le jeu TPCx-BB est **synthétique**. Les chiffres servent à valider la faisabilité des indicateurs, pas à prendre des décisions.

## 2. Utilisateurs

| Profil | Responsabilités | Besoins | Priorité |
|---|---|---|---|
| Direction générale | Stratégie, arbitrage entre canaux | CA consolidé, évolution, poids de chaque canal | Indispensable |
| Direction commerciale | Assortiment, promotions | Meilleurs produits et catégories, profils d'acheteurs | Indispensable |
| Responsable magasin | Pilotage de son magasin | CA, transactions, panier, retours | Indispensable |
| Contrôleur de gestion | Fiabilité financière | Remises, retours, écarts entre périodes | Utile |
| Responsable stocks | Disponibilité produits | Stock par article et par lieu | Utile |
| Équipe Data | Intégration, qualité | Contrôles, traçabilité des lots | Indispensable |

## 3. Fiche du kit (section 3.4)

| Information | Valeur constatée |
|---|---|
| Nom du kit | `retail_project/` : deux lots, `data/` et `data_refresh/` |
| Version / provenance | Non communiquée (structure conforme au schéma TPCx-BB) |
| Date de mise à disposition | Non communiquée |
| Source de distribution | Fichiers remis par le formateur |
| Format | `.dat` texte, séparateur `\|`, **sans en-tête**, UTF-8 (+ 2 rapports `.csv`) |
| Volume total | 968,3 Mo (`data/` 960 Mo, `data_refresh/` 9,2 Mo) |
| Nombre de fichiers | 34 fichiers, 23 tables |
| Outil de génération | Non communiqué |

## 4. Ce que les données couvrent

| Besoin | Couverture |
|---|---|
| CA, transactions, panier, quantités, remises par canal, magasin, catégorie, période | **Couvert** |
| Retours par produit et par motif | **Couvert** |
| Profil des clients | **Partiel** : démographie uniquement, pas de référentiel client |
| Stocks | **Partiel** : entrepôts uniquement, pas de stock magasin |
| Comportement web | **Partiel** : clics sans session ni type d'événement |

Le détail est dans `UC01_questions_decisionnelles.pdf`, `UC01_qualification_donnees.pdf` et `UC01_limites_et_hypotheses.pdf`.
