#!/usr/bin/env bash
# UC-07, parcours B (local) : démonstration RÉELLE, sur HDFS, des notions étudiées pour ADLS Gen2.
#   - organisation des zones dans un espace de noms hiérarchique (équivalent du conteneur ADLS) ;
#   - opérations sur les répertoires (renommage atomique : ce qu'apporte le HNS) ;
#   - ACL POSIX par répertoire, avec ACL par défaut (même modèle que les ACL ADLS Gen2) ;
#   - tests de la matrice de droits avec plusieurs identités ;
#   - limite : authentification « simple » en local (pas d'Entra ID, pas de Kerberos).
# Bac à sable isolé : /retail-intelligence-demo. Les zones réelles /retail-lake ne sont PAS modifiées
# (le Raw n'est que lu, par une copie de store.dat).
# Usage (Ubuntu) : bash scripts/tp4.sh bash scripts/uc07_demo_hdfs.sh
# Nettoyage : hdfs dfs -rm -r -skipTrash /retail-intelligence-demo
set -uo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/env_tp4.sh"
cd "$TP4_DIR" || exit 1

D=/retail-intelligence-demo          # = conteneur ADLS « retail-intelligence »
ADMIN=$(whoami)                      # a démarré le NameNode : super-utilisateur HDFS
titre () { echo; echo "================ $* ($(date +%H:%M:%S)) ================"; }
ok=0; ko=0
defaut () {  # defaut <répertoire> <entrées> : ACL par défaut (héritée par les nouveaux fichiers) sur le répertoire et ses sous-répertoires
  for d in $1 $(hdfs dfs -ls -R "$1" | awk '$1 ~ /^d/ {print $NF}'); do hdfs dfs -setfacl -m "$2" "$d"; done
}
essai () {   # essai <identité> <attendu: AUTORISE|REFUSE> <description> <commande hdfs...>
  local id=$1 attendu=$2 desc=$3; shift 3
  if HADOOP_USER_NAME=$id "$@" >/tmp/uc07_out 2>&1; then obtenu=AUTORISE; else obtenu=REFUSE; fi
  local verdict="CONFORME"; [ "$obtenu" = "$attendu" ] && ok=$((ok+1)) || { verdict="NON CONFORME"; ko=$((ko+1)); }
  printf "%-14s | %-48s | attendu %-8s | obtenu %-8s | %s\n" "$id" "$desc" "$attendu" "$obtenu" "$verdict"
  [ "$obtenu" = "REFUSE" ] && grep -o "Permission denied: [^,]*" /tmp/uc07_out | head -1 | sed 's/^/               -> /'
}

titre "0. Contexte"
echo "Date : $(date '+%d/%m/%Y %H:%M:%S') | administrateur HDFS : $ADMIN"
echo "hadoop.security.authentication = $(hdfs getconf -confKey hadoop.security.authentication)"
echo "dfs.permissions.enabled        = $(hdfs getconf -confKey dfs.permissions.enabled)"
echo "dfs.namenode.acls.enabled      = $(hdfs getconf -confKey dfs.namenode.acls.enabled)"
hdfs dfs -test -d $D && hdfs dfs -rm -r -skipTrash $D >/dev/null && echo "ancien bac à sable supprimé"

titre "1. Organisation des zones (équivalent du conteneur ADLS Gen2, mêmes chemins que /retail-lake)"
hdfs dfs -mkdir -p $D/raw/tpcxbb/initial/store $D/bronze/tpcxbb $D/silver/tpcxbb $D/gold/retail $D/gold/analyses                    $D/quality/tpcxbb/rapport_controles $D/documentation
# Copies d'échantillons réels (les zones /retail-lake ne sont que lues)
hdfs dfs -cp /retail-lake/raw/tpcxbb/initial/store/store.dat $D/raw/tpcxbb/initial/store/
hdfs dfs -cp /retail-lake/bronze/tpcxbb/store $D/bronze/tpcxbb/store
hdfs dfs -cp /retail-lake/silver/tpcxbb/store $D/silver/tpcxbb/store
hdfs dfs -cp /retail-lake/gold/retail/performance_magasin_annuelle $D/gold/retail/performance_magasin_annuelle
# Fichier de démonstration déposé depuis le poste : KPI agrégés, non sensibles
hdfs dfs -put -f analytics/outputs/kpi.csv $D/gold/analyses/kpi_annuels.csv
hdfs dfs -put -f ../../J3/J3_Retail_Intelligence/preuves/08_rapport_qualite.csv $D/quality/tpcxbb/rapport_controles/
echo "Zones raw/bronze/silver/gold/quality du projet Retail Intelligence. Démonstration TP J4 (UC-07, parcours B)."   | hdfs dfs -put -f - $D/documentation/LISEZMOI.txt
hdfs dfs -ls -R $D | grep -vE "_SUCCESS|\.crc" | awk '{print $1, $3, $8}'
echo "Vérification du fichier déposé (lecture) :"; hdfs dfs -cat $D/gold/analyses/kpi_annuels.csv | head -3 | cut -c1-110

titre "2. Espace de noms hiérarchique : opérations sur les répertoires"
hdfs dfs -mkdir -p $D/gold/_publication_en_cours
for f in a b c d e; do echo "lot $f" | hdfs dfs -put -f - $D/gold/_publication_en_cours/part-$f.csv; done
echo "Avant : $(hdfs dfs -count $D/gold/_publication_en_cours | awk '{print $2" fichier(s) dans "$4}')"
t0=$(date +%s%N); hdfs dfs -mv $D/gold/_publication_en_cours $D/gold/analyses_v2; t1=$(date +%s%N)
echo "Renommage du répertoire entier en UNE opération de métadonnées : $(( (t1-t0)/1000000 )) ms (lancement du client compris)"
echo "Après : $(hdfs dfs -count $D/gold/analyses_v2 | awk '{print $2" fichier(s) dans "$4}')"
hdfs dfs -test -d $D/gold/_publication_en_cours || echo "L'ancien chemin n'existe plus : aucun état intermédiaire visible."
echo "Taille par zone (opération sur un répertoire) :"; hdfs dfs -du -s -h "$D/*"

titre "3. Droits : POSIX + ACL (moindre privilège, matrice docs/cloud/security-matrix.md)"
# Bases : propriétaire = administrateur, aucun droit pour « others » dans les zones.
Z="$D/raw $D/bronze $D/silver $D/gold $D/quality"
hdfs dfs -chmod 750 $Z
hdfs dfs -chmod -R o-rwx $Z                                      # sous-dossiers et fichiers compris
hdfs dfs -chmod 755 $D $D/documentation
# Identités (en production : groupes Entra ID ; ici, utilisateurs nommés car le mode simple ne vérifie pas les groupes).
#   svc_ingestion : identité technique d'ingestion (NiFi au J2 ; identité managée ADF dans Azure) -> dépose en raw
#   data_eng      : équipe Data Engineering (traitements Spark ; identité managée Synapse)  -> écrit bronze, silver, gold
#   analyste      : analyste métier (UC-08)                                               -> lit gold et quality
hdfs dfs -setfacl -R -m user:svc_ingestion:rwx,user:data_eng:r-x $D/raw
defaut $D/raw default:user:svc_ingestion:rwx,default:user:data_eng:r-x
for z in bronze silver; do
  hdfs dfs -setfacl -R -m user:data_eng:rwx $D/$z
  defaut $D/$z default:user:data_eng:rwx
done
for z in gold quality; do
  hdfs dfs -setfacl -R -m user:data_eng:rwx,user:analyste:r-x $D/$z
  defaut $D/$z default:user:data_eng:rwx,default:user:analyste:r-x
done
for z in raw bronze silver gold; do echo "--- $z"; hdfs dfs -getfacl $D/$z | grep -vE "^# (owner|group)|^$"; done

titre "4. Tests de la matrice de droits (identités simulées par HADOOP_USER_NAME)"
printf "%-14s | %-48s | %-17s | %-15s | %s\n" "identité" "action" "attendu" "obtenu" "verdict"
essai svc_ingestion AUTORISE "déposer un nouveau fichier en raw"           hdfs dfs -put -f analytics/outputs/inventaire_jeux.csv $D/raw/tpcxbb/initial/store/
essai svc_ingestion REFUSE   "lire bronze"                                 hdfs dfs -ls $D/bronze
essai svc_ingestion REFUSE   "lire gold"                                   hdfs dfs -ls $D/gold
essai data_eng      AUTORISE "lire raw"                                    hdfs dfs -cat $D/raw/tpcxbb/initial/store/store.dat
essai data_eng      REFUSE   "écrire en raw (zone d'ingestion)"            hdfs dfs -put -f analytics/outputs/kpi.csv $D/raw/tpcxbb/initial/store/
essai data_eng      AUTORISE "écrire en bronze"                            hdfs dfs -put -f analytics/outputs/inventaire_jeux.csv $D/bronze/tpcxbb/
essai data_eng      AUTORISE "écrire en silver"                            hdfs dfs -put -f analytics/outputs/statistiques.csv $D/silver/tpcxbb/
essai data_eng      AUTORISE "publier en gold"                             hdfs dfs -put -f analytics/outputs/analyse2_categories.csv $D/gold/analyses/
essai analyste      AUTORISE "lire gold/analyses/kpi_annuels.csv"          hdfs dfs -cat $D/gold/analyses/kpi_annuels.csv
essai analyste      AUTORISE "lire un fichier publié ensuite (ACL héritée)" hdfs dfs -cat $D/gold/analyses/analyse2_categories.csv
essai analyste      AUTORISE "lire le rapport qualité"                     hdfs dfs -ls $D/quality/tpcxbb/rapport_controles
essai analyste      REFUSE   "écrire en gold"                              hdfs dfs -put -f analytics/outputs/kpi.csv $D/gold/analyses/copie.csv
essai analyste      REFUSE   "lire raw"                                    hdfs dfs -ls $D/raw
essai analyste      REFUSE   "lire bronze"                                 hdfs dfs -ls $D/bronze
essai analyste      REFUSE   "lire silver"                                 hdfs dfs -ls $D/silver
essai inconnu       REFUSE   "lire gold sans aucun droit"                  hdfs dfs -ls $D/gold
echo "Bilan : $ok conforme(s), $ko non conforme(s)"
echo "ACL héritée par le fichier publié par data_eng :"
hdfs dfs -getfacl $D/gold/analyses/analyse2_categories.csv | grep -vE "^$"

titre "5. Limite de sécurité du mode local"
echo "En mode 'simple', l'identité est DÉCLARÉE par le client, pas prouvée :"
essai $ADMIN        AUTORISE "n'importe qui se déclarant '$ADMIN' lit raw" hdfs dfs -ls $D/raw
echo "=> les ACL organisent les droits, mais sans authentification forte (Kerberos en local, Entra ID dans Azure),"
echo "   elles ne protègent pas contre un utilisateur malveillant. Limite documentée dans security-matrix.md."

titre "6. Correspondance des chemins local -> ADLS Gen2 (cible, non déployée)"
for p in raw/tpcxbb/initial/store/store.dat bronze/tpcxbb/store silver/tpcxbb/store gold/retail/performance_magasin_annuelle gold/analyses/kpi_annuels.csv; do
  printf "  hdfs://localhost:9000%-62s -> abfss://retail-intelligence@<compte>.dfs.core.windows.net/%s\n" "$D/$p" "$p"
done
[ "$ko" -eq 0 ]
