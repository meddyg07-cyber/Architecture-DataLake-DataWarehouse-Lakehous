# UC-06 – Étape 1 : fiche d'environnement

<p class="meta">Retail Intelligence Platform · TP Jour 3 · 18/11/2026 · Livrable 1</p>

Preuves : `preuves/logs/00_environnement.log`, `preuves/logs/01_test_spark.log`.

## 1. Versions observées

| Composant | Version observée | Commande de vérification |
|---|---|---|
| Système | Windows 11 + WSL 2, **Ubuntu 24.04** (noyau 6.6 WSL2), 12 cœurs, 7,6 Gio de RAM | `nproc`, `free -h` |
| Python | **3.12.3** (Python système d'Ubuntu) | `python --version` |
| Environnement virtuel | `~/retail-intelligence/tp3/.venv` (créé par `python3 -m venv`) | `which python` |
| Java | **OpenJDK 17.0.21** (même JVM que Hadoop) | `java -version` |
| PySpark / Spark | **4.3.0** (paquet `pyspark` installé par pip dans le venv, Spark embarqué) | `pip show pyspark`, `spark.version` |
| JupyterLab | **4.6.6** (+ `ipykernel`, `nbconvert`) | `pip show jupyterlab` |
| Hadoop / HDFS | **3.5.0**, pseudo-distribué, `hdfs://localhost:9000` (installé au J2) | `hdfs version` |

**Compatibilité vérifiée.** Spark 4.x accepte Java 17 et Java 21. Nous gardons **Java 17**, la JVM qui fait déjà tourner
HDFS : une seule version de Java pour Hadoop et Spark. Java 21 n'est utilisé que par NiFi (J2). PySpark embarque son
propre client Hadoop, ce qui lui permet de lire `hdfs://localhost:9000` sans autre configuration.

## 2. Mode d'exécution

| Élément | Valeur |
|---|---|
| Mode | **Spark local** : `master("local[*]")`, un seul processus qui utilise les 12 cœurs. Ce n'est **pas un cluster** |
| Stockage | **HDFS réel** (NameNode et DataNode du J2, réplication 1) : lecture et écriture en `hdfs://` |
| Interfaces | Scripts Python lancés dans le terminal, et JupyterLab pour les notebooks (exécutés avec `nbconvert --execute`, sorties conservées) |
| Paramètres Spark | `spark.sql.shuffle.partitions=12` (au lieu de 200, inutile pour 670 000 lignes), fuseau `Europe/Paris`, compression Parquet `snappy`, mode ANSI actif par défaut (Spark 4) |

## 3. Chemins

| Rôle | Chemin |
|---|---|
| Code du TP (dépôt Git) | `J3/J3_Retail_Intelligence/` (vu sous Ubuntu par `/mnt/c/...`) |
| Environnement Python | `~/retail-intelligence/tp3/.venv` (hors dépôt, non versionné) |
| **Entrée** (lecture seule, droits 555 depuis le J2) | `hdfs:///retail-lake/raw/tpcxbb/initial/<table>/<table>.dat` |
| Sortie Bronze | `hdfs:///retail-lake/bronze/tpcxbb/<table>` |
| Sortie Silver | `hdfs:///retail-lake/silver/tpcxbb/<table>` |
| Sortie Gold | `hdfs:///retail-lake/gold/retail/<jeu>` |
| Qualité (quarantaine, rapport) | `hdfs:///retail-lake/quality/tpcxbb/` |
| Fichiers techniques (tests, comparaison des formats) | `hdfs:///retail-lake/logs/tp3/` |
| Preuves locales | `J3_Retail_Intelligence/preuves/` (JSON, CSV, journaux) |

## 4. Vérifications attendues (§4.4.2)

| Vérification | Résultat (`01_test_spark.log`) |
|---|---|
| Lancer un interpréteur et un notebook | ✅ `python` du venv, et JupyterLab avec le noyau du venv |
| Initialiser une session Spark | ✅ `Version Spark : 4.3.0`, `Master : local[*]`, 12 cœurs, Java 17.0.21 |
| Lire un fichier de test | ✅ `store.dat` lu **dans HDFS** : 12 lignes, 29 colonnes |
| Afficher un schéma | ✅ `printSchema()` (types proposés par `inferSchema`) |
| Écrire dans un répertoire autorisé | ✅ Parquet écrit dans `/retail-lake/logs/tp3_test_spark` puis relu (3 lignes). **Jamais dans Raw** |

## 5. Ressources disponibles

12 cœurs logiques et environ 4,6 Gio de mémoire disponible. Le plus gros fichier traité (`store_sales.dat`, 93 Mo,
667 579 lignes) tient largement en mémoire : nous n'avons eu besoin ni d'échantillon, ni de réglage de mémoire.

## Captures (18/11/2026, Edge piloté par script, bandeau date et URL)

![JupyterLab avec le noyau du venv : la session Spark est créée (Spark 4.3.0, local[*], Python 3.12.3) et la source Raw est dans HDFS.](../preuves/captures/etape1_jupyterlab_session_spark.png)

*JupyterLab avec le noyau du venv : la session Spark est créée (Spark 4.3.0, local[*], Python 3.12.3) et la source Raw est dans HDFS.*
