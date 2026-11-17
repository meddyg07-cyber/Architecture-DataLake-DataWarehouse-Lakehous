"""Genere UC01 inventaire_sources.xlsx et dictionnaire_KPI.xlsx a partir des preuves.

Usage : python build_xlsx.py <dossier_UC01>
"""
import sys
from pathlib import Path

import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

UC = Path(sys.argv[1])
P = UC / "preuves"
rd = lambda f: pd.read_csv(P / f, sep=";", encoding="utf-8-sig")  # noqa: E731


def style(path):
    wb = load_workbook(path)
    for ws in wb.worksheets:
        for c in ws[1]:
            c.font = Font(bold=True, color="FFFFFF")
            c.fill = PatternFill("solid", fgColor="1B3550")
            c.alignment = Alignment(wrap_text=True, vertical="top")
        for i, col in enumerate(ws.columns, 1):
            w = max(len(str(c.value or "")) for c in col)
            ws.column_dimensions[get_column_letter(i)].width = min(max(10, w + 2), 60)
            for c in col[1:]:
                c.alignment = Alignment(wrap_text=True, vertical="top")
        ws.freeze_panes = "A2"
        ws.auto_filter.ref = ws.dimensions
    wb.save(path)


# ------------------------------------------------------------------ inventaire_sources.xlsx
kit = pd.DataFrame([
    ("Nom du kit ou de l'archive", "Dossier 'retail_project/retail_project' (sous-dossiers data/ et data_refresh/)", "Verifie (observe)"),
    ("Version ou provenance", "Non communique. Contenu conforme au schema TPCx-BB (23 tables) ; version exacte non verifiee", "Non disponible / A valider"),
    ("Date de mise a disposition", "Non communiquee. Date de copie locale observee : 16/11/2026", "A valider"),
    ("Source de telechargement ou de distribution", "Non communiquee (fichiers remis par le formateur)", "A valider"),
    ("Format des fichiers", "32 fichiers .dat texte delimite '|' sans en-tete, UTF-8, LF ; 2 fichiers .csv de rapport (CRLF)", "Verifie"),
    ("Volume total constate", "968,3 Mo (1 015 327 295 octets) (data/ : 960 Mo ; data_refresh/ : 9,2 Mo)", "Verifie (mesure)"),
    ("Nombre de fichiers", "34 (22 dans data/, 12 dans data_refresh/) ; 23 tables distinctes", "Verifie (mesure)"),
    ("Outils de generation eventuellement utilises", "Non documente. Les fichiers *_audit.csv suggerent un generateur (type PDGF) mais rien ne le confirme", "Hypothese"),
    ("Periode couverte (ventes)", "data/ : 2001-01-01 -> 2005-12-13 ; data_refresh/ : 2005-12-13 -> 2005-12-31", "Verifie"),
    ("Nature des donnees", "Synthetiques (benchmark), aucune donnee reelle d'entreprise", "Verifie (enonce) / Deduit (distributions uniformes)"),
    ("Donnees complementaires (hors TPCx-BB)", "Aucune fournie", "Verifie"),
], columns=["Information", "Valeur constatee", "Statut"])

inv = rd("inventaire_fichiers.csv")
USAGE = {
    "store_sales": "Fait central ventes magasin : CA, transactions, panier, quantites, remises",
    "web_sales": "Fait central ventes web : CA, commandes, panier, livraison",
    "store_returns": "Retours magasin : taux et motifs de retour",
    "web_returns": "Retours web : taux et motifs de retour",
    "inventory": "Photos hebdomadaires de stock par article x entrepot",
    "item": "Referentiel produits (categorie, marque, prix)",
    "item_marketprices": "Prix concurrents par article et periode",
    "customer": "Referentiel clients - PRESENT UNIQUEMENT dans data_refresh (1000 lignes)",
    "customer_address": "Adresses clients - PRESENT UNIQUEMENT dans data_refresh (500 lignes)",
    "customer_demographics": "Profils demographiques (combinatoire) rattaches aux ventes",
    "household_demographics": "Profils foyer rattaches aux ventes",
    "income_band": "Tranches de revenu (via household_demographics)",
    "store": "Referentiel magasins (12) et geographie",
    "warehouse": "Referentiel entrepots (5) - stock et expedition web",
    "web_clickstreams": "Clics web (navigation, lien vente)",
    "web_page": "Referentiel pages web", "web_site": "Referentiel sites web",
    "product_reviews": "Avis produits (note + texte libre)", "promotion": "Referentiel promotions",
    "reason": "Motifs de retour", "ship_mode": "Modes de livraison",
    "date_dim": "Calendrier (1900-2199)", "time_dim": "Heure de la journee (a la seconde)",
}
inv["usage_analytique"] = inv["table"].map(USAGE).fillna("Rapport technique de generation des prix")
inv["statut"] = "Verifie (fichier ouvert et mesure)"

dom = pd.DataFrame([
    ("Ventes magasin", "store_sales", "Oui", "Identifiants, date, heure, produit, client (sk), magasin, quantite, montants", "Exploitable"),
    ("Ventes web", "web_sales", "Oui", "Identifiants, date vente + expedition, produit, client (sk), page, site, entrepot, montants", "Exploitable"),
    ("Retours", "store_returns, web_returns, reason", "Oui", "Ticket/commande + article, date, quantite, montant, motif", "Exploitable (lot data) ; refresh : 93-96% sans vente d'origine"),
    ("Produits", "item, item_marketprices", "Oui", "Id, libelle, categorie (9), classe, marque, prix ; prix concurrents", "Exploitable ; cout d'achat > prix courant pour 43% des articles"),
    ("Clients", "customer, customer_address", "PARTIEL", "Uniquement dans data_refresh (1000 clients sk 99000-99999) ; 0% des ventes du lot data rattachables", "Non exploitable pour caracteriser les clients des ventes historiques"),
    ("Clients (demographie)", "customer_demographics, household_demographics, income_band", "Oui", "Genre, statut marital, education, risque credit, revenu foyer", "Exploitable via cdemo_sk/hdemo_sk des ventes (100% correspondance)"),
    ("Magasins", "store", "Oui", "12 magasins, 8 Etats US, ville, comte", "Exploitable ; s_closed_date_sk incoherent (1917-2141)"),
    ("Stocks", "inventory, warehouse", "Oui", "Photo hebdomadaire date x article x entrepot (5 entrepots)", "Exploitable ; stocks par entrepot, pas par magasin ; pas de mouvements"),
    ("Navigation", "web_clickstreams, web_page", "Oui", "Date, heure, article, page, utilisateur (58%), lien vente (9,9%)", "Partiel : pas de type d'evenement ni de session"),
    ("Avis produits", "product_reviews", "Oui", "Note 1-5, texte, article, utilisateur, commande", "Exploitable (texte libre)"),
    ("Promotions", "promotion", "Oui", "300 promotions, canaux, cout", "Dates de promotion incoherentes (1901-2199)"),
    ("Dates et temps", "date_dim, time_dim", "Oui", "Calendrier complet + heures", "Exploitable"),
    ("Logistique", "ship_mode, warehouse", "Oui", "Modes de livraison, entrepots", "Exploitable"),
    ("Donnees complementaires", "-", "Non fournies", "-", "Non disponible"),
], columns=["Domaine", "Tables observees", "Present", "Contenu verifie", "Exploitabilite"])

out = UC / "UC01_inventaire_sources.xlsx"
with pd.ExcelWriter(out, engine="openpyxl") as xw:
    kit.to_excel(xw, sheet_name="0_Kit_provenance", index=False)
    dom.to_excel(xw, sheet_name="1_Domaines", index=False)
    inv.to_excel(xw, sheet_name="2_Inventaire_fichiers", index=False)
    rd("colonnes.csv").to_excel(xw, sheet_name="3_Colonnes_types", index=False)
    rd("controles_cles.csv").to_excel(xw, sheet_name="4_Cles", index=False)
    rd("controles_relations.csv").to_excel(xw, sheet_name="5_Relations", index=False)
    rd("controles_qualite.csv").to_excel(xw, sheet_name="6_Controles_qualite", index=False)
style(out)
print("OK", out)

# ------------------------------------------------------------------ dictionnaire_KPI.xlsx
C = ["Code", "Nom", "Definition metier", "Formule", "Unite", "Perimetre / axes", "Frequence", "Sources",
     "Donnees manquantes", "Limites d'interpretation", "Valeur test (data, 2001-2005)", "Priorite"]
K = [
    ("KPI-01", "Chiffre d'affaires brut", "Ventes apres remise, hors taxe, avant retours",
     "SUM(ss_ext_sales_price) + SUM(ws_ext_sales_price)", "Unite monetaire (non documentee)",
     "Canal, magasin, categorie, periode", "Quotidienne", "store_sales, web_sales, date_dim, item, store",
     "Devise", "Avant retours ; 2005 incomplete", "2 981 466 779", "Indispensable"),
    ("KPI-02", "Nombre de transactions", "Nombre de tickets (magasin) ou de commandes (web)",
     "COUNT(DISTINCT ss_ticket_number) + COUNT(DISTINCT ws_order_number)", "Nombre",
     "Canal, magasin, periode", "Quotidienne", "store_sales, web_sales", "-",
     "1 ligne != 1 transaction (7,5 lignes par ticket)", "178 200", "Indispensable"),
    ("KPI-03", "Panier moyen", "CA moyen par transaction", "KPI-01 / KPI-02", "Unite monetaire",
     "Canal, magasin, periode", "Mensuelle", "store_sales, web_sales", "-",
     "Valeurs tres elevees (artefact synthetique)", "Magasin 14 335 ; web 19 127", "Indispensable"),
    ("KPI-04", "Quantites vendues", "Nombre d'unites vendues", "SUM(ss_quantity) + SUM(ws_quantity)", "Unites",
     "Canal, article, categorie, periode", "Quotidienne", "store_sales, web_sales, item", "-",
     "Additionner des produits differents a peu de sens", "67 479 852", "Indispensable"),
    ("KPI-05", "Taux de remise", "Part du prix catalogue accordee en remise",
     "SUM(ext_discount_amt) / SUM(ext_list_price)", "%", "Canal, categorie, periode", "Mensuelle",
     "store_sales, web_sales", "-", "~50 % partout (jeu synthetique)", "50,0 %", "Utile"),
    ("KPI-06", "Evolution du CA N/N-1", "Variation du CA par rapport a l'annee precedente",
     "(CA_N - CA_N-1) / CA_N-1", "%", "Canal, magasin, categorie", "Mensuelle / annuelle",
     "store_sales, web_sales, date_dim", "-", "Comparer des periodes completes (2005 s'arrete au 13/12)",
     "2004 vs 2003 : magasin +0,37 % ; web -0,64 %", "Indispensable"),
    ("KPI-07", "Taux de retour", "Part du CA retournee par les clients",
     "SUM(return_amt) / SUM(ext_sales_price)", "%", "Canal, categorie, article, motif", "Mensuelle",
     "store_returns, web_returns, ventes, reason", "Retours du refresh sans vente d'origine",
     "Les retours sont dates au retour (jusqu'en 2008)", "Magasin 2,32 % ; web 2,31 %", "Utile"),
    ("KPI-08", "Stock moyen", "Quantite moyenne en stock par article et entrepot",
     "AVG(inv_quantity_on_hand) par semaine", "Unites", "Article, entrepot (5), semaine", "Hebdomadaire",
     "inventory, warehouse, item", "Stock magasin absent", "Photos hebdomadaires, pas de mouvements",
     "259 semaines disponibles", "Utile"),
]
kpi = pd.DataFrame(K, columns=C)
out = UC / "UC01_dictionnaire_KPI.xlsx"
with pd.ExcelWriter(out, engine="openpyxl") as xw:
    kpi.to_excel(xw, sheet_name="Dictionnaire_KPI", index=False)
    rd("kpi_test_par_annee_canal.csv").to_excel(xw, sheet_name="Test_annee_canal", index=False)
    rd("kpi_test_par_magasin.csv").to_excel(xw, sheet_name="Test_magasin", index=False)
    rd("kpi_test_par_categorie.csv").to_excel(xw, sheet_name="Test_categorie", index=False)
style(out)
print("OK", out)
