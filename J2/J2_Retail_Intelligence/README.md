# J2 – Retail Intelligence Platform

TP Jour 2 (UC-03 et UC-04) : Hadoop, HDFS et ingestion avec Apache NiFi. IPSSI Mastère Data & IA.

## Contenu

| Dossier / fichier | Contenu | Livrable du sujet |
|---|---|---|
| `03_UC03_hdfs/UC03_fiche_environnement.md` | Versions, chemins, configuration, services, ports, sécurité, écarts | 1 |
| `03_UC03_hdfs/UC03_fiche_hadoop_hdfs.md` | État de HDFS, rôle du NameNode et des DataNodes, mono-nœud | 2 |
| `03_UC03_hdfs/UC03_depot_et_verification.md` | Inventaire des 34 fichiers, dépôt, contrôles (MD5 34/34), permissions | 3, 6 |
| `03_UC03_hdfs/UC03_arborescence_datalake.md` | Arborescence `/retail-lake`, schéma, rôle des zones, provenance | 4 |
| `03_UC03_hdfs/UC03_commandes_hdfs.md` | Commandes HDFS, résultats, erreurs | 5 |
| `04_UC04_nifi/UC04_fiche_decouverte_nifi.md` | Instance NiFi, concepts (FlowFile, Processor…) | Étape 6 |
| `04_UC04_nifi/UC04_flux_nifi.md` | Schéma, configuration, exécution, export, flux enrichi conçu | 7, 8, 9 |
| `04_UC04_nifi/UC04_erreurs_et_provenance.md` | Tests d'erreur, tableau des 14 erreurs et corrections, provenance | 10, 11 |
| `04_UC04_nifi/UC04_ingestion_tpcxbb.json` | Export (*flow definition*) du Process Group NiFi | 8 |
| `04_UC04_nifi/UC04_guide_pas_a_pas.md` | Liste des captures de l'interface NiFi et procédure manuelle | – |
| `J2_questions_de_recul.md` | Réponses aux 14 questions de recul | §19 |
| `*/preuves/` | Sorties de commandes horodatées (`.txt`), CSV de contrôle, schémas SVG, `captures/` | 16 |
| `scripts/` | Scripts d'installation, d'exécution et de collecte des preuves | 13 |

Le livrable 12 (script de repli) est **sans objet** : NiFi a fonctionné, et le flux a réellement été exécuté.

## Réalisé ou seulement conçu

| Élément | Statut |
|---|---|
| Installation Hadoop 3.5.0 et NiFi 2.12.0, HDFS pseudo-distribué | ✅ exécuté |
| Arborescence `/retail-lake`, dépôt de 34 fichiers TPCx-BB, contrôle MD5, correction des permissions | ✅ exécuté |
| Flux NiFi GetFile → PutHDFS (+ LogAttribute), dépôt dans `/retail-lake/raw/nifi`, 2 tests d'erreur, provenance, export | ✅ exécuté (flux créé par l'API REST NiFi, visible dans l'interface) |
| Flux enrichi UpdateAttribute / RouteOnAttribute (étape 12) | 📝 conçu uniquement |
| Zones bronze, silver, gold, quality, logs | créées, vides (alimentées au J3) |

## Environnement et versions

| Composant | Version |
|---|---|
| Système | Windows 11 + **WSL 2.6.1**, Ubuntu **24.04.4 LTS** (mono-nœud, usage pédagogique) |
| Java | OpenJDK **17** (Hadoop) et OpenJDK **21** (NiFi) |
| Hadoop | **3.5.0** (`/opt/hadoop`) |
| NiFi | **2.12.0** (`/opt/nifi`), avec `nifi-hadoop-nar` et `nifi-hadoop-libraries-nar` 2.12.0 |
| Python | 3.12.3 (Ubuntu), 3.11 (Windows, génération des PDF) |

## Reproduire

Toutes les commandes se lancent **dans Ubuntu (WSL)**, depuis le dossier `scripts/`.

**1. Installation (une seule fois).** En root : `apt install openjdk-17-jdk-headless openjdk-21-jdk-headless
openssh-server`, puis création de `/opt/hadoop`, `/opt/nifi` et `/data/nifi/{input,archive,error}` avec
l'utilisateur comme propriétaire. Ensuite, en tant qu'utilisateur :
```bash
# archives dans ~/downloads : hadoop-3.5.0.tar.gz(.sha512), nifi-2.12.0-bin.zip(.sha512), 2 NAR Hadoop
bash setup_env_wsl.sh            # vérifie les SHA-512, installe, configure HDFS et NiFi, SSH local
hdfs namenode -format            # PREMIÈRE INSTALLATION UNIQUEMENT : efface toutes les métadonnées HDFS
```

**2. Démarrage, à chaque séance** (HDFS sous Java 17, puis NiFi sous Java 21) :
```bash
bash start_env.sh
```
Garder un terminal Ubuntu ouvert : WSL arrête la VM, et donc HDFS et NiFi, quand plus aucune session n'est active.

**3. UC-03 et UC-04**
```bash
bash uc03_hdfs.sh all          # étapes 1 à 5 → 03_UC03_hdfs/preuves/
bash uc03_permissions.sh       # zone Raw en lecture seule
bash uc04_prepare.sh           # dossiers NiFi + copie de travail de store.dat
python3 uc04_nifi.py build     # crée le Process Group et les 3 processeurs
python3 uc04_nifi.py run       # exécute le flux et vérifie dans HDFS
python3 uc04_nifi.py erreur_dossier ; python3 uc04_nifi.py erreur_conflit
python3 uc04_nifi.py provenance ; python3 uc04_nifi.py export
bash captures_terminal_uc03.sh # affiche les écrans à capturer
```
**PDF** (sous Windows) : `python ../../J1/J1_Retail_Intelligence/scripts/build_pdf.py 03_UC03_hdfs 04_UC04_nifi .`

**4. Arrêt** (arrêter d'abord les flux dans l'interface NiFi) :
```bash
bash stop_env.sh               # NiFi, puis HDFS
```

## Chemins et paramètres (non sensibles)

| Élément | Valeur |
|---|---|
| NameNode | `hdfs://localhost:9000` · interface http://localhost:9870 |
| NiFi | https://localhost:8443/nifi (certificat auto-signé, utilisateur unique) |
| Configuration Hadoop | `/opt/hadoop/etc/hadoop/{core-site,hdfs-site,hadoop-env}` : réplication 1, blocs de 128 Mo |
| Data Lake | `/retail-lake/{raw/{tpcxbb/{initial,refresh},nifi},bronze/tpcxbb,silver,gold,quality,logs}` |
| Kit source | `J1/retail_project/retail_project`, vu sous Ubuntu par le lien `~/tpcxbb_kit` (le chemin Windows contient des espaces) |
| Flux NiFi | GetFile `/data/nifi/input` (10 s, Keep Source File=false) → PutHDFS `/retail-lake/raw/nifi` (Conflict Resolution=fail) ; failure → LogAttribute (warn) |
| Spécifique WSL | `java.arg.ipv4=-Djava.net.preferIPv4Stack=true` dans `/opt/nifi/conf/bootstrap.conf` |

**Secrets** : les identifiants NiFi sont générés au premier démarrage. Pour les relire :
`grep -E 'Generated Username|Generated Password' /opt/nifi/logs/nifi-app*.log`. Ils ne sont **jamais** versionnés :
les scripts les relisent à l'exécution, ou dans `NIFI_USER` / `NIFI_PASS`.

## Usage de l'IA

Installation, exécution et rédaction réalisées avec l'assistance de Claude (Anthropic). Les captures de
l'interface Web (NameNode et NiFi) ont été prises par Edge piloté par script. Pendant ces captures, GetFile a été
supprimé par erreur puis recréé à l'identique : c'est l'erreur n° 14 de `UC04_erreurs_et_provenance.md`. Les commandes ont été
réellement exécutées sur mon poste. Les résultats et les documents ont été vérifiés et relus par moi.
