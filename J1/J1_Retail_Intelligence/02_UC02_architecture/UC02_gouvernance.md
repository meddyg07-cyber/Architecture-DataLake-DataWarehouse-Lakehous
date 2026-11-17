# UC-02 – Gouvernance

<p class="meta">Retail Intelligence Platform · TP Jour 1 · 16/11/2026</p>

| Thème | Règle proposée |
|---|---|
| **Traçabilité** | Chaque ligne garde son lot (`data` ou `data_refresh`), son fichier source et sa date d'ingestion, de Bronze jusqu'à Gold. Un manifeste par lot (md5, nombre de lignes) est généré à l'ingestion |
| **Documentation** | Un dictionnaire des tables et colonnes (repris de `UC01_inventaire_sources.xlsx`), avec le statut de chaque nom (Vérifié ou Déduit). Le dictionnaire KPI fait référence pour les calculs |
| **Qualité** | Bronze : nombre de champs et nombre de lignes conformes au manifeste. Silver : types, clés non nulles et uniques, rattachements, règles métier (quantité > 0…). Les lignes en échec vont en **quarantaine** au lieu d'être supprimées. On suit le taux de rejet par lot |
| **Accès** | Bronze : équipe Data seule. Silver : équipe Data et analystes. Gold : métiers en lecture seule. Droits attribués par rôle |
| **Protection des données** | `customer` contient des données personnelles (nom, e-mail, date de naissance). Pseudonymisation en Silver, accès restreint, aucune donnée personnelle en Gold (RGPD) |
| **Suivi des traitements** | Journaux NiFi et Spark ; pour chaque exécution : date, lot, lignes lues, écrites et rejetées, statut. Un lot en erreur n'est pas publié en Gold |
| **Coûts et volumes** | Parquet compressé (moins de stockage) ; partitionnement année/mois ; Bronze conservé intégralement, mais archivable (niveau froid sur Azure) |
