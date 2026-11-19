#!/usr/bin/env bash
# Environnement du TP J3, à charger dans Ubuntu (WSL) avant toute commande : source scripts/env_tp3.sh
# Spark tourne sous Java 17, comme Hadoop (Spark 4.x accepte Java 17 et 21 ; on garde la même JVM que HDFS).
export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
export HADOOP_HOME=/opt/hadoop
export HADOOP_CONF_DIR=/opt/hadoop/etc/hadoop
export PATH="$JAVA_HOME/bin:$PATH:/opt/hadoop/bin:/opt/hadoop/sbin"
export TP3_VENV="$HOME/retail-intelligence/tp3/.venv"
export TP3_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PYSPARK_PYTHON="$TP3_VENV/bin/python"
# shellcheck disable=SC1091
source "$TP3_VENV/bin/activate"
