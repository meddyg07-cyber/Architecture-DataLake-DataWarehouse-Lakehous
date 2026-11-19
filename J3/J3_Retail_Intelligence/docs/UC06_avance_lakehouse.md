# Partie avancée (facultative) – Approfondissement Lakehouse

<p class="meta">Retail Intelligence Platform · TP Jour 3 · 18/11/2026</p>

> **Statut : étude conceptuelle, non exécutée.** Aucun format de table (Delta Lake, Iceberg, Hudi) n'a été installé :
> le sujet ne l'impose pas et interdit d'installer un composant non validé. Les constats sur Parquet, en revanche,
> s'appuient sur **nos** sorties réelles de la partie obligatoire.

## 1. Limites de Parquet seul, constatées sur notre chaîne

| Ce que Parquet permet (vérifié) | Ce qu'il ne garantit pas (constaté sur nos dossiers) |
|---|---|
| Stockage colonne : 43 Mo contre 93 Mo pour le `.dat` | **Atomicité** : `02_silver.py` écrit avec `overwrite`. S'il s'arrête au milieu, le dossier `silver/store_sales` reste à moitié vide, et un lecteur au même moment voit des données partielles |
| Lecture sélective : `ReadSchema` limité à 2 colonnes | **Historique** : chaque exécution écrase la précédente. Impossible de relire « le Silver d'hier » |
| Compression `snappy` | **Mise à jour d'une ligne** : corriger une vente demande de réécrire toute la partition `sold_year=…` |
| Partitionnement : `PartitionFilters: sold_year = 2004` | **Schéma imposé** : rien n'empêche de déposer dans le dossier un fichier avec une colonne en plus ou un type différent |
| Statistiques min/max par bloc | **Concurrence** : deux scripts qui écrivent en même temps peuvent se marcher dessus. Pas d'isolation |

## 2. Formats de tables Lakehouse

Les trois formats ajoutent une **couche de métadonnées** au-dessus de fichiers Parquet. C'est ce journal ou ce catalogue
qui définit quels fichiers forment la version courante de la table.

| Critère | Delta Lake | Apache Iceberg | Apache Hudi |
|---|---|---|---|
| Métadonnées | Journal de transactions `_delta_log/` (JSON + checkpoints Parquet) | Arbre de métadonnées : metadata.json → manifest lists → manifests, référencé par un catalogue | Timeline `.hoodie/` (commits, compactions) |
| Transactions | ACID par commit atomique dans le journal ; contrôle de concurrence optimiste | ACID par remplacement atomique du pointeur de métadonnées dans le catalogue | ACID ; deux modes de table : *Copy-on-Write* et *Merge-on-Read* |
| Évolution du schéma | Contrôle du schéma à l'écriture, ajout de colonnes (`mergeSchema`) | Très complète : ajout, renommage, suppression et réordonnancement par identifiant de colonne ; évolution des partitions | Ajout de colonnes ; évolution compatible |
| Historique | *Time travel* par version ou date ; `VACUUM` pour purger | Snapshots, *time travel*, branches et tags | Requêtes incrémentales et *time travel* sur la timeline |
| Moteurs | Spark (natif), et d'autres via connecteurs | Spark, Flink, Trino, Dremio… (format très ouvert) | Spark, Flink, Hive, Presto |
| Point fort | Simplicité avec Spark ; `MERGE INTO` | Neutralité vis-à-vis des moteurs ; tables très grandes | Ingestion incrémentale et *upserts* fréquents |
| Contraintes | Maintenance (`OPTIMIZE`, `VACUUM`) | Nécessite un catalogue (Hive, REST, Glue…) | Plus de réglages (compaction, index) |

Ces fonctionnalités dépendent de la version de chaque format. Elles sont à vérifier dans la documentation de la version
retenue avant tout choix.

## 3. Scénario d'évolution du schéma

**Évolution supposée** : la source ajoute à `store_sales` une colonne `ss_channel_detail` (texte) et passe
`ss_ticket_number` de `bigint` à texte (format `MAG-000123`).

| Point | Analyse |
|---|---|
| Impact sur l'existant | Avec Parquet seul, les anciens et les nouveaux fichiers n'ont plus le même schéma. Spark échoue, ou met les valeurs à null sans `mergeSchema`. Le changement de type casse R01 (le ticket ne se convertit plus en `bigint`), donc **toutes** les nouvelles lignes partent en quarantaine |
| Contrôles nécessaires | Comparer, avant tout traitement, le nombre et les types de colonnes du lot reçu avec le schéma attendu (`common.SOURCES`). Bloquer le lot (statut ECHEC) au lieu de laisser le Silver se dégrader. Mesurer le taux de quarantaine par lot (une alerte au-delà de 1 %) |
| Adaptation du traitement | Versionner le schéma (`SOURCES_V2`). Ajouter la colonne en `null` pour l'historique. Garder le ticket en texte et créer une clé de substitution. Rejouer Bronze → Silver sur le nouveau lot seulement |
| Preuves | Rapport qualité avant et après ; volume réconcilié par lot ; relecture du schéma Silver ; avec un format de table, l'historique des versions montre le commit qui a changé le schéma |

## 4. Stratégie incrémentale : intégrer `data_refresh`

Le lot `data_refresh` contient 6 632 ventes. Au J1, nous avions relevé que `ss_sold_date_sk` y va de 38697 à 38715. Or
38697 correspond au 13/12/2005, qui est aussi le **dernier jour du lot `initial`** : les deux lots se recouvrent sur une
journée, et le risque de doublon est donc réel.

| Question | Proposition |
|---|---|
| Identifier les nouvelles données | Un lot = un dossier Raw (`raw/tpcxbb/refresh/<date>`). Un **registre des lots traités** (table `quality/lots_traites` : lot, fichier, MD5, nombre de lignes, date) : un lot dont le MD5 est déjà dans le registre n'est pas retraité |
| Éviter les doublons | Comme (ticket, article) n'est pas unique, il faut une **empreinte de ligne** : hachage des 23 colonnes métier. Le lot est fusionné dans le Silver avec un *anti-join* sur cette empreinte, ou avec `MERGE INTO` si l'on dispose d'un format de table |
| Gérer les corrections | Une correction de la source arrive comme une nouvelle version de la ligne, avec la même clé métier. Parquet seul oblige à réécrire la partition concernée (par exemple `sold_year=2005`) ; un format de table fait un `MERGE` ou un `UPDATE` atomique |
| Tracer les exécutions | `_lot` et `_run_id_*` sont déjà présents sur chaque ligne. On ajoute un journal des exécutions (lot, début, fin, lignes lues, écrites et en quarantaine, statut) dans `logs/` |
| Vérifier la cohérence | Volume avant + volume du lot − doublons = volume après ; CA du Gold recalculé uniquement pour les partitions touchées (2005), puis réconcilié avec le Silver. C'est le même contrôle que `04_qualite.py`, ventilé par lot |

## 5. Architecture Lakehouse cible

```
 Sources TPCx-BB (.dat)      NiFi (J2)         Spark / PySpark (J3)                        Consommateurs (J4)
 ───────────────────── ──► ─────────── ──► ┌───────────────────────────────────────────┐ ──► Power BI / notebooks
 lot initial, refresh       GetFile         │ RAW     .dat bruts, lecture seule (HDFS)   │      Synapse / SQL
                            → PutHDFS       │ BRONZE  Parquet texte + provenance         │
                                            │ SILVER  Parquet typé, nettoyé, partitionné │◄── contrôles qualité
                                            │ GOLD    Parquet agrégé (KPI)               │    + quarantaine
                                            └───────────────────────────────────────────┘
                     Catalogue / métadonnées : AUJOURD'HUI = chemins + common.py + docs ;
                     CIBLE = Hive Metastore ou catalogue Iceberg/Unity, avec un format de table
```

| Élément | Garantie réelle aujourd'hui | Dépendrait d'une technologie supplémentaire |
|---|---|---|
| Traçabilité ligne par ligne (`_source_file`, `_run_id`) | ✅ | – |
| Contrôles qualité et réconciliation | ✅ (script, pas une contrainte du stockage) | Contraintes à l'écriture (`CHECK`) : Delta / Iceberg |
| Écriture atomique, isolation des lecteurs | ❌ | Format de table |
| Historique et retour arrière | ❌ (seulement l'historique du rapport qualité) | *Time travel* |
| Upsert et correction ligne par ligne | ❌ | `MERGE INTO` |
| Catalogue partagé (tables nommées, SQL) | ❌ (des chemins HDFS) | Metastore ou catalogue |

**Conclusion.** Notre chaîne applique l'**organisation** Lakehouse : zones, formats ouverts, qualité, traçabilité. Elle
n'en a pas les **garanties transactionnelles**. Pour les obtenir, la première étape serait d'écrire Silver et Gold en
**Delta Lake** ou **Iceberg** (paquet ajouté à Spark, après validation de la matrice des versions), sans changer la
logique des scripts.
