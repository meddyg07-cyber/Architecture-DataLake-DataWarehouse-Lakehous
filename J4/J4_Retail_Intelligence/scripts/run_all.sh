#!/usr/bin/env bash
# Chaîne complète du TP J4 (UC-08 puis UC-07 parcours B). Chaque étape écrit son journal dans preuves/logs/.
# Prérequis : HDFS démarré, Silver et Gold du J3 présents, venv du TP3 complété (README, §Reproduction).
# Usage (Ubuntu) : bash scripts/run_all.sh            # tout
#                  bash scripts/run_all.sh 04_uc07_demo_hdfs   # une seule étape
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/env_tp4.sh"
cd "$TP4_DIR"
mkdir -p preuves/logs

ONLY="${*:-}"
etape () {   # etape <journal> <commande...>
  if [ -n "$ONLY" ] && [[ " $ONLY " != *" $1 "* ]]; then return 0; fi
  local log="preuves/logs/$1.log"; shift
  echo "=== $(date '+%d/%m/%Y %H:%M:%S') | $* ===" | tee "$log"
  "$@" 2>&1 | grep -vE "WARN NativeCodeLoader|Setting default log level|To adjust logging level|WARN Utils: (Your hostname|Set SPARK_LOCAL_IP)|incubator modules|log4j2-defaults|Kernel is running over TCP|JavaUtils|^\s+at |java.io.IOException: Failed to delete" | tee -a "$log"
  echo "=== fin $(date '+%H:%M:%S') ===" | tee -a "$log"
}

hdfs dfsadmin -report 2>/dev/null | grep -q "Live datanodes (1)" || { echo "HDFS n'est pas démarré"; exit 1; }
etape 00_environnement bash -c 'python --version; java -version 2>&1 | head -1; python -m pip list 2>/dev/null | grep -iE "^(pyspark|pandas|matplotlib|pyarrow|openpyxl|jupyterlab|ipykernel) "; jupyter kernelspec list; hdfs version | head -1; nproc; free -h | head -2'
etape 01_notebook_uc08 jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.kernel_name=retail-tp4 --ExecutePreprocessor.timeout=1800 analytics/notebooks/TP4_Retail_Intelligence.ipynb
etape 02_kpi_cli       python analytics/scripts/kpi_retail.py --axes annee --annees 2001-2005 --sortie analytics/outputs/kpi_cli.csv
etape 03_test_kpi_cli  python tests/test_kpi_cli.py
etape 04_kpi_cli_periode_egale python analytics/scripts/kpi_retail.py --axes annee,categorie --annees 2004-2005 --periode-egale --sortie analytics/outputs/kpi_categorie_2004_2005_periode_egale.csv
etape 05_uc07_demo_hdfs bash scripts/uc07_demo_hdfs.sh
etape 06_hdfs_zones_projet bash -c 'hdfs dfs -ls /retail-lake /retail-lake/*/ | grep -v "^Found"; hdfs dfs -du -s -h "/retail-lake/*"'
echo "Chaîne terminée : journaux dans preuves/logs/"
