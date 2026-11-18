#!/usr/bin/env bash
# Affiche, étape par étape, les commandes UC-03 à capturer (Win + Maj + S).
# Usage : bash captures_terminal_uc03.sh      (agrandir la fenêtre du terminal avant)
export HADOOP_HOME=/opt/hadoop JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
export PATH=$PATH:$HADOOP_HOME/bin:$HADOOP_HOME/sbin
export PREUVES="$(cd "$(dirname "$0")/../03_UC03_hdfs/preuves" && pwd)"
B='\033[1;36m'; G='\033[1;32m'; N='\033[0m'

ecran() {   # ecran "titre" commande1 commande2 ...
  clear
  echo -e "${B}==== $1 ====${N}"
  echo -e "${B}$(date '+%d/%m/%Y %H:%M:%S') · $(whoami)@$(hostname) · Ubuntu (WSL2)${N}\n"
  shift
  for c in "$@"; do echo -e "${G}\$ $c${N}"; bash -c "$c" 2>&1; echo; done
  read -rp "📸 Capture d'écran, puis Entrée pour la suite..." _
}

ecran "CAPTURE 1 – Étape 1 : versions" \
  "grep PRETTY_NAME /etc/os-release" \
  "hadoop version | head -1" \
  "readlink -f /proc/\$(jps | awk '\$2==\"NameNode\"{print \$1}')/exe   # Java utilisé par le NameNode" \
  "jps"

ecran "CAPTURE 2 – Étape 1 : état de HDFS" \
  "hdfs dfsadmin -report | sed -n '1,5p;/Live datanodes/,/DFS Remaining%/p'"

ecran "CAPTURE 3 – Étape 2 : commandes HDFS" \
  "hdfs dfsadmin -safemode get" \
  "hdfs dfs -ls /" \
  "hdfs dfs -ls -d /retail-lake" \
  "hdfs dfs -du -h -s /retail-lake" \
  "hdfs dfs -ls /repertoire-inexistant   # erreur volontaire"

ecran "CAPTURE 4 – Étape 3 : arborescence du Data Lake" \
  "hdfs dfs -ls -R /retail-lake | grep '^d' | grep -v 'tpcxbb/initial/\|tpcxbb/refresh/'"

ecran "CAPTURE 5 – Étape 4 : source locale avant dépôt" \
  "ls -l ~/tpcxbb_kit/data/store_sales/" \
  "head -2 ~/tpcxbb_kit/data/store_sales/store_sales.dat | cut -c1-150" \
  "wc -l ~/tpcxbb_kit/data/store_sales/store_sales.dat"

ecran "CAPTURE 6 – Étape 4 : dépôt dans HDFS" \
  "hdfs dfs -count -h /retail-lake/raw/tpcxbb/initial /retail-lake/raw/tpcxbb/refresh" \
  "hdfs dfs -ls -h /retail-lake/raw/tpcxbb/initial/store_sales /retail-lake/raw/tpcxbb/initial/inventory"

ecran "CAPTURE 7 – Étape 5 : lecture, permissions et blocs" \
  "hdfs dfs -cat /retail-lake/raw/tpcxbb/initial/store/store.dat | head -2 | cut -c1-150" \
  "hdfs dfs -ls /retail-lake/raw/tpcxbb/initial/store" \
  "hdfs fsck /retail-lake/raw/tpcxbb/initial/inventory -files -blocks | grep -E 'inventory.dat|Status'"

ecran "CAPTURE 8 – Étape 5 : intégrité (source locale vs HDFS)" \
  "md5sum ~/tpcxbb_kit/data/store_sales/store_sales.dat" \
  "hdfs dfs -cat /retail-lake/raw/tpcxbb/initial/store_sales/store_sales.dat | md5sum" \
  "cut -d';' -f6 \"\$PREUVES/05_controle_integrite_md5.csv\" | tail -n +2 | sort | uniq -c   # 34 fichiers contrôlés"

clear; echo "Terminé : 8 captures."
