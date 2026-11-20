"""Reproductibilité (AV-01) : le script en ligne de commande doit redonner exactement les KPI du notebook.

Usage : python tests/test_kpi_cli.py  (après le notebook et l'étape 02_kpi_cli de run_all.sh)
"""
import sys
from pathlib import Path

import pandas as pd

OUT = Path(__file__).resolve().parents[1] / "analytics" / "outputs"
COLS = ["annee", "ca_brut", "ca_net_paye", "nb_transactions", "nb_lignes", "quantites",
        "panier_moyen_net", "panier_moyen_brut", "taux_remise_pct"]

nb = pd.read_csv(OUT / "kpi.csv", sep=";", decimal=",")[COLS].set_index("annee")
cli = pd.read_csv(OUT / "kpi_cli.csv", sep=";", decimal=",")[COLS].set_index("annee")
ecarts = (nb - cli).abs()
print("Notebook (kpi.csv) contre ligne de commande (kpi_cli.csv), écart absolu par KPI et par année :")
print(ecarts.to_string())
total = float(ecarts.to_numpy().sum())
print(f"{ecarts.size} valeurs comparées, somme des écarts = {total}")
if total != 0:
    print("ECHEC : le calcul n'est pas reproductible")
    sys.exit(1)
print("OK : calcul reproductible, résultats identiques")
