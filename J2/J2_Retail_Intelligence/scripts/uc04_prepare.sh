#!/usr/bin/env bash
# UC-04 – Préparation du test NiFi : dossiers locaux, destination HDFS distincte, copie de travail.
export HADOOP_HOME=/opt/hadoop JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
export PATH=$PATH:$HADOOP_HOME/bin
SRC="$HOME/tpcxbb_kit/data/store/store.dat"     # fichier réel du kit (12 lignes)
OUT="$(cd "$(dirname "$0")/../04_UC04_nifi/preuves" && pwd)/00_preparation.txt"
{
  echo "### Préparation UC-04 – $(date '+%F %T')"
  ls -ld /data/nifi/input /data/nifi/archive /data/nifi/error
  hdfs dfs -mkdir -p /retail-lake/raw/nifi && hdfs dfs -ls -d /retail-lake/raw/nifi
  if [ -z "$(ls -A /data/nifi/input)" ]; then
    cp -p "$SRC" /data/nifi/input/ && echo "Copie de travail placée : $SRC -> /data/nifi/input/"
  else
    echo "/data/nifi/input n'est pas vide, aucune copie ajoutée :"; ls -l /data/nifi/input
  fi
  ls -l /data/nifi/input
  md5sum "$SRC" /data/nifi/input/store.dat
  echo "Utilisateur qui exécute NiFi : $(ps -o user= -p $(pgrep -f org.apache.nifi.NiFi | head -1))"
} 2>&1 | tee "$OUT"
