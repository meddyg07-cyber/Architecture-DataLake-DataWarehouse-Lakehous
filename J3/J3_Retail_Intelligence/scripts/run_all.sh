#!/usr/bin/env bash
# Chaîne complète du TP J3 (UC-06), dans l'ordre d'exécution. Chaque étape écrit son journal dans preuves/logs/.
# Prérequis : HDFS démarré (bash ../../J2/J2_Retail_Intelligence/scripts/start_env.sh) et venv installé (README).
# Usage (Ubuntu) : bash scripts/run_all.sh
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/env_tp3.sh"
cd "$TP3_DIR"
mkdir -p preuves/logs

ONLY="${*:-}"   # bash scripts/run_all.sh 05_qualite 08_hdfs_sorties -> ne relance que ces étapes
etape () {   # etape <journal> <commande...>
  if [ -n "$ONLY" ] && [[ " $ONLY " != *" $1 "* ]]; then return 0; fi
  local log="preuves/logs/$1.log"; shift
  echo "=== $(date '+%d/%m/%Y %H:%M:%S') | $* ===" | tee "$log"
  "$@" 2>&1 | grep -vE "WARN NativeCodeLoader|Setting default log level|To adjust logging level|WARN Utils: (Your hostname|Set SPARK_LOCAL_IP)|incubator modules|log4j2-defaults" | tee -a "$log"
  echo "=== fin $(date '+%H:%M:%S') ===" | tee -a "$log"
}

hdfs dfsadmin -report 2>/dev/null | grep -q "Live datanodes (1)" || { echo "HDFS n'est pas démarré"; exit 1; }
etape 00_environnement bash -c 'python --version; java -version 2>&1 | head -1; python -m pip show pyspark jupyterlab 2>/dev/null | grep -E "^(Name|Version)"; hdfs version | head -1; nproc; free -h | head -2'
etape 01_test_spark      python scripts/test_spark.py
etape 02_bronze          python transformations/01_bronze.py
etape 03_silver          python transformations/02_silver.py
etape 04_gold            python transformations/03_gold.py
etape 05_qualite         python transformations/04_qualite.py
etape 06_formats         python transformations/05_formats.py
etape 07_tests_regles    python tests/test_regles_silver.py
etape 08_hdfs_sorties    bash -c 'hdfs dfs -ls -R /retail-lake/bronze /retail-lake/silver /retail-lake/gold /retail-lake/quality | grep -v "_SUCCESS" ; hdfs dfs -du -h /retail-lake/bronze/tpcxbb /retail-lake/silver/tpcxbb /retail-lake/gold/retail'
echo "Chaîne terminée : journaux dans preuves/logs/"
