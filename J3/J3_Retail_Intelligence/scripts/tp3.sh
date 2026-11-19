#!/usr/bin/env bash
# Lance une commande dans l'environnement du TP J3 et filtre les avertissements de démarrage de Spark.
# Usage : bash scripts/tp3.sh python transformations/01_bronze.py
set -o pipefail
source "$(dirname "${BASH_SOURCE[0]}")/env_tp3.sh"
cd "$TP3_DIR" || exit 1
"$@" 2>&1 | grep -vE "WARN NativeCodeLoader|Setting default log level|To adjust logging level|WARN Utils: (Your hostname|Set SPARK_LOCAL_IP)|WARN SparkStringUtils"
