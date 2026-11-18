# J2 – Questions de recul

<p class="meta">Retail Intelligence Platform · TP Jour 2 · 17/11/2026 · §19 du sujet</p>

**1. Quel est le rôle du NameNode dans HDFS ?**
C'est le gestionnaire des **métadonnées**. Il connaît l'arborescence, les noms, les propriétaires et les
permissions, et il sait de quels **blocs** se compose chaque fichier et sur quels DataNodes ils se trouvent. Il ne
stocke pas les données elles-mêmes. Toute opération (`ls`, `mkdir`, lecture, écriture) passe d'abord par lui. Chez
nous, il écoute sur `localhost:9000` et conserve son image (`fsimage` + journal `edits`) dans `~/hadoop-data/namenode`.

**2. Quelle différence existe entre un NameNode et un DataNode ?**
Le NameNode sait **où** sont les données, les DataNodes les **détiennent**. Le NameNode est unique (ou doublé en
haute disponibilité) et garde les métadonnées en mémoire. Les DataNodes sont nombreux : ils stockent les blocs sur
leurs disques, servent les lectures et écritures **directement** aux clients, et envoient au NameNode des
*heartbeats* et des *block reports*. Exemple : pour `inventory.dat` (405 Mo), le NameNode connaît la liste des
4 blocs, et le DataNode stocke ces 4 blocs.

**3. Pourquoi HDFS découpe-t-il les fichiers en blocs ?**
- Pour stocker des fichiers **plus gros qu'un disque**, en les répartissant sur plusieurs machines.
- Pour **paralléliser** : chaque bloc peut être traité par une tâche Spark ou MapReduce différente, au plus près de
  la donnée (localité).
- Pour **répliquer** et récupérer à la granularité du bloc.
- Les blocs sont **grands** (128 Mo) afin de limiter le nombre d'objets que le NameNode garde en mémoire et de
  privilégier les lectures séquentielles.

**4. Quel est l'intérêt de la réplication ?**
La **tolérance aux pannes** : chaque bloc est copié sur plusieurs DataNodes (3 par défaut). Si une machine ou un
disque tombe, les données restent lisibles, et le NameNode recrée automatiquement les copies manquantes. La
réplication améliore aussi la **lecture parallèle** et la localité. Chez nous, `dfs.replication=1`, car il n'y a
qu'un DataNode : il n'y a donc **aucune redondance**.

**5. Pourquoi organiser un Data Lake en plusieurs zones ?**
Pour séparer les données selon leur **niveau de confiance et de préparation** : Raw/Bronze (brut), Silver
(nettoyé), Gold (prêt pour le métier). Chaque zone a ses **règles** (immuable ou retraitable), ses **droits
d'accès** (équipe Data ou métiers) et sa **durée de conservation**. Sans zones, on obtient un *data swamp* où
personne ne sait ce qui est fiable. Les zones `quality/` et `logs/` séparent en plus les contrôles et les journaux
des données métier.

**6. Pourquoi conserver les données sources dans Raw ?**
Pour pouvoir **rejouer** les traitements après une correction, sans redemander les fichiers ; pour **prouver** ce
qui a été reçu (audit, MD5) ; pour disposer d'informations non exploitées aujourd'hui (*schema on read*). La zone
doit donc être **immuable** : chez nous, les fichiers sont en lecture seule (`444`).

**7. Quel est le rôle d'un FlowFile dans NiFi ?**
C'est l'**unité de données qui circule** dans le flux : un **contenu** (les octets, stockés une fois dans le content
repository) et des **attributs** (métadonnées clé/valeur : `filename`, `path`, `uuid`, dates…). Les processeurs le
lisent, l'enrichissent et le routent. Son UUID permet de suivre son parcours dans la provenance.

**8. Quelle différence existe entre un Processor et une Connection ?**
Le **Processor** **agit** : il lit, transforme, route ou écrit (GetFile, PutHDFS), et il possède des propriétés,
une planification et des relations de sortie. La **Connection** **transporte** : elle relie la relation d'un
composant (par exemple `success`) à un autre composant. C'est aussi une **file d'attente**, qui tamponne les
FlowFiles et applique la *back-pressure* quand la destination ne suit pas.

**9. Pourquoi la provenance est-elle importante ?**
Elle permet de **reconstituer** ce qui est arrivé à chaque donnée : d'où elle vient, quand elle est arrivée, par
quels composants elle est passée, où elle a été écrite. C'est indispensable pour l'**audit** et la conformité
(RGPD), le **diagnostic** d'un incident et la **confiance** dans les chiffres. Exemple : `RECEIVE
file:/data/nifi/input/store.dat` (16:03:35), puis `SEND hdfs://localhost:9000/retail-lake/raw/nifi/store.dat`
(16:03:36). Pour la 2ᵉ copie, l'absence de SEND prouve qu'elle n'a pas été écrite.

**10. Comment distinguer un échec technique d'un rejet métier ?**
- **Échec technique** : le traitement n'a pas pu se faire (service indisponible, droits, chemin absent, conflit de
  nom). Le contenu n'est pas en cause, et on peut **réessayer** une fois la cause corrigée. Dans NiFi, il passe par la
  relation `failure`. Exemples : le test A (dossier inexistant) et le test B (conflit dans HDFS).
- **Rejet métier** : le transfert a réussi, mais la donnée **viole une règle** (format, colonne manquante, quantité
  négative, clé inconnue). Réessayer ne sert à rien : la ligne part en **quarantaine** (`quality/`) pour analyse ou
  correction à la source. Exemple : `item_marketprices_audit.csv`, qui n'a pas la structure d'un fichier de données.

**11. Quels risques apparaissent si un flux est relancé sans contrôle des doublons ?**
- **Doublons** dans le lac, donc des ventes et des KPI **gonflés**.
- **Écrasement silencieux** d'un dépôt antérieur (avec la stratégie `replace`), donc perte de la version d'origine
  et de la preuve.
- **Incohérences** entre zones, et coûts de stockage et de traitement inutiles.

Les parades : stratégie `fail` (vérifiée au test B), chemins datés ou par lot, manifeste des fichiers déjà ingérés
(nom + MD5), traitements **idempotents**.

**12. Quelles limites présente un environnement mono-nœud ?**
- **Aucune tolérance aux pannes** : un seul DataNode et une réplication de 1, donc la perte de la machine ou de la VM
  WSL rend tout HDFS indisponible.
- Le NameNode est un **point unique de défaillance**, sans haute disponibilité.
- **Pas de parallélisme réel**, et des performances limitées à un seul disque (virtuel).
- Pas de répartition de charge ; sécurité simplifiée (un seul utilisateur, super-utilisateur, sans Kerberos).

Il sert à **apprendre**. Ce n'est pas un cluster de production.

**13. Pourquoi une copie locale ne constitue-t-elle pas une preuve de dépôt HDFS ?**
Une copie locale prouve seulement que le fichier existe **sur le disque de la machine**. Elle ne prouve pas que
HDFS l'a reçu, découpé en blocs et rendu accessible aux autres traitements. La preuve doit venir de **HDFS lui-même** :
- `hdfs dfs -ls` (présence, taille, droits) ;
- `hdfs fsck` (blocs, santé) ;
- une **relecture** depuis HDFS comparée à la source (MD5 identique, 34/34) ;
- l'événement **SEND** `hdfs://…` dans la provenance NiFi.

**14. Quelles informations doivent être conservées pour reproduire une ingestion ?**
- Les **versions** (OS, Java, Hadoop, NiFi) et la **configuration** (`core-site.xml`, `hdfs-site.xml`, propriétés
  des processeurs, export du flux).
- Les **chemins source et destination**, le **lot** et la **date**.
- Pour chaque fichier : **nom, taille, nombre de lignes et somme de contrôle** (manifeste).
- Les **commandes ou scripts** exécutés, avec leurs **journaux horodatés** et codes retour.
- La **provenance** NiFi (UUID, événements).
- Les **erreurs** rencontrées et leurs corrections.
- Les **droits** appliqués.

Tout cela figure dans `preuves/`, `scripts/` et le `README.md`.
