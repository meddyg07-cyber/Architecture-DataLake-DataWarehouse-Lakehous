#!/usr/bin/env bash
# UC-03 – Correction des permissions de la zone Raw (constat de l'étape 5).
# put -p a recopié les droits 777 que WSL attribue aux fichiers Windows (/mnt/c) → Raw modifiable par tous.
# Cible : dossiers 755, fichiers 444 (lecture seule : la zone Raw est immuable), groupe supergroup.
export HADOOP_HOME=/opt/hadoop JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64 PATH=$PATH:/opt/hadoop/bin
OUT="$(cd "$(dirname "$0")/../03_UC03_hdfs/preuves" && pwd)/06_correction_permissions.txt"
R=/retail-lake/raw/tpcxbb
run() { { echo "[$(date '+%F %T')] \$ $1"; bash -c "$1" 2>&1; echo "→ code retour : $?"; echo; } | tee -a "$OUT"; }
: > "$OUT"; echo "### Correction des permissions de la zone Raw – $(whoami)@$(hostname)" | tee -a "$OUT"; echo | tee -a "$OUT"
echo "## AVANT" | tee -a "$OUT"
run "hdfs dfs -ls $R/initial/store_sales $R/refresh/store_sales"
run "hdfs dfs -ls -R $R | grep -c '^-rwxrwxrwx'"
echo "## CORRECTION" | tee -a "$OUT"
run "hdfs dfs -chgrp -R supergroup $R"
run "hdfs dfs -chmod -R 755 $R"
run "hdfs dfs -chmod 444 '$R/*/*/*'"
echo "## APRÈS" | tee -a "$OUT"
run "hdfs dfs -ls $R/initial/store_sales $R/refresh/store_sales"
run "hdfs dfs -ls -R $R | awk '{print substr(\$1,1,1), \$1, \$4}' | sort | uniq -c"
run "hdfs dfs -ls -d $R $R/initial $R/initial/store_sales"
