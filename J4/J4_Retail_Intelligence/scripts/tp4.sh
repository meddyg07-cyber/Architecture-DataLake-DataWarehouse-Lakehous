#!/usr/bin/env bash
# Lance une commande dans l'environnement du TP J4 et filtre les avertissements de démarrage de Spark.
# Usage : bash scripts/tp4.sh python analytics/scripts/kpi.py
set -o pipefail
source "$(dirname "${BASH_SOURCE[0]}")/env_tp4.sh"
cd "$TP4_DIR" || exit 1
"$@" 2>&1 | grep -vE "WARN NativeCodeLoader|Setting default log level|To adjust logging level|WARN Utils: (Your hostname|Set SPARK_LOCAL_IP)|WARN SparkStringUtils|incubator modules|log4j2-defaults"
