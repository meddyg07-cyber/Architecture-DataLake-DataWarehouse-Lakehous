# J4 – Retail Intelligence Platform

TP Jour 4 : **UC-08**, analyse décisionnelle et visualisation, et **UC-07**, transposition de la plateforme vers
Azure. IPSSI, Mastère Data & IA.

**Parcours retenu : B (local / open source).** Aucune ressource Azure n'a été créée.

**UC-08** a été **réellement exécuté** le 19/11/2026 sur les jeux Silver et Gold du J3, lus dans HDFS. Résultats :
- 7 KPI, réconciliés au centime avec le J1 ;
- des statistiques descriptives ;
- 3 analyses métier et 4 visualisations ;
- des constats et des recommandations.

**UC-07** se compose :
- d'une architecture Azure **étudiée** ;
- d'un déploiement ADLS **simulé** (commandes écrites, non exécutées) ;
- d'une démonstration **réelle** sur HDFS des zones, du HNS et des ACL (16 tests sur 16 conformes).

> Données **synthétiques** TPCx-BB, canal magasin. Les constats valident une démarche, pas une réalité commerciale.

## Livrables

| Code | Livrable du sujet | Fichier |
|---|---|---|
| J4-01 | Inventaire analytique | `docs/analytics/inventaire-analytique.md`, `analytics/outputs/inventaire_jeux.csv` |
| J4-02 | Dictionnaire des KPI | `docs/analytics/kpi-dictionary.md`. Formules : `analytics/scripts/kpi_retail.py` |
| J4-03 | Analyses statistiques | `docs/analytics/business-analysis.md` §1, `analytics/outputs/statistiques.csv`, `kpi.csv` |
| J4-04 | Analyses métier | `docs/analytics/business-analysis.md` §2 à §4 (Q1, Q3, Q5), `analytics/outputs/analyse*.csv` |
| J4-05 | Visualisations | `analytics/visualizations/` : 4 PNG commentés |
| J4-06 | Synthèse décisionnelle | `docs/analytics/interpretation.md` |
| J4-07 | Architecture Azure | `docs/cloud/azure-architecture.md`, `azure/architecture/schema_architecture.svg` (et `.png`) |
| J4-08 | Organisation ADLS Gen2 | `docs/cloud/adls-organization.md` (zones, chemins, conventions, HNS) |
| J4-09 | Sécurité | `docs/cloud/security-matrix.md` |
| J4-10 | Preuves Azure | `azure/simulation/dossier_simulation.md` (simulation **documentée**) + preuves locales `preuves/` |
| J4-11 | README J4 | ce fichier |
| – | Notebook | `analytics/notebooks/TP4_Retail_Intelligence.ipynb` (exécuté, sorties et graphiques conservés) |
| – | Questions de recul | `J4_questions_de_recul.md` |
| – | Complémentaire et avancé (facultatif) | CO-05 (gouvernance, `security-matrix.md` §5) ; AV-01 (`kpi_retail.py` paramétré et testé) ; AV-02 (transposition, `azure-architecture.md` §5). Étudiés, sans déploiement |

## Réalisé, simulé, étudié

| Statut | Éléments |
|---|---|
| **Exécuté** (preuves dans `preuves/`) | Notebook UC-08 ; KPI en ligne de commande et test de reproductibilité ; démonstration HDFS (zones, renommage de répertoire, ACL, 16 tests de droits) |
| **Simulé** (non exécuté) | Création d'ADLS Gen2, dépôt de fichier, RBAC et ACL Azure, suppression : `azure/simulation/deploiement_adls_simulation.sh`, bloqué par `exit 1` |
| **Étudié** | ADF, Synapse (Studio, Spark pools, SQL serverless), Power BI, Key Vault ; Airflow, MinIO, Iceberg, Trino, Superset |

## Versions observées (`preuves/logs/00_environnement.log`)

Environnement du TP3 **réutilisé** (§1.2 du sujet). Seules les bibliothèques de visualisation ont été ajoutées.

| Composant | Version |
|---|---|
| Ubuntu 24.04 sous WSL 2 | 12 cœurs, 7,6 Gio de RAM |
| Python | 3.12.3, venv `~/retail-intelligence/tp3/.venv` |
| PySpark / Spark | 4.3.0, mode local `local[*]` |
| Java | OpenJDK 17.0.21 |
| Hadoop HDFS | 3.5.0, `hdfs://localhost:9000` (ACL activées) |
| Pandas | 2.3.3 (pandas 3 est signalé « non pleinement supporté » par PySpark, voir l'erreur n° 1) |
| Matplotlib | 3.11.2 |
| PyArrow / openpyxl | 26.0.1 / 3.1.5 |
| JupyterLab / noyau | 4.6.6 / « Python - Retail TP4 » (`retail-tp4`) |

## Reproduire

Toutes les commandes se lancent **dans Ubuntu (WSL)**, depuis `J4/J4_Retail_Intelligence/`. Prérequis : HDFS démarré,
et les zones Silver et Gold du J3 présentes (`bash ../../J3/J3_Retail_Intelligence/scripts/run_all.sh`).

**1. Compléter le venv du TP3 (une seule fois)**
```bash
source ~/retail-intelligence/tp3/.venv/bin/activate
python -m pip install "pandas<3" matplotlib pyarrow openpyxl
python -m ipykernel install --user --name retail-tp4 --display-name "Python - Retail TP4"
```

**2. Exécuter**
```bash
bash scripts/run_all.sh                         # toute la chaîne (environ 4 min), journaux dans preuves/logs/
bash scripts/run_all.sh 05_uc07_demo_hdfs       # ou une seule étape
bash scripts/tp4.sh python analytics/scripts/kpi_retail.py --axes annee,magasin --annees 2001-2004   # KPI à la demande
bash scripts/tp4.sh jupyter lab                 # ouvrir le notebook dans JupyterLab
hdfs dfs -rm -r -skipTrash /retail-intelligence-demo                 # supprimer le bac à sable UC-07
```

| # | Étape (`run_all.sh`) | Entrée | Sortie | Contrôle intégré |
|---|---|---|---|---|
| 00 | `00_environnement` | – | versions | – |
| 01 | `01_notebook_uc08` : notebook exécuté avec `nbconvert` | Silver, Gold (HDFS), rapport qualité du J3, dictionnaire du J1 | `analytics/outputs/*.csv`, `analytics/visualizations/*.png` | Unicité des grains ; **J1 = J4** (39 valeurs) ; **Gold = Silver** ; arrêt en cas d'écart |
| 02 | `02_kpi_cli` : `kpi_retail.py` | Silver | `kpi_cli.csv` | – |
| 03 | `03_test_kpi_cli` | `kpi.csv`, `kpi_cli.csv` | – | Notebook = ligne de commande (40 valeurs) |
| 04 | `04_kpi_cli_periode_egale` | Silver | `kpi_categorie_2004_2005_periode_egale.csv` | Exemple de paramétrage |
| 05 | `05_uc07_demo_hdfs` : `uc07_demo_hdfs.sh` | Échantillons copiés de `/retail-lake` | Bac à sable `/retail-intelligence-demo` | 16 tests de droits, arrêt si non conforme |
| 06 | `06_hdfs_zones_projet` | – | Arborescence réelle `/retail-lake` | – |

## Résultats principaux

- **KPI 2004 (canal magasin)** : CA net payé 234,3 M$ ; 18 039 transactions ; panier moyen de 12 991 $ ; remise de
  50,0 %. Évolution 2005 : −6,48 % sur l'année, mais **−1,53 % à période égale**.
- **Q1** : activité stable et **sans saisonnalité**. L'indice mensuel, ramené au nombre de jours, varie de 98,8 à 101,0.
- **Q3** : Music et Books font **72 % du CA**, en proportion de leur catalogue. 6,1 % des produits font 50 % du CA.
- **Q5** : magasins homogènes (CV de 1,67 %), classement instable. Seul Buffalo (KS) est durablement 1er (+4,1 %),
  grâce à son nombre de transactions.

## Limites connues

- Données **synthétiques**. Les niveaux absolus (panier de 12 900 $, 372 articles par ticket) sont irréalistes : seules
  les comparaisons relatives ont un sens.
- Canal web, retours, stocks, marge et profils clients ne sont **pas analysés**, faute de tables en Silver
  (`kpi-dictionary.md` §3).
- **Aucune exécution Azure** : coûts, performances et RBAC restent théoriques.
- La démonstration HDFS prouve le modèle des zones et des ACL, mais l'authentification y est `simple` : l'identité est
  déclarée, pas prouvée (démontré et documenté).
- Spark local sur un seul poste : ce n'est pas un cluster.

## Erreurs rencontrées et corrections

| # | Erreur | Cause | Correction |
|---|---|---|---|
| 1 | `FutureWarning: PySpark does not yet fully support pandas >= 3.0.0` | `pip install pandas` a installé pandas 3.1 | `pip install "pandas<3"` (2.3.3) |
| 2 | Graphiques absents du notebook (`FigureCanvasAgg is non-interactive`), alors que les PNG étaient bien créés | `MPLBACKEND=Agg` dans `env_tp4.sh` forçait un rendu sans affichage, même dans le noyau Jupyter | Variable retirée ; `%matplotlib inline` en tête du notebook |
| 3 | Étiquette d'axe illisible sur l'histogramme (« ( ), tranchesde2000 ») | Matplotlib interprète le texte entre deux `$` comme une formule mathématique | `text.parse_math = False` : « $ » reste le symbole du dollar |
| 4 | `TypeError: unsupported operand type(s) for -: 'float' and 'str'` dans `test_kpi_cli.py` | La ligne de commande exportait les `decimal` Spark avec un point, alors que le CSV est lu avec une virgule décimale | Conversion des décimaux en `float` avant l'export. **Défaut réel trouvé par le test de reproductibilité** |
| 5 | `set: pipefail: invalid option name` et `$'\r': command not found` | Fins de ligne Windows (CRLF) introduites en modifiant le script depuis Windows | Fichiers repassés en LF (`sed -i 's/\r$//'`) |
| 6 | Démonstration UC-07 : une exécution a duré 1 heure | Le NameNode n'a reçu aucune requête de 12:54 à 13:54 : WSL était suspendu (mise en veille du poste), le script n'était pas en cause | Relance : 2 min 30. Chaque section du journal est désormais horodatée |
| 7 | Première version de la matrice : le Bronze donné à l'ingestion, comme dans l'exemple du sujet | Notre ingestion (NiFi) écrit en **Raw** ; c'est Spark qui écrit le Bronze | Zone Raw ajoutée à la démonstration ; matrice et tests alignés sur l'architecture réelle |
| 8 | Texte des cellules Markdown du notebook illisible (« Lemontantnetpayé… » en italique mathématique) | JupyterLab traite le texte entre deux `$` comme une formule (MathJax). `\$` et `&#36;` ne suffisent pas : MathJax passe **après** le rendu Markdown | 4 variantes testées dans JupyterLab : seul `\\$` s'affiche « $ ». Appliqué automatiquement à toutes les cellules Markdown |

## Preuves

- `preuves/logs/` : un journal par étape de `run_all.sh`, horodaté.
- `preuves/captures/` : **20 captures** (Edge piloté par script, bandeau avec la date et l'URL, jamais le jeton
  JupyterLab). `uc08_*` pour UC-08, `uc07_*` pour UC-07. Chacune est intégrée et légendée dans le document qu'elle
  prouve.
- `analytics/outputs/` : tous les résultats chiffrés en CSV, plus `resume_uc08.json`.

## Usage de l'IA

Code, exécution et rédaction réalisés avec l'assistance de Claude (Anthropic). Toutes les commandes ont été réellement
exécutées sur mon poste. Les chiffres des documents proviennent des sorties enregistrées dans `analytics/outputs/` et
`preuves/`. J'ai vérifié et relu les résultats et les documents. La partie Azure est une **simulation**, signalée comme
telle partout.
