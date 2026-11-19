# J3 – Retail Intelligence Platform

TP Jour 3 (UC-06) : transformation, qualité des données et Data Lakehouse avec PySpark et Parquet. IPSSI, Mastère
Data & IA.

Chaîne réalisée : **HDFS Raw (J2) → Bronze → Silver → Gold**, en Parquet. Tout a été **réellement exécuté** le
18/11/2026, en Spark local, sur les vrais fichiers TPCx-BB lus dans HDFS. Aucune donnée n'a été simulée, sauf les
8 lignes du test des règles, marquées `TEST_SYNTHETIQUE`.

## Contenu et livrables

| N° | Livrable du sujet | Fichier |
|---|---|---|
| 1 | Fiche environnement | `docs/UC06_fiche_environnement.md` |
| 2 | Inventaire technique | `docs/UC06_inventaire_sources.md` |
| 3 | Notebook d'exploration | `notebooks/01_exploration.ipynb` (exécuté, sorties conservées) |
| 4 | Règles de nettoyage | `docs/UC06_regles_nettoyage.md` |
| 5 | Scripts PySpark | `transformations/01_bronze.py`, `02_silver.py`, `03_gold.py` (+ `common.py`) |
| 6 | Données Silver | `hdfs:///retail-lake/silver/tpcxbb/{store_sales,item,date_dim,store}`, documentées dans `docs/UC06_transformations_silver_gold.md` |
| 7 | Données Gold | `hdfs:///retail-lake/gold/retail/{ventes_mensuelles_categorie,performance_magasin_annuelle}`, même document |
| 8 | Données Parquet | `docs/UC06_parquet_formats.md`, `transformations/05_formats.py`, `notebooks/02_lecture_silver_gold.ipynb` |
| 9 | Rapport qualité | `docs/UC06_rapport_qualite.md`, `transformations/04_qualite.py`, `preuves/08_rapport_qualite.csv` |
| 10 | README | ce fichier |
| 11 | Preuves | `preuves/` : bilans JSON, `logs/` (un journal par étape), `captures/` |
| – | Questions de recul | `J3_questions_de_recul.md` |
| – | Partie avancée (facultative, **étude non exécutée**) | `docs/UC06_avance_lakehouse.md` |
| – | UC-05 NoSQL / HBase (facultatif) | **non traité** |

Les données Silver et Gold restent dans HDFS : elles **ne sont pas versionnées**. Le dépôt contient le code, les
paramètres, la documentation et les preuves, ce qui suffit à les reproduire.

## Prérequis et versions observées

| Composant | Version |
|---|---|
| Ubuntu 24.04 sous WSL 2 | 12 cœurs, 7,6 Gio de RAM |
| Python | 3.12.3, venv `~/retail-intelligence/tp3/.venv` |
| PySpark / Spark | 4.3.0 (pip), **mode local `local[*]`** |
| Java | OpenJDK 17.0.21 (le même que Hadoop) |
| Hadoop HDFS | 3.5.0, `hdfs://localhost:9000`, installé au J2 |
| JupyterLab | 4.6.6 |

## Reproduire

Toutes les commandes se lancent **dans Ubuntu (WSL)**.

**1. Installation (une seule fois)**
```bash
sudo apt install python3.12-venv                     # absent par défaut sur Ubuntu 24.04 (erreur n° 1)
mkdir -p ~/retail-intelligence/tp3 && cd ~/retail-intelligence/tp3
python3 -m venv .venv && source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install pyspark==4.3.0 jupyterlab ipykernel nbconvert
```

**2. Démarrer HDFS** (NiFi n'est pas nécessaire au J3)
```bash
bash ../../J2/J2_Retail_Intelligence/scripts/start_env.sh      # ou : start-dfs.sh avec JAVA_HOME=Java 17
```

**3. Exécuter la chaîne**, depuis `J3/J3_Retail_Intelligence/`
```bash
bash scripts/run_all.sh                       # tout, dans l'ordre (environ 7 min), journaux dans preuves/logs/
bash scripts/run_all.sh 05_qualite            # ou une seule étape
bash scripts/tp3.sh python transformations/03_gold.py                 # ou un script à la main
bash scripts/tp3.sh jupyter nbconvert --to notebook --execute --inplace notebooks/01_exploration.ipynb
bash scripts/tp3.sh jupyter lab               # interface JupyterLab (Ctrl+C pour arrêter)
```

**Ordre d'exécution et sorties**

| # | Script | Entrée | Sortie | Contrôle intégré |
|---|---|---|---|---|
| 0 | `scripts/test_spark.py` | `raw/…/store.dat` | `logs/tp3_test_spark` | Session, lecture et écriture |
| 1 | `transformations/01_bronze.py` | `raw/tpcxbb/initial/*.dat` | `bronze/tpcxbb/<table>` | Lignes Raw = Bronze |
| 2 | `transformations/02_silver.py` | Bronze | `silver/tpcxbb/<table>` + `quality/tpcxbb/quarantaine/<table>` | Bronze = Silver + quarantaine |
| 3 | `transformations/03_gold.py` | Silver | `gold/retail/<jeu>` | Jointures (lignes avant et après), unicité du grain |
| 4 | `transformations/04_qualite.py` | Raw, Bronze, Silver, Gold | `preuves/08_*`, `quality/tpcxbb/rapport_controles` | 31 contrôles, arrêt si ECHEC |
| 5 | `transformations/05_formats.py` | Silver | `logs/tp3/formats/` | Volumes, types, temps |
| 6 | `tests/test_regles_silver.py` | 8 lignes synthétiques en mémoire | – | 8 cas sur 8 |

**Paramètres** : tous dans `transformations/common.py`, à savoir :
- les chemins HDFS (variable `TP3_HDFS` pour changer de NameNode) ;
- le lot ;
- les sources retenues et leurs schémas (noms et types) ;
- les clés candidates ;
- `TP3_MASTER` pour le mode Spark.

**Arrêt** : `Ctrl+C` dans JupyterLab, puis `bash ../../J2/J2_Retail_Intelligence/scripts/stop_env.sh`.

## Limites connues

- **Spark local**, un seul poste : ce n'est pas un cluster. Les temps mesurés sont indicatifs.
- Données **synthétiques** : marges négatives sur 74 % des lignes, écarts minimes. Les résultats valident la chaîne,
  pas une tendance métier.
- Seul le lot `initial` est traité. `data_refresh` relève de la stratégie incrémentale, qui est seulement conçue.
- Le CA n'intègre pas les retours (`store_returns`).
- Parquet seul n'offre **ni ACID, ni historique, ni mise à jour de ligne**.
- La clé (ticket, article) n'est pas unique : il n'y a pas d'identifiant de ligne de vente.

## Erreurs rencontrées et corrections

| # | Erreur | Cause | Correction |
|---|---|---|---|
| 1 | `ensurepip is not available` à la création du venv | Paquet `python3.12-venv` absent sur Ubuntu 24.04 | `apt install python3.12-venv`, puis le venv a été recréé |
| 2 | `hdfs: command not found` dans `wsl bash -c` | Un shell non interactif s'arrête au début de `~/.bashrc` : les variables Hadoop n'y sont pas chargées | `scripts/env_tp3.sh` exporte explicitement `JAVA_HOME`, `HADOOP_HOME` et `PATH` |
| 3 | PowerShell : `référence de variable non valide` sur `\$PATH`, et guillemets supprimés dans les arguments passés à `wsl` | PowerShell 5.1 interprète `$` et retire les `"` des arguments transmis aux exécutables natifs | Commandes regroupées dans des scripts (`tp3.sh`, `run_all.sh`) appelés sans guillemets |
| 4 | Barres de progression Spark dans les journaux | Option `spark.ui.showConsoleProgress` active par défaut | Désactivée dans `common.spark_session()` et dans `test_spark.py` |
| 5 | **`[CAST_INVALID_INPUT] The value 'abc' … cannot be cast to "INT"`** dans le test des règles | **Spark 4 est en mode ANSI** : `cast()` sur une valeur invalide **lève une erreur** au lieu de renvoyer `null`. R01 aurait arrêté tout le traitement au lieu de mettre la ligne en quarantaine | `try_cast()` dans `02_silver.py` et dans le notebook. Le test passe ensuite (8 cas sur 8). **Bug réel trouvé par le test, invisible sur les vraies données** |
| 6 | `ERROR: Pipe to stdout was broken` dans `00_environnement.log` | `pip show … \| head -2` coupe le tube pendant que pip écrit encore | `grep -E "^(Name\|Version)"` à la place de `head` |
| 7 | Étape `08_hdfs_sorties` interrompue | Mon affichage côté PowerShell coupé à 80 lignes, ce qui a fermé le tube | `run_all.sh` accepte une liste d'étapes ; les étapes 00 et 08 ont été relancées seules |

## Usage de l'IA

Code, exécution et rédaction réalisés avec l'assistance de Claude (Anthropic). Toutes les commandes ont été réellement
exécutées sur mon poste. Les chiffres des documents proviennent des sorties enregistrées dans `preuves/`. J'ai vérifié
et relu les résultats et les documents.
