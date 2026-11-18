# UC-04 – Guide pas à pas du flux NiFi (GetFile → PutHDFS)

Environnement : Ubuntu 24.04 sous WSL2, NiFi 2.12.0 (Java 21), HDFS 3.5.0 sur `hdfs://localhost:9000`.
Interface : https://localhost:8443/nifi (identifiants générés au 1er démarrage, à relire avec la commande
`grep -E 'Generated Username|Generated Password' /opt/nifi/logs/nifi-app*.log`, à ne jamais committer).

## ★ Captures de l'interface NiFi (faites le 17/11/2026, de 17:31 à 17:44)
Les captures ont été prises dans **Edge piloté par script** (Playwright), sur la vraie interface NiFi connectée au
vrai flux. Un bandeau ajouté sous chaque image indique la date, l'heure et l'URL. Elles sont rangées dans
`04_UC04_nifi/preuves/captures/` et intégrées aux documents `UC04_*`. Trois fichiers ont été ajoutés à la liste
ci-dessous : `etape11_provenance_send_transit_uri.png`, `etape11_lignage_receive_drop.png` et
`etape10_getfile_invalide.png`.

Pour les refaire à la main : Win + Maj + S, mode « Fenêtre », en suivant le tableau ci-dessous.

| # | Où | Quoi capturer | Nom de fichier proposé |
|---|---|---|---|
| 1 | Menu ☰ → *About* | Version 2.12.0 | `etape6_about.png` |
| 2 | Canvas racine | Le Process Group et la barre d'état | `etape6_canvas_racine.png` |
| 3 | Double-clic sur le Process Group | Le flux complet : GetFile → PutHDFS → LogAttribute, compteurs, files d'attente | `etape8_flux_complet.png` |
| 4 | Clic droit sur GetFile → *Configure* → *Properties* | Propriétés de GetFile | `etape8_getfile_properties.png` |
| 5 | Idem → onglet *Scheduling* | Run Schedule 10 sec | `etape8_getfile_scheduling.png` |
| 6 | PutHDFS → *Configure* → *Properties* | Propriétés de PutHDFS | `etape8_puthdfs_properties.png` |
| 7 | PutHDFS → *Relationships* | success auto-terminate, failure non terminée | `etape8_puthdfs_relationships.png` |
| 8 | Menu ☰ → *Bulletin Board* | WARNING PutHDFS « file with same name already exists » (test B) | `etape10_bulletin_conflit.png` |
| 9 | Menu ☰ → *Data Provenance* | Liste des 6 événements de `store.dat` | `etape11_provenance_liste.png` |
| 10 | Provenance → ⓘ sur l'événement **SEND** | Détails : UUID, Transit URI hdfs://… | `etape11_provenance_send.png` |
| 11 | Même fenêtre → onglet *Attributes* | Attributs du FlowFile | `etape11_provenance_attributs.png` |
| 12 | Provenance → icône de lignage sur le SEND | Graphe RECEIVE → SEND → DROP | `etape11_lignage.png` |

Pour illustrer le **test A** (processeur invalide), refais-le à la main : GetFile → *Configure* → `Input Directory` =
`/data/nifi/input_inexistant` → *Apply*. Survole l'icône ⚠ et capture le message (`etape10_getfile_invalide.png`).
**Remets ensuite `/data/nifi/input`.**

> Si l'historique des bulletins a été vidé (ils ne durent que 5 minutes), relance le test B : `cp ~/tpcxbb_kit/data/store/store.dat /data/nifi/input/`, démarre PutHDFS, LogAttribute et GetFile, puis arrête GetFile.

---

# Procédure manuelle équivalente (pour comprendre ou reconstruire le flux)

> Faire une capture d'écran à chaque 📸 et la ranger dans `preuves/`.

## 0. Préparation (déjà fait par `scripts/uc04_prepare.sh`)
- Dossiers locaux : `/data/nifi/input`, `/data/nifi/archive`, `/data/nifi/error`
- Destination HDFS distincte de l'UC-03 : `/retail-lake/raw/nifi`
- Fichier d'essai = **copie de travail** de `store.dat` (12 lignes, 3,3 Ko) ; l'original et le dépôt UC-03 sont conservés.

## 1. Étape 6–7 – Découverte de l'interface
1. Se connecter, accepter le certificat local. 📸 canvas vide + version (menu ☰ → *About*).
2. Repérer : barre d'outils (Processor, Process Group…), canvas, panneau d'état (en haut).
3. Clic droit sur le canvas → *Create Process Group*, le nommer `UC04_ingestion_tpcxbb`, double-cliquer pour entrer dedans.

## 2. Étape 8 – Construire le flux
### A. GetFile
Glisser l'icône **Processor** sur le canvas → chercher `GetFile` → *Add*. Double-clic → onglet **Properties** :

| Propriété | Valeur |
|---|---|
| Input Directory | `/data/nifi/input` |
| Keep Source File | `false` |
| Recurse Subdirectories | `false` |

Onglet **Scheduling** : *Run Schedule* `10 sec` (évite de scruter le dossier en continu). *Apply*.

### B. PutHDFS
Ajouter `PutHDFS`. Properties :

| Propriété | Valeur |
|---|---|
| Hadoop Configuration Resources | `/opt/hadoop/etc/hadoop/core-site.xml,/opt/hadoop/etc/hadoop/hdfs-site.xml` |
| Directory | `/retail-lake/raw/nifi` |
| Conflict Resolution Strategy | `fail` (n'écrase jamais un fichier existant) |

Onglet **Relationships** : cocher *terminate* pour **success** uniquement. Laisser **failure** non terminée.

### C. Gestion de l'échec
Ajouter `LogAttribute` (Properties par défaut, Log Level `warn`). Relier PutHDFS → LogAttribute avec la
relation **failure**. Dans LogAttribute, Relationships → *terminate* sur `success`.

### D. Relier
Glisser la flèche de GetFile vers PutHDFS → cocher **success** → *Add*.
Vérifier qu'aucun processeur n'affiche de triangle jaune/rouge. 📸 flux complet + 📸 propriétés de chaque processeur.

## 3. Étape 9 – Démarrer et tester
1. Vérifier dans Ubuntu : `ls -l /data/nifi/input` et `hdfs dfs -ls /retail-lake/raw/nifi`.
2. Démarrer **PutHDFS** puis **LogAttribute**, puis **GetFile** (clic droit → *Start*).
3. Observer les compteurs *In / Out* et la file d'attente. 📸
4. Vérifier :
   ```bash
   hdfs dfs -ls -h /retail-lake/raw/nifi
   hdfs dfs -du -h /retail-lake/raw/nifi
   hdfs dfs -cat /retail-lake/raw/nifi/store.dat | md5sum ; md5sum ~/tpcxbb_kit/data/store/store.dat
   ls -l /data/nifi/input      # vide : GetFile a consommé la copie
   ```
   📸 terminal.
5. **Arrêter GetFile** après le test (ne pas relancer en boucle).

## 4. Étape 10 – Erreurs contrôlées (2 tests, rétablir après chacun)
**Test A – dossier source inexistant** : GetFile arrêté → Input Directory = `/data/nifi/input_inexistant` → *Apply*.
Le processeur devient invalide / bulletin rouge. 📸 du message. Rétablir `/data/nifi/input`.

**Test B – conflit de nom dans HDFS (failure de PutHDFS)** : recopier la même copie de travail
(`cp ~/tpcxbb_kit/data/store/store.dat /data/nifi/input/`) et démarrer GetFile.
Comme `store.dat` existe déjà dans `/retail-lake/raw/nifi` et que la stratégie est `fail`, le FlowFile part
en **failure** → LogAttribute. 📸 bulletin + file d'attente. Lire le journal :
`grep -A20 LogAttribute /opt/nifi/logs/nifi-app.log | tail -30`.
→ Montre que la stratégie anti-écrasement fonctionne (pas de doublon silencieux).

## 5. Étape 11 – Provenance
Menu ☰ → **Data Provenance** → rechercher le FlowFile `store.dat` → icône ⓘ.
Relever : *FlowFile UUID*, *Filename*, événements (`RECEIVE` par GetFile, `SEND` par PutHDFS avec l'URI
`hdfs://localhost:9000/retail-lake/raw/nifi/store.dat`, `DROP`), date/heure, taille. 📸 détail + onglet *Attributes*.
Clic sur l'icône de lignage (*Show Lineage*) → 📸 graphe.

## 6. Exporter le flux (livrable 8)
Sortir du Process Group → clic droit sur `UC04_ingestion_tpcxbb` → *Download flow definition* → enregistrer
le `.json` dans `04_UC04_nifi/` (ne contient pas de mot de passe ; à vérifier avant commit).

## 7. Étape 12 (optionnel) – Enrichir
GetFile → **UpdateAttribute** (`source=tpcxbb`, `lot=initial`, `date_ingestion=${now():format('yyyy-MM-dd')}`)
→ **RouteOnAttribute** (`dat = ${filename:endsWith('.dat')}`) → PutHDFS ; `unmatched` → PutFile `/data/nifi/error`.
