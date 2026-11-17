# UC-02 – Positionnement des composants

<p class="meta">Retail Intelligence Platform · TP Jour 1 · 16/11/2026</p>

| Composant | Statut (référentiel) | Rôle dans l'architecture | Couche | Jour |
|---|---|---|---|---|
| Linux / Ubuntu | Obligatoire | Environnement d'exécution local | Socle | J2 |
| Python | Obligatoire | Exploration (fait en UC-01), scripts de contrôle | Préparation | J1 |
| Hadoop / HDFS | Obligatoire | Stockage distribué des zones Bronze, Silver et Gold | Stockage | J2 |
| Apache NiFi | Obligatoire | Ingestion des lots, contrôles d'entrée, métadonnées | Ingestion | J2 |
| Apache Spark / PySpark | Obligatoire | Transformations Bronze → Silver → Gold, calcul des KPI | Traitement | J3 |
| Parquet | Format de référence | Stockage colonnaire des zones Silver et Gold | Stockage | J3 |
| ADLS Gen2 | Objectif obligatoire | Déclinaison cloud du Data Lake | Stockage cloud | J4 |
| Azure Data Factory | Présentation / étude | Équivalent cloud de NiFi (orchestration) | Ingestion cloud | J4 (étude) |
| Azure Synapse | Présentation / étude | Requêtes SQL sur le lac côté cloud | Usage cloud | J4 (étude) |
| Delta Lake | **Facultatif** | Transactions ACID sur Silver et Gold, ce qui ferait un Lakehouse | Stockage | J3 (option) |
| HBase | **Facultatif** | Accès rapide par clé (ex. fiche produit) ; pas nécessaire pour les KPI | Usage | J3 (option) |
| PDGF | Selon kit | Génération de données ; non utilisé (données déjà fournies) | – | – |

**Règle respectée :** l'architecture fonctionne sans Delta Lake ni HBase, qui ne conditionnent pas le socle.
