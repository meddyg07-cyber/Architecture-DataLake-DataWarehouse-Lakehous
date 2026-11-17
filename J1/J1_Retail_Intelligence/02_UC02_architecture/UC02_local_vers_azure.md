# UC-02 – Architecture locale et cible Azure

<p class="meta">Retail Intelligence Platform · TP Jour 1 · 16/11/2026</p>

> Conception logique uniquement : rien n'est déployé à ce stade. Le déploiement Azure est prévu au Jour 4.

## 1. Correspondance local / cloud

| Couche | Local (Linux / Ubuntu) | Cible Azure |
|---|---|---|
| Stockage | HDFS | **ADLS Gen2** (espace de noms hiérarchique) |
| Ingestion | Apache NiFi | Azure Data Factory (étudié) |
| Traitement | Spark / PySpark | Spark sur Synapse ou Databricks (étudié) |
| Format | Parquet | Parquet (identique) |
| Requêtes | Spark SQL | Azure Synapse SQL (étudié) |
| Sécurité | Droits HDFS, comptes Linux | Microsoft Entra ID, RBAC, ACL |

## 2. Organisation ADLS Gen2

| Élément | Proposition |
|---|---|
| Compte de stockage | Un compte `stretailintel<env>` avec espace de noms hiérarchique activé (exigé pour ADLS Gen2) |
| Conteneurs | `bronze`, `silver`, `gold` (un par zone) |
| Organisation | `bronze/tpcxbb/<table>/lot=<lot>/ingest=<date>/` ; `silver/<table>/annee=/mois=/` ; `gold/<fait_ou_dim>/` |
| Identités | Microsoft Entra ID ; une identité managée pour Data Factory et Spark (pas de compte partagé) |
| RBAC | Rôle *Storage Blob Data Contributor* pour l'équipe Data ; *Storage Blob Data Reader* sur `gold` pour les métiers |
| ACL | Droits fins par dossier, par exemple dossier client de Silver réservé à l'équipe Data |
| Secrets | Azure Key Vault ; aucune clé ni mot de passe dans le code |
| Coûts et quotas | Niveau *Hot* pour Silver et Gold, *Cool* ou *Archive* pour les anciens lots Bronze ; alertes budgétaires ; environ 1 Go aujourd'hui, donc un coût de stockage très faible ; le coût principal vient du calcul Spark |

## 3. Comparaison

| Critère | Local | Azure |
|---|---|---|
| Coût | Matériel du poste, gratuit | Paiement à l'usage |
| Mise en place | Installation manuelle (Hadoop, NiFi, Spark) | Services managés |
| Montée en charge | Limitée à la machine | Élastique |
| Sécurité | À construire | Entra ID, RBAC, Key Vault intégrés |
| Usage dans le parcours | Développement et tests (J2, J3) | Cible de production (J4) |
