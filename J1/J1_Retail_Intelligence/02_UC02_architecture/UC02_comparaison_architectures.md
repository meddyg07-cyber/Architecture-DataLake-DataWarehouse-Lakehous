# UC-02 – Comparaison des architectures

<p class="meta">Retail Intelligence Platform · TP Jour 1 · 16/11/2026</p>

## 1. Contraintes issues de UC-01

| Contrainte | Constat |
|---|---|
| Formats | Fichiers texte `\|` sans en-tête (structurés) ; un champ texte libre (avis) |
| Volume | Environ 1 Go aujourd'hui, dont 23 M de lignes de stock ; croissance par lots (`data_refresh`) |
| Domaines | 23 tables : ventes, retours, stocks, produits, magasins, démographie, navigation, avis |
| Historisation | Lots successifs à conserver ; dimensions sans historique dans le kit |
| Qualité | Champs incohérents, retours orphelins dans le refresh : il faut contrôler et mettre en quarantaine |
| Usages | KPI récurrents (BI) et exploration (clics, avis) |
| Sécurité | Données personnelles dans `customer` (nom, e-mail, date de naissance) |
| Évolution | Passage vers le cloud Azure (ADLS Gen2) au Jour 4 |

## 2. Comparaison

| Critère | Data Warehouse | Data Lake en zones | Data Lakehouse |
|---|---|---|---|
| **Principe** | Base relationnelle modélisée ; données nettoyées avant chargement (ETL) | Stockage de fichiers bruts, puis transformés par zones (ELT) | Data Lake + format de table transactionnel (Delta, Iceberg) offrant les garanties d'un DW |
| **Données adaptées** | Structurées | Toutes (structurées, semi-structurées, texte) | Toutes |
| **Avantages** | Requêtes SQL rapides, modèle clair pour la BI, qualité forte | Peu coûteux, conserve le brut, scalable, flexible | Un seul stockage pour BI et data science, ACID, historique des versions |
| **Limites** | Rigide, coûteux à faire évoluer, données brutes perdues, texte et clics mal gérés | Risque de « data swamp » sans gouvernance ; pas de transactions ACID | Plus complexe, technologies plus récentes |
| **Usages** | Reporting, KPI | Exploration, stockage d'historique, data science | BI + data science + historique |
| **Gouvernance** | Schéma imposé à l'écriture | À construire : catalogue, zones, droits | Schéma imposé, versions, mais catalogue nécessaire |
| **Pertinence ici** | Bonne pour les KPI, insuffisante pour les clics et les lots bruts | Bonne base : conserve les lots, accepte tous les formats | **La meilleure cible**, mais Delta Lake est facultatif dans le parcours |

## 3. Choix retenu

**Un Data Lake organisé en zones Bronze, Silver et Gold, avec des fichiers Parquet et une zone Gold modélisée en étoile.**

- Le **Data Lake** conserve les lots bruts (traçabilité, rejouabilité) et accepte les clics et les avis.
- La zone **Gold en étoile** joue le rôle du Data Warehouse pour les KPI : faits ventes, retours et stock ; dimensions produit, magasin, date et démographie.
- Ce choix suit les **composants obligatoires** du parcours : HDFS, NiFi, Spark, Parquet.
- **Delta Lake** peut être ajouté plus tard sur Silver et Gold pour obtenir un Lakehouse. C'est un approfondissement facultatif, pas une condition du socle.

> Limite assumée : sans Delta Lake, Parquet n'offre ni transactions ACID ni mises à jour ligne à ligne. Les lots sont donc rechargés par partition complète.

## 4. Questions de recul

1. **Pourquoi un Data Lake complète un Data Warehouse ?** Il garde le brut et les données non tabulaires (clics, avis) que le DW ne stocke pas.
2. **Quand un Lakehouse est-il pertinent ?** Quand on veut la BI et la data science sur un même stockage, avec des mises à jour fiables (ACID).
3. **Pourquoi conserver le brut ?** Pour rejouer un traitement, corriger une règle et prouver la provenance.
4. **Pourquoi des zones ?** Pour séparer brut, nettoyé et prêt à l'emploi, avec des droits et une qualité différents à chaque niveau.
5. **Ce que Parquet seul ne garantit pas :** les transactions ACID, les mises à jour et suppressions de lignes, l'historique des versions et l'évolution contrôlée du schéma.
6. **Risques d'une gouvernance insuffisante :** un « data swamp », des KPI différents d'une équipe à l'autre, et des fuites de données personnelles.
7. **Socle ou approfondissement :** le socle comprend Linux, Python, HDFS, NiFi, Spark, Parquet et ADLS Gen2. Delta Lake et HBase relèvent de l'approfondissement.
