# TP J4 – Questions de recul

<p class="meta">Retail Intelligence Platform · TP Jour 4 · 19/11/2026</p>

Les réponses s'appuient sur les résultats réellement obtenus (notebook UC-08, démonstration HDFS UC-07).

**1. Pourquoi faut-il vérifier la granularité avant de calculer un KPI ?**

Parce qu'une même formule donne un résultat faux si on se trompe de grain. Dans `store_sales`, une ligne est un
**article d'un ticket**, pas une vente au sens « passage en caisse ».
- Un panier moyen calculé par ligne donnerait 1 723 $, alors que le vrai panier par ticket est de 12 913 $ : 7,5 fois
  plus.
- Le grain du Gold G1 est le couple (mois, catégorie). Additionner ses `nb_tickets` sur les catégories compte
  **plusieurs fois** un ticket qui contient plusieurs catégories.

C'est pourquoi le notebook teste l'unicité de la clé de chaque jeu avant tout calcul. Il montre ainsi que le couple
(ticket, article) **n'est pas** une clé des ventes.

**2. Quelle différence existe entre un nombre de lignes et un nombre de transactions ?**

Une transaction est un **ticket de caisse**. Nous avons vérifié qu'un ticket correspond à un seul magasin, une seule
date et un seul client. Une ligne est un article de ce ticket.
- En 2004 : 136 014 lignes, mais 18 039 transactions (7,5 lignes par ticket).
- Le nombre d'articles, lui, est encore autre chose : 6,9 millions d'unités.

Confondre ces trois comptages fausse le panier moyen et toute comparaison entre magasins.

**3. Quelles limites avez-vous rencontrées dans les données utilisées pour vos analyses ?**

- Données **synthétiques** : panier médian de 11 645 $, 372 articles par ticket, remise d'environ 50 % partout, marge
  négative sur 74 % des lignes, aucune saisonnalité.
- **2005 incomplète** (arrêt au 13/12).
- Un seul canal en Silver (magasin).
- Retours non intégrés : le CA est **avant retours**.
- Date de fermeture des magasins inutilisable.
- Surface des magasins sans unité documentée.
- Devise non documentée.

**4. Quels indicateurs n'avez-vous pas pu calculer, et pour quelles raisons ?**

- Poids des **canaux** (Q2) : `web_sales` n'a pas été transformé au J3.
- **Taux de retour** (KPI-07) : `store_returns` n'est pas en Silver.
- **Stock** (KPI-08) : `inventory` n'est pas en Silver.
- **Marge** : les coûts ne sont pas fiables (alerte qualité du J3).
- **Profil client** (Q4) : la jointure clients a été refusée au J3.

Nous avons préféré documenter ces manques plutôt que de reprendre les valeurs du J1, calculées sur des données brutes
non contrôlées.

**5. Comment avez-vous vérifié la cohérence des résultats ?**

Par trois réconciliations automatiques, qui arrêtent le notebook en cas d'écart :
1. **J1 = J4** : 39 valeurs de KPI identiques au centime entre le calcul Pandas du J1 sur les `.dat` bruts et le calcul
   Spark du J4 sur le Silver.
2. **Gold = Silver** : même CA (1 150 529 586,37 $) et mêmes quantités.
3. **Notebook = ligne de commande** : 40 valeurs identiques (`tests/test_kpi_cli.py`).

Nous avons aussi vérifié des cohérences internes :
- somme des montants par ticket = somme des lignes ;
- remise ≈ CA brut, pour un taux de 50 %.

**6. Quelle différence existe entre un constat statistique et une conclusion causale ?**

Un constat décrit **ce qui est observé** : « Buffalo a 4,1 % de CA en plus et 4,1 % de tickets en plus. » Une
conclusion causale affirme **pourquoi** : « Buffalo vend plus grâce à son emplacement. »

Pour la seconde, il faudrait :
- isoler la cause (trafic, zone de chalandise, offre) ;
- écarter les autres explications ;
- idéalement, disposer d'une expérience.

Nous avons une corrélation de 0,88 entre CA et transactions, mais ni trafic ni données clients. Nous nous arrêtons donc
au constat.

**7. Pourquoi les données synthétiques doivent-elles être identifiées dans la restitution ?**

Parce qu'un lecteur prendrait sinon des **artefacts** du générateur pour des faits. Par exemple : un panier de
12 000 $, aucune saisonnalité, des catégories qui pèsent en proportion de leur catalogue.

Les décisions prises sur ces niveaux seraient absurdes. Seule la **démarche** est transposable : définitions,
contrôles, comparaisons relatives. C'est pourquoi chaque graphique porte la mention « données TPCx-BB synthétiques ».

**8. Quel est le rôle d'ADLS Gen2 dans votre architecture ?**

C'est le **stockage du Data Lake** de la cible Azure, avec les zones `raw` → `bronze` → `silver` → `gold` et
`quality`. Il remplacerait HDFS.
- Il conserve les fichiers et porte les droits (ACL) ;
- il est lu et écrit par Spark via `abfss://`.

Il ne calcule rien, il n'orchestre rien. En parcours B, ce rôle est tenu par **HDFS**, avec la même arborescence.

**9. Quel intérêt apporte le Hierarchical Namespace ?**

De **vrais répertoires** au lieu de préfixes dans un espace plat. Cela apporte :
- le **renommage atomique** d'un dossier, en une opération de métadonnées. C'est indispensable au *commit* des
  écritures Spark et à la publication du Gold sans état intermédiaire. Démontré sur HDFS : dossier de 5 fichiers
  renommé en une commande ;
- des **ACL POSIX par répertoire**, avec héritage, qui permettent le moindre privilège zone par zone dans un seul
  conteneur.

Sans HNS, renommer un dossier, c'est copier puis supprimer chaque objet.

**10. Quelle différence existe entre RBAC et ACL ?**

| | RBAC | ACL |
|---|---|---|
| Ce qu'il attribue | Un **rôle** | Des droits `r`, `w`, `x` |
| Sur quoi | Une **ressource Azure**, au plus fin un conteneur | **Un répertoire ou un fichier** |
| Ordre d'évaluation | En premier | Seulement si le RBAC n'accorde pas l'accès |

Conséquence : donner *Storage Blob Data Reader* à un analyste lui ouvrirait **tout** le conteneur, Raw compris. Nous
lui donnons donc des ACL sur `gold/` seulement. Nos 16 tests HDFS montrent ce modèle par ACL.

**11. Dans quels cas Azure Data Factory serait-il utile ?**

- Pour **déplacer** les fichiers vers ADLS : activité *Copy*. Depuis notre poste, il faudrait un *Self-hosted
  Integration Runtime*.
- Pour **planifier et enchaîner** les traitements : Bronze, puis Silver, puis Gold, puis contrôles. On aurait les
  déclencheurs, les reprises sur erreur et le suivi des exécutions.
- Pour intégrer le lot `data_refresh` à son arrivée.

ADF remplacerait NiFi et notre `run_all.sh`. Il ne remplace ni le stockage ni le moteur Spark.

**12. Quel rôle pourrait jouer Synapse Analytics ?**

Celui d'**espace d'analyse** :
- les **Spark pools** exécuteraient nos scripts du J3 et le notebook UC-08, en changeant seulement la racine des
  chemins ;
- le **SQL serverless** exposerait le Gold en vues SQL pour Power BI et les analystes ;
- **Synapse Studio** remplacerait JupyterLab.

En open source, il faut plusieurs briques pour couvrir ces fonctions : Spark, Trino, un catalogue, Airflow et
Superset.

**13. Quels éléments de votre architecture sont réellement déployés et lesquels restent théoriques ?**

- **Déployés et exécutés** : HDFS, NiFi (J2) ; PySpark, Bronze, Silver, Gold, qualité (J3) ; notebook UC-08, KPI,
  graphiques ; démonstration des zones, du HNS et des ACL sur HDFS (J4).
- **Simulés** : création d'ADLS Gen2, dépôt de fichier, rôles et ACL Azure. Les commandes sont écrites, mais **non
  exécutées**.
- **Théoriques** : ADF, Synapse, Power BI, Key Vault, ainsi qu'Airflow, MinIO, Iceberg, Trino et Superset.

Le schéma d'architecture le montre par trois styles de cadre.

**14. Quels seraient les principaux risques de coût ou de sécurité dans une mise en production ?**

*Coût :*
- pool Spark ou espace Synapse laissé actif ;
- requêtes SQL serverless sur des fichiers non partitionnés, facturées au volume lu ;
- stockage du Raw en niveau chaud sans cycle de vie ;
- crédit gratuit épuisé, puis facturation.

Parades : budget et alertes, arrêt automatique, Parquet partitionné, suppression du groupe de ressources.

*Sécurité :*
- rôle *Contributor* donné par facilité, qui permet de lire les clés du compte ;
- clés partagées laissées actives ;
- rôle de données sur tout le conteneur au lieu d'ACL ;
- secrets dans Git ;
- accès public au stockage ;
- en local, authentification `simple`, où n'importe qui peut se déclarer administrateur (démontré).

Parades : Entra ID et identités managées, clés désactivées, ACL par groupe, Key Vault, journalisation des accès.
