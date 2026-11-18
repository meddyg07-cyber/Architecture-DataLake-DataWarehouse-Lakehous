#!/usr/bin/env bash
# UC-03 – Hadoop, HDFS et création du Data Lake (étapes 1 à 5).
# Chaque commande est journalisée (horodatage + commande + sortie + code retour) dans preuves/.
# Usage (Ubuntu/WSL) : bash uc03_hdfs.sh [etape]   etape = 1..5 ou "all" (défaut)
set -u
export HADOOP_HOME=/opt/hadoop HADOOP_CONF_DIR=/opt/hadoop/etc/hadoop
export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
export PATH=$PATH:$HADOOP_HOME/bin:$HADOOP_HOME/sbin

HERE="$(cd "$(dirname "$0")" && pwd)"
OUT="$HERE/../03_UC03_hdfs/preuves"
# Kit TPCx-BB fourni (jamais modifié). Hadoop refuse les chemins locaux contenant des espaces
# ("Data Lake Warehouse Lakehouse") → on passe par un lien symbolique sans espace.
KIT="$(cd "$HERE/../../../J1/retail_project/retail_project" && pwd)"
SRC="$HOME/tpcxbb_kit"
[ -L "$SRC" ] || ln -s "$KIT" "$SRC"
LAKE=/retail-lake
mkdir -p "$OUT"

LOG=""
run() {   # run "commande" : exécute et journalise dans $LOG
  {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] \$ $1"
    bash -c "$1" 2>&1
    echo "→ code retour : $?"
    echo
  } | tee -a "$LOG"
}
section() { LOG="$OUT/$1"; : > "$LOG"; echo "### $2 – $(date '+%Y-%m-%d %H:%M:%S') – utilisateur $(whoami)@$(hostname)" | tee -a "$LOG"; echo | tee -a "$LOG"; }

etape1() {
  section 01_environnement_hadoop.txt "Étape 1 – Vérification de l'environnement Hadoop"
  run "grep PRETTY_NAME /etc/os-release; uname -r"
  run "java -version"
  run "/usr/lib/jvm/java-21-openjdk-amd64/bin/java -version"
  run "hadoop version"
  run "python3 --version"
  run "echo HADOOP_HOME=\$HADOOP_HOME; echo HADOOP_CONF_DIR=\$HADOOP_CONF_DIR; echo JAVA_HOME=\$JAVA_HOME"
  run "cat \$HADOOP_CONF_DIR/core-site.xml"
  run "cat \$HADOOP_CONF_DIR/hdfs-site.xml"
  run "jps"
  run "hdfs dfsadmin -report"
  run "hdfs getconf -confKey dfs.blocksize; hdfs getconf -confKey dfs.replication; hdfs getconf -namenodes"
  run "ss -ltn | grep -E ':9000|:9870|:9864|:8443'"
  run "grep -hE ' (ERROR|FATAL) ' \$HADOOP_HOME/logs/*.log | tail -5 || echo 'Aucune erreur dans les journaux Hadoop'"
}

etape2() {
  section 02_commandes_hdfs.txt "Étape 2 – Découverte des commandes HDFS"
  run "hdfs dfsadmin -safemode get"                       # 1. état du système
  run "hdfs dfsadmin -report -live | head -25"            # 2. informations sur les nœuds
  run "hdfs dfs -ls /"                                    # 3. répertoires disponibles
  run "hdfs dfs -mkdir -p $LAKE"                          # 4. répertoire de travail
  run "hdfs dfs -ls -d $LAKE"                             # 5. permissions
  run "hdfs dfs -du -h -s $LAKE"                          # 6. taille
  run "hdfs dfs -ls /repertoire-inexistant"               # erreur volontaire documentée
}

etape3() {
  section 03_arborescence_datalake.txt "Étape 3 – Création de l'arborescence du Data Lake"
  for d in raw/tpcxbb/initial raw/tpcxbb/refresh raw/nifi bronze/tpcxbb silver gold quality logs; do
    run "hdfs dfs -mkdir -p $LAKE/$d"
  done
  run "hdfs dfs -ls -R $LAKE"
}

etape4() {
  section 04_depot_tpcxbb.txt "Étape 4 – Dépôt des données TPCx-BB"
  run "ls -la '$SRC' '$SRC/'"
  run "du -sh '$SRC/data' '$SRC/data_refresh'"
  run "find '$SRC/data' '$SRC/data_refresh' -type d -empty"
  # Inspection avant dépôt : taille, lignes, nb de colonnes (séparateur |), 1re ligne
  {
    echo "lot;table;fichier;format;taille_octets;lignes;colonnes;lisible"
    for f in $(cd "$SRC" && find data data_refresh -type f | sort); do
      p="$SRC/$f"; lot=${f%%/*}; t=$(basename "$(dirname "$f")")
      ext=${f##*.}
      if [ "$ext" = "dat" ]; then cols=$(head -1 "$p" | awk -F'|' '{print NF}'); else cols=$(head -1 "$p" | awk -F',' '{print NF}'); fi
      [ -r "$p" ] && lis=oui || lis=non
      echo "$lot;$t;$(basename "$f");$ext;$(stat -c %s "$p");$(wc -l < "$p");$cols;$lis"
    done
  } > "$OUT/04_inventaire_avant_depot.csv"
  run "column -s';' -t '$OUT/04_inventaire_avant_depot.csv'"
  # Dépôt : 1 sous-répertoire par table, le lot initial dans initial/, le lot refresh dans refresh/
  # (-p conserve dates et permissions ; pas de -f : un fichier existant n'est jamais écrasé)
  for lot in data:initial data_refresh:refresh; do
    l=${lot%%:*}; dest=$LAKE/raw/tpcxbb/${lot##*:}
    for t in $(cd "$SRC/$l" && ls); do
      [ -z "$(ls -A "$SRC/$l/$t")" ] && { echo "[$(date '+%F %T')] $l/$t vide : non déposé" | tee -a "$LOG"; continue; }
      run "hdfs dfs -mkdir -p $dest/$t && hdfs dfs -put -p '$SRC/$l/$t/'* $dest/$t/"
    done
  done
  run "hdfs dfs -ls -R -h $LAKE/raw/tpcxbb"
}

etape5() {
  section 05_verification_stockage.txt "Étape 5 – Vérification du stockage"
  run "hdfs dfs -ls $LAKE $LAKE/raw $LAKE/raw/tpcxbb"           # répertoires attendus
  run "hdfs dfs -count -h $LAKE/raw/tpcxbb/initial $LAKE/raw/tpcxbb/refresh"
  run "hdfs dfs -du -h $LAKE/raw/tpcxbb/initial $LAKE/raw/tpcxbb/refresh"
  run "hdfs dfs -ls $LAKE/raw/tpcxbb/initial/store"                # permissions
  run "hdfs dfs -cat $LAKE/raw/tpcxbb/initial/store/store.dat | head -3"   # lecture
  run "hdfs dfs -get $LAKE/raw/tpcxbb/initial/store/store.dat /tmp/store_recupere.dat && cmp /tmp/store_recupere.dat '$SRC/data/store/store.dat' && echo 'Fichier récupéré identique à la source'"
  run "hdfs fsck $LAKE/raw/tpcxbb -files -blocks | grep -E 'store_sales.dat|Total|Status|replicated'"
  # Intégrité : MD5 local vs MD5 du contenu relu depuis HDFS, + taille, pour chaque fichier
  {
    echo "fichier_hdfs;taille_locale;taille_hdfs;md5_local;md5_hdfs;resultat"
    for lot in data:initial data_refresh:refresh; do
      l=${lot%%:*}; dest=$LAKE/raw/tpcxbb/${lot##*:}
      for p in $(cd "$SRC/$l" && find . -type f | sort); do
        p=${p#./}; h="$dest/$p"
        sl=$(stat -c %s "$SRC/$l/$p"); sh=$(hdfs dfs -stat %b "$h")
        ml=$(md5sum < "$SRC/$l/$p" | cut -d' ' -f1); mh=$(hdfs dfs -cat "$h" | md5sum | cut -d' ' -f1)
        [ "$sl" = "$sh" ] && [ "$ml" = "$mh" ] && r=OK || r=KO
        echo "$h;$sl;$sh;$ml;$mh;$r"
      done
    done
  } > "$OUT/05_controle_integrite_md5.csv"
  run "column -s';' -t '$OUT/05_controle_integrite_md5.csv'"
  run "grep -c ';OK\$' '$OUT/05_controle_integrite_md5.csv'; grep ';KO\$' '$OUT/05_controle_integrite_md5.csv' || echo 'Aucun écart'"
  run "ls -la '$SRC/data/store_sales/'"   # la source originale est conservée
}

case "${1:-all}" in
  1) etape1;; 2) etape2;; 3) etape3;; 4) etape4;; 5) etape5;;
  all) etape1; etape2; etape3; etape4; etape5;;
esac
