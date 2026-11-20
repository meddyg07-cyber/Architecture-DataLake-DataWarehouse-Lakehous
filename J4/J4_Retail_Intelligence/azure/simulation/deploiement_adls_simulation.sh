#!/usr/bin/env bash
# =====================================================================================================================
#  SIMULATION — CE SCRIPT N'A PAS ÉTÉ EXÉCUTÉ.  Parcours B : aucune ressource Azure n'a été créée pendant le TP J4.
#  Il documente les opérations qui SERAIENT faites en parcours A, dans l'ordre, avec les contrôles associés.
#  Prérequis d'une exécution réelle : accord du formateur, abonnement autorisé, budget défini, Azure CLI connectée
#  (az login). AUCUN secret dans ce fichier : les valeurs viennent de azure/configuration/parametres.env (non versionné).
# =====================================================================================================================
echo "Simulation documentaire : script volontairement bloqué (voir azure/simulation/dossier_simulation.md)."; exit 1

set -euo pipefail
source "$(dirname "$0")/../configuration/parametres.env"     # ABONNEMENT, REGION, RG, COMPTE, CONTENEUR, groupes Entra ID

# --- 0. Contexte et garde-fous de coût -------------------------------------------------------------------------------
az account set --subscription "$ABONNEMENT"
az account show --query "{abonnement:name, etat:state}" -o table               # contrôle : bon abonnement, état Enabled
az group create -n "$RG" -l "$REGION" --tags projet=retail-intelligence env=dev tp=J4
az consumption budget create --budget-name budget-retail-tp --amount "$BUDGET_EUR" --time-grain Monthly \
   --start-date "$DEBUT_MOIS" --end-date "$FIN_BUDGET" --resource-group "$RG"   # puis alertes à 50 % et 80 % (portail)

# --- 1. Compte de stockage ADLS Gen2 (HNS activé à la création) ---------------------------------------------------
az storage account create -n "$COMPTE" -g "$RG" -l "$REGION" \
   --kind StorageV2 --sku Standard_LRS --hns true \
   --min-tls-version TLS1_2 --allow-blob-public-access false --allow-shared-key-access false
az storage account show -n "$COMPTE" -g "$RG" --query "{kind:kind, hns:isHnsEnabled, sku:sku.name}" -o table
#    contrôle attendu : kind = StorageV2, hns = True, sku = Standard_LRS

# --- 2. Conteneur et zones -------------------------------------------------------------------------------------------
az storage fs create -n "$CONTENEUR" --account-name "$COMPTE" --auth-mode login
for z in raw/tpcxbb/initial bronze/tpcxbb silver/tpcxbb gold/retail gold/analyses quality/tpcxbb logs documentation; do
  az storage fs directory create -f "$CONTENEUR" -n "$z" --account-name "$COMPTE" --auth-mode login
done
az storage fs file list -f "$CONTENEUR" --account-name "$COMPTE" --auth-mode login --recursive -o table

# --- 3. Dépôt d'un fichier de démonstration (agrégé, non sensible) et vérification -----------------------------------
az storage fs file upload -f "$CONTENEUR" --account-name "$COMPTE" --auth-mode login \
   -s analytics/outputs/kpi.csv -p gold/analyses/kpi_annuels.csv
az storage fs file show -f "$CONTENEUR" --account-name "$COMPTE" --auth-mode login -p gold/analyses/kpi_annuels.csv \
   --query "{taille:contentLength, modifie:lastModified}" -o table          # contrôle : taille = celle du fichier local
az storage fs file download -f "$CONTENEUR" --account-name "$COMPTE" --auth-mode login \
   -p gold/analyses/kpi_annuels.csv -d /tmp/kpi_relu.csv && diff -q analytics/outputs/kpi.csv /tmp/kpi_relu.csv

# --- 4. Droits : RBAC minimal + ACL par zone (matrice docs/cloud/security-matrix.md) ----------------------------------
SCOPE=$(az storage account show -n "$COMPTE" -g "$RG" --query id -o tsv)
az role assignment create --assignee-object-id "$GRP_ADMINS" --assignee-principal-type Group \
   --role "Storage Blob Data Owner" --scope "$SCOPE/blobServices/default/containers/$CONTENEUR"
# Pas de rôle de données RBAC pour analystes / data eng : il ouvrirait tout le conteneur. Droits par ACL :
acl () { az storage fs access update-recursive -f "$CONTENEUR" -p "$1" --acl "$2" --account-name "$COMPTE" --auth-mode login; }
racine () { az storage fs access set -f "$CONTENEUR" -p "/" --acl "$1" --account-name "$COMPTE" --auth-mode login; }
racine "user::rwx,group::r-x,other::---,group:$GRP_INGESTION:--x,group:$GRP_DATAENG:--x,group:$GRP_ANALYSTES:--x"
acl raw     "group:$GRP_INGESTION:rwx,group:$GRP_DATAENG:r-x,default:group:$GRP_INGESTION:rwx,default:group:$GRP_DATAENG:r-x"
acl bronze  "group:$GRP_DATAENG:rwx,default:group:$GRP_DATAENG:rwx"
acl silver  "group:$GRP_DATAENG:rwx,default:group:$GRP_DATAENG:rwx"
acl gold    "group:$GRP_DATAENG:rwx,group:$GRP_ANALYSTES:r-x,default:group:$GRP_DATAENG:rwx,default:group:$GRP_ANALYSTES:r-x"
acl quality "group:$GRP_DATAENG:rwx,group:$GRP_ANALYSTES:r-x,default:group:$GRP_DATAENG:rwx,default:group:$GRP_ANALYSTES:r-x"
az storage fs access show -f "$CONTENEUR" -p gold --account-name "$COMPTE" --auth-mode login -o table
#    contrôles attendus : un compte analyste lit gold/analyses/kpi_annuels.csv, mais reçoit 403 sur raw/ et en écriture sur gold/

# --- 5. Journalisation des accès -------------------------------------------------------------------------------------
# az monitor diagnostic-settings create ... --logs StorageRead StorageWrite StorageDelete -> espace Log Analytics

# --- 6. Fin de TP : suppression de TOUT ce qui a été créé (arrêt des coûts) ------------------------------------------
az group delete -n "$RG" --yes --no-wait
az group exists -n "$RG"                                                       # contrôle final : false
