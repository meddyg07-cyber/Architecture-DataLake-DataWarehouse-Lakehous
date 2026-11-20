#!/usr/bin/env bash
# Environnement du TP J4, à charger dans Ubuntu (WSL) : source scripts/env_tp4.sh
# Réutilise l'environnement du TP3 (consigne §1.2) : même venv, même Java 17 que HDFS, même Spark embarqué.
export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
export HADOOP_HOME=/opt/hadoop
export HADOOP_CONF_DIR=/opt/hadoop/etc/hadoop
export PATH="$JAVA_HOME/bin:$PATH:/opt/hadoop/bin:/opt/hadoop/sbin"
export TP4_VENV="$HOME/retail-intelligence/tp3/.venv"
export TP4_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PYSPARK_PYTHON="$TP4_VENV/bin/python"
# shellcheck disable=SC1091
source "$TP4_VENV/bin/activate"
