# Fiche révision – Jour 1 (BI, DW, Data Lake, Lakehouse)

## Décisionnel
- **BI** : transformer des données en informations pour décider.
- **Processus** : Décision → Questions → KPI → Sources → Qualité → ETL/ELT → Modélisation → Analyse → Restitution → Action → Mesure.
- Un projet décisionnel part d'une **question métier**, pas d'un outil.

## KPI
- Définition complète : nom, formule, champs sources, unité, **granularité**, période, filtres, limites.
- Ne pas confondre : ligne ≠ transaction ≠ commande ≠ vente ≠ retour.
  - Ex. TP : 7,5 lignes par ticket → nb transactions = `COUNT(DISTINCT ticket)`.
- Préciser HT/TTC, avant/après remise, avec/sans retours.

## OLTP vs OLAP
| OLTP | OLAP |
|---|---|
| Transactionnel (saisir une vente) | Analytique (analyser les ventes) |
| Beaucoup de petites écritures | Grosses lectures, agrégations |
| Modèle normalisé | Modèle dimensionnel |

Opérations OLAP : **drill-down** (année → mois), **roll-up** (inverse), **slice** (1 valeur), **dice** (plusieurs filtres), **pivot** (changer d'axe).

## ETL vs ELT
- **ETL** : Extract → Transform → Load. On nettoie avant de charger (DW classique).
- **ELT** : Extract → Load → Transform. On charge le brut puis on transforme (Data Lake : Bronze → Silver).
- Ce sont des organisations de flux, pas des outils.
- **Staging** : zone de préparation (contrôles formats, doublons, types, valeurs manquantes).

## Data Warehouse / Data Mart
- **DW** = orienté sujet, intégré, historisé, stable (non volatil).
- **Data Mart** = sous-ensemble du DW pour un domaine (ventes, stocks…).
- Chaîne classique : Sources → ETL → Staging → DW → Data Marts → BI.

## Modélisation dimensionnelle
- **Fait** : l'événement mesuré (quantité, montant, remise).
- **Dimension** : le contexte (quand, quoi, où, qui).
- **Grain** : ce que représente UNE ligne de la table de faits. Première question à se poser.
  - Ex. TP : 1 ligne = 1 article d'un ticket.
- **Étoile** : dimensions dénormalisées, peu de jointures, simple → reporting.
- **Flocon** : dimensions normalisées, plus de jointures, moins de redondance.
- Ex. TP : Gold en étoile (fait_ventes, fait_retours, fait_stock + dim_produit, dim_magasin, dim_date…).
- **Clé de substitution (surrogate key)** : clé technique (`*_sk`) qui remplace la clé métier.

## Qualité des données (7 dimensions)
| Dimension | Question | Ex. TP |
|---|---|---|
| Complétude | Manque-t-il des valeurs ? | |
| Validité | La valeur respecte-t-elle le format/domaine ? | dates de fermeture magasin absurdes |
| Cohérence | Les données se contredisent-elles ? | marge négative 74 % |
| Unicité | Y a-t-il des doublons ? | 0,6 % doublons (ticket, article) |
| Exactitude | La valeur est-elle vraie ? | |
| Fraîcheur | La donnée est-elle à jour ? | 2005 s'arrête au 13/12 |
| Intégrité | Les clés étrangères pointent-elles vers qq chose ? | client 100 % sans correspondance |

- **Quarantaine** : on isole les lignes en erreur au lieu de les supprimer.
- Attention : données synthétiques, clic ≠ achat, corrélation ≠ causalité.

## Big Data
- **5V** : Volume, Vélocité, Variété, Véracité, Valeur.
- **Structuré** (tables, CSV), **semi-structuré** (JSON, XML, logs), **non structuré** (texte, images).
- **Scalabilité verticale** = machine plus grosse ; **horizontale** = plus de machines (distribué).
- **HDFS** : fichiers découpés en **blocs**, stockés sur des **DataNodes**, **répliqués** (3 par défaut) ; le **NameNode** garde l'index.

## Data Lake
- Stocke tout, en brut, à bas coût.
- **Schema on read** (schéma appliqué à la lecture) vs **schema on write** (DW).
- Sans gouvernance → **Data Swamp** (marécage).
- Zones (architecture médaillon) :
  - **Bronze / Raw** : brut + provenance, jamais modifié.
  - **Silver** : nettoyé, typé, contrôlé.
  - **Gold** : prêt pour le métier (KPI, étoile).
- DW et Data Lake **coexistent**.

## Lakehouse et formats
- **Lakehouse** = Data Lake + garanties du DW (ACID, schéma, versions) via **Delta Lake / Iceberg / Hudi**.
- **ACID** : Atomicité, Cohérence, Isolation, Durabilité.
- **Parquet seul ≠ Lakehouse** : pas d'ACID, pas d'update/delete de ligne, pas d'historique de versions.

| Format | Caractéristiques |
|---|---|
| CSV | Texte, lignes, pas de type, lisible |
| JSON | Semi-structuré, imbriqué |
| Parquet | Colonnaire, typé, compressé → analytique |

- **Partitionnement** : découper les fichiers par clé (ex. année/mois) pour lire moins.

## Composants
| Composant | Rôle | Statut |
|---|---|---|
| Linux, Python | Environnement, scripts | Obligatoire |
| HDFS | Stockage distribué | Obligatoire |
| NiFi | Ingestion des flux | Obligatoire |
| Spark / PySpark | Traitement distribué | Obligatoire |
| Parquet | Format de stockage | Référence |
| ADLS Gen2 | Data Lake sur Azure | Obligatoire (J4) |
| Data Factory, Synapse | Ingestion / requêtes cloud | Étudiés |
| Delta Lake, HBase | ACID / accès par clé | Facultatifs |

## Azure (pour J4)
- **ADLS Gen2** = Blob Storage + **espace de noms hiérarchique** (vrais dossiers).
- **Entra ID** (identités), **RBAC** (droits par rôle), **ACL** (droits par dossier), **Key Vault** (secrets).
- Niveaux de stockage : **Hot / Cool / Archive** (du plus cher à l'accès au moins cher à stocker).
- Une simulation locale n'est pas un déploiement cloud.

## Batch vs streaming
- **Batch** : traitement par lots à intervalles
- **Streaming** : traitement en continu, temps réel.

---
**Les 5 à retenir absolument** : grain · faits/dimensions · étoile vs flocon · ETL vs ELT · DW vs Lake vs Lakehouse (+ Bronze/Silver/Gold).
