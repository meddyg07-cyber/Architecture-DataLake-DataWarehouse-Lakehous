# UC-01 – Limites et hypothèses

<p class="meta">Retail Intelligence Platform · TP Jour 1 · 16/11/2026</p>

## 1. Limites

| # | Limite | Constat | Conséquence |
|---|---|---|---|
| L1 | Pas de référentiel client pour l'historique | `customer` n'existe que dans le refresh (1 000 clients) ; 0 % des ventes s'y rattachent | Profils clients limités à la démographie |
| L2 | Une table présente n'a pas tous ses champs renseignés | `wcs_user_sk` vide à 42 % ; dates de fin de validité vides à 100 % | Pas d'historique des dimensions ; visiteurs anonymes |
| L3 | Ligne de vente ≠ transaction | 7,5 lignes par ticket en moyenne | Transactions = `COUNT(DISTINCT ticket)` |
| L4 | Ventes magasin et web modélisées différemment | 23 colonnes contre 34 (le web a livraison, entrepôt, page) | Harmoniser les colonnes communes |
| L5 | Un clic n'est pas un achat | Pas de session ni de type d'événement | Pas de taux de conversion |
| L6 | Les retours sont distincts des ventes | Tables séparées, datées au retour (jusqu'en 2008) | CA calculé avant retours ; taux de retour rattaché à la vente |
| L7 | Corrélation ≠ causalité | Remise de 50 % partout, sans groupe témoin | Analyses de promotion seulement descriptives |
| L8 | Jeu synthétique | Magasins à ±3 %, marges négatives, pas de saisonnalité | Aucune conclusion métier possible |

## 2. Hypothèses

| # | Hypothèse | À l'appui |
|---|---|---|
| H1 | `data_refresh/` est un lot incrémental qui suit `data/` | Clés contiguës, période du 13/12 au 31/12/2005 |
| H2 | Les noms de colonnes suivent le schéma TPCx-BB | Nombre de champs et calculs cohérents |
| H3 | Les montants sont hors taxes ; la devise est inconnue | La taxe est dans une colonne séparée |
| H4 | `wcs_sales_sk` contient le numéro de commande web | 100 % de correspondance |

## 3. Questions de recul

1. **Besoins couverts :** ventes, produits, magasins, retours et évolution. Clients, stocks et web ne le sont que partiellement.
2. **KPI non fiables :** la marge, le taux de conversion web, le stock magasin et le profil client complet.
3. **Disponible ou exploitable :** `customer` est disponible (le fichier existe) mais pas exploitable (rien ne s'y rattache).
4. **Relations à vérifier :** clics → utilisateur, avis → commande, retours du refresh.
5. **Limites du jeu synthétique :** distributions uniformes, résultats sans valeur métier.
6. **Données complémentaires utiles :** CRM (clients), stock magasin, outil web analytics (sessions), coûts réels.
