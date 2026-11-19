# TP J3 – Questions de recul

<p class="meta">Retail Intelligence Platform · TP Jour 3 · 18/11/2026</p>

**1. Pourquoi vérifier les schémas avant de transformer ?**
Parce que nos `.dat` n'ont ni en-tête ni types. Spark devine des colonnes `_c0…`, et des `double` pour l'argent. Sans
vérification, on calcule faux sans le voir : un montant arrondi, une date lue comme du texte, une colonne décalée.
Nous avons imposé les noms et les types (`decimal(7,2)`), puis mesuré 0 valeur non convertible avant de transformer.

**2. Différence entre une donnée brute, Silver et Gold ?**
- La **brute** (Raw/Bronze) est la source telle que reçue : le `.dat`, puis sa copie Parquet en texte avec la
  provenance.
- La **Silver** est la même donnée, au même grain (1 ligne = 1 article d'un ticket), mais typée, contrôlée et enrichie
  de sa date, avec des indicateurs d'anomalie.
- La **Gold** est une donnée **agrégée pour une question métier** : 540 lignes « catégorie × mois » au lieu de
  667 579 lignes de ventes.

**3. Pourquoi connaître la granularité avant d'agréger ?**
Pour savoir ce que l'on compte. Compter les lignes de `store_sales` donne des **articles vendus**, pas des
**tickets**. Il faut `COUNT(DISTINCT ticket)`, soit environ 7,5 fois moins. De même, `nb_tickets` du Gold G1 ne
s'additionne pas entre catégories, puisqu'un ticket peut en contenir plusieurs.

**4. Risques d'une jointure sur une clé supposée ?**
- **Multiplier des lignes** si la clé n'est pas unique côté dimension : le CA est alors gonflé.
- **Perdre des lignes** avec une jointure interne sur des clés qui ne correspondent pas.
- **Rapprocher des choses sans rapport.**

Nous avons vérifié l'unicité (0 doublon) et l'existence (0 orphelin), puis comparé les volumes avant et après (667 579
des deux côtés). Exemple d'une jointure refusée : `ss_customer_sk → customer`, qui ne rapproche aucune vente.

**5. Pourquoi ne pas supprimer automatiquement les valeurs atypiques ?**
Parce qu'atypique ne veut pas dire faux. Nos 11 910 ventes au-dessus du seuil de Tukey sont cohérentes (100 articles à
près de 200 $). Les supprimer retirerait du vrai CA. Les 8 174 lignes qui partagent une clé sont, elles aussi, de vraies
ventes. Nous les **signalons** (`_flag_…`) et laissons l'analyste décider.

**6. Quels contrôles vérifient la cohérence d'un jeu transformé ?**
- **Réconciliation des volumes** : Raw = Bronze = Silver + quarantaine.
- **Réconciliation des mesures** : somme du CA Gold = somme du CA Silver, au centime ; quantités identiques ; parts de
  CA = 100 %.
- **Unicité du grain.**
- **Intégrité référentielle.**
- **Règles de calcul internes** : `ext_sales = prix × quantité`.
- **Stabilité des volumes par période.**

Au total, 31 contrôles dans `04_qualite.py`.

**7. Pourquoi Parquet est-il adapté à l'analytique ?**
Il stocke les données **par colonne**, compressées, avec leur **schéma et leurs types**. Une agrégation ne lit que les
colonnes utiles, et seulement les partitions utiles. Mesuré : 43 Mo contre 93 Mo en CSV, et une agrégation 3 fois plus
rapide (0,35 s contre 1,06 s). Le `decimal` est conservé, ce qui n'est pas le cas en CSV ou en JSON.

**8. Pourquoi Parquet seul ne fournit-il pas les garanties d'une table Lakehouse ?**
Parce que c'est un format de **fichier** :
- pas de journal de transactions, donc un `overwrite` interrompu laisse un état partiel ;
- pas de versions ;
- pas de `UPDATE` ni de `DELETE` d'une ligne ;
- pas de contrôle du schéma à l'écriture ;
- pas d'isolation entre écrivains.

Ce sont Delta Lake, Iceberg ou Hudi qui ajoutent ces garanties, par une couche de métadonnées.

**9. Dans quels cas une base NoSQL compléterait-elle le Data Lake ?**
Pour des **accès opérationnels rapides à une clé** :
- fiche produit par `i_item_id` ;
- dernier état du stock d'un article ;
- historique des événements d'un client, consulté par une application en quelques millisecondes.

Le Data Lake et Parquet servent les **analyses sur de gros volumes**. Une base comme HBase servirait la lecture et
l'écriture unitaire. Les deux sont complémentaires.

**10. Quelles limites de TPCx-BB pour interpréter les résultats ?**
- Données **synthétiques** : 74 % de marges négatives, panier moyen d'environ 13 000 $, remise d'environ 50 %
  partout ;
- écarts très faibles entre magasins et entre années (±1,5 %) : **aucune tendance réelle** ne peut en être tirée ;
- 2005 incomplète ;
- clients non rapprochables ;
- dates de fermeture absurdes.

Les résultats valident la **chaîne technique**, pas une connaissance métier. Nous ne revendiquons ni score ni
performance au sens du benchmark.
