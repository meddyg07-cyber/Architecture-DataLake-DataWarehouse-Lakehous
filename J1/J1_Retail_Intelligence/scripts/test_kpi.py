"""UC-01 - Test de calculabilite des KPI sur le lot principal (data/).

Usage : python test_kpi.py <racine_retail_project> <dossier_preuves>
Ecrit kpi_test_par_annee_canal.csv, kpi_test_par_magasin.csv, kpi_test_par_categorie.csv.
Les montants sont exprimes dans l'unite monetaire du jeu (non documentee).
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from J1.J1_Retail_Intelligence.scripts.schema_tpcxbb import SCHEMA  # noqa: E402

ROOT, OUT = Path(sys.argv[1]), Path(sys.argv[2])


def load(t, cols, lot="data"):
    return pd.read_csv(ROOT / lot / t / f"{t}.dat", sep="|", header=None, names=SCHEMA[t], usecols=cols,
                       quoting=3)


dd = load("date_dim", ["d_date_sk", "d_year"]).set_index("d_date_sk")["d_year"]
it = load("item", ["i_item_sk", "i_category"]).set_index("i_item_sk")["i_category"]
st = load("store", ["s_store_sk", "s_store_name", "s_state"]).set_index("s_store_sk")

ss = load("store_sales", ["ss_sold_date_sk", "ss_item_sk", "ss_store_sk", "ss_ticket_number", "ss_quantity",
                          "ss_ext_sales_price", "ss_ext_list_price", "ss_ext_discount_amt", "ss_net_paid",
                          "ss_net_profit"])
ss.columns = [c.replace("ss_", "") for c in ss.columns]
ss = ss.rename(columns={"sold_date_sk": "date_sk", "ticket_number": "txn"})
ss["canal"] = "magasin"
ws = load("web_sales", ["ws_sold_date_sk", "ws_item_sk", "ws_order_number", "ws_quantity", "ws_ext_sales_price",
                        "ws_ext_list_price", "ws_ext_discount_amt", "ws_net_paid", "ws_net_profit"])
ws.columns = [c.replace("ws_", "") for c in ws.columns]
ws = ws.rename(columns={"sold_date_sk": "date_sk", "order_number": "txn"})
ws["canal"] = "web"
sales = pd.concat([ss, ws], ignore_index=True)
sales["annee"] = sales.date_sk.map(dd)
sales["categorie"] = sales.item_sk.map(it)

sr = load("store_returns", ["sr_returned_date_sk", "sr_return_amt"]).assign(canal="magasin")
sr.columns = ["date_sk", "return_amt", "canal"]
wr = load("web_returns", ["wr_returned_date_sk", "wr_return_amt"]).assign(canal="web")
wr.columns = ["date_sk", "return_amt", "canal"]
ret = pd.concat([sr, wr])
ret["annee"] = ret.date_sk.map(dd)


def kpi(g):
    return pd.Series({
        "CA_brut (ext_sales_price)": round(g.ext_sales_price.sum(), 2),
        "CA_net_paye (net_paid)": round(g.net_paid.sum(), 2),
        "Nb_transactions": g.txn.nunique(),
        "Nb_lignes": len(g),
        "Quantites_vendues": int(g.quantity.sum()),
        "Panier_moyen": round(g.ext_sales_price.sum() / g.txn.nunique(), 2),
        "Taux_remise_%": round(100 * g.ext_discount_amt.sum() / g.ext_list_price.sum(), 2),
        "Marge_nette": round(g.net_profit.sum(), 2),
    })


by = sales.groupby(["annee", "canal"]).apply(kpi, include_groups=False).reset_index()
by["Evolution_CA_vs_N-1_%"] = by.groupby("canal")["CA_brut (ext_sales_price)"].pct_change().mul(100).round(2)
r = ret.groupby(["annee", "canal"]).return_amt.sum().rename("Montant_retours (date de retour)").round(2)
by = by.merge(r, on=["annee", "canal"], how="left")
by.to_csv(OUT / "kpi_test_par_annee_canal.csv", sep=";", index=False, encoding="utf-8-sig")

m = ss.assign(**{"magasin": ss.store_sk.map(st.s_store_name), "etat": ss.store_sk.map(st.s_state)})
m = m.groupby(["store_sk", "magasin", "etat"]).apply(kpi, include_groups=False).reset_index()
m.sort_values("CA_brut (ext_sales_price)", ascending=False).to_csv(
    OUT / "kpi_test_par_magasin.csv", sep=";", index=False, encoding="utf-8-sig")

c = sales.groupby(["categorie", "canal"]).apply(kpi, include_groups=False).reset_index()
c.sort_values("CA_brut (ext_sales_price)", ascending=False).to_csv(
    OUT / "kpi_test_par_categorie.csv", sep=";", index=False, encoding="utf-8-sig")
print(by.to_string())
print(m.to_string())
print(c.head(6).to_string())
