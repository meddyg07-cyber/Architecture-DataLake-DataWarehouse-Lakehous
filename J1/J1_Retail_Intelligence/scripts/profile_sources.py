"""UC-01 - Inventaire et qualification des sources TPCx-BB.

Usage : python profile_sources.py <racine_retail_project> <dossier_preuves>

Produit dans <dossier_preuves> :
  arborescence.txt, apercu_fichiers.txt, inventaire_fichiers.csv, colonnes.csv,
  controles_cles.csv, controles_relations.csv, controles_qualite.csv, profil_log.txt
Aucune donnee source n'est modifiee.
"""
import csv
import hashlib
import os
import sys
import time
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from J1.J1_Retail_Intelligence.scripts.schema_tpcxbb import SCHEMA, DOMAIN  # noqa: E402

ROOT = Path(sys.argv[1])
OUT = Path(sys.argv[2])
OUT.mkdir(parents=True, exist_ok=True)
LOG = open(OUT / "profil_log.txt", "w", encoding="utf-8")
CHUNK = 1_000_000
BIG = 2_000_000  # au-dela : distinct calcule sur le 1er bloc seulement


def log(msg):
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    LOG.write(line + "\n")


def human(n):
    for u in ["o", "Ko", "Mo", "Go"]:
        if n < 1024:
            return f"{n:.1f} {u}"
        n /= 1024
    return f"{n:.1f} To"


def infer_type(s: pd.Series) -> str:
    s = s[s != ""]
    if s.empty:
        return "vide"
    s = s.head(50_000)
    checks = [("entier", r"-?\d+"), ("decimal", r"-?\d+\.\d+"), ("date", r"\d{4}-\d{2}-\d{2}"),
              ("heure", r"\d{2}:\d{2}:\d{2}")]
    for name, rx in checks:
        if s.str.fullmatch(rx).all():
            return name
    if s.str.fullmatch(r"-?\d+(\.\d+)?").all():
        return "decimal"
    if s.isin(["Y", "N"]).all():
        return "booleen (Y/N)"
    return "texte"


# ---------------------------------------------------------------- 1. arborescence
files = sorted(p for p in ROOT.rglob("*") if p.is_file())
with open(OUT / "arborescence.txt", "w", encoding="utf-8") as f:
    f.write(f"Racine : {ROOT}\n\n")
    for p in files:
        f.write(f"{str(p.relative_to(ROOT)):<62} {p.stat().st_size:>12} octets  ({human(p.stat().st_size)})\n")
    tot = sum(p.stat().st_size for p in files)
    f.write(f"\nTotal : {len(files)} fichiers, {tot} octets ({human(tot)})\n")
log(f"{len(files)} fichiers trouves")

# ---------------------------------------------------------------- 2. inventaire + colonnes
inv_rows, col_rows, preview = [], [], []
for p in files:
    rel = p.relative_to(ROOT)
    lot = rel.parts[0]
    table = rel.parts[1] if len(rel.parts) > 2 else p.stem
    t0 = time.time()
    h = hashlib.md5()
    fc, nlines, crlf, bad_utf8, head = Counter(), 0, 0, 0, []
    with open(p, "rb") as fh:
        for l in fh:
            h.update(l)
            nlines += 1
            if l.endswith(b"\r\n"):
                crlf += 1
            fc[l.count(b"|") + 1] += 1
            try:
                l.decode("utf-8")
            except UnicodeDecodeError:
                bad_utf8 += 1
            if nlines <= 3:
                head.append(l)
    md5 = h.hexdigest()
    enc = "UTF-8 valide" if bad_utf8 == 0 else f"non UTF-8 ({bad_utf8} lignes)"
    preview.append(f"===== {rel} =====\n" + "\n".join(
        l.decode("utf-8", "replace").rstrip("\r\n")[:300] for l in head) + "\n")

    if p.suffix == ".csv":
        inv_rows.append(dict(lot=lot, table=table, fichier=p.name, chemin=str(rel), format="CSV (virgule, CRLF)",
                             taille_octets=p.stat().st_size, taille=human(p.stat().st_size), lignes=nlines,
                             nb_colonnes="variable", nb_champs_observes="variable",
                             entete="oui (texte de rapport)", encodage=enc,
                             fin_de_ligne="CRLF" if crlf else "LF", md5=md5, schema_applique="non",
                             domaine="Produits / audit generation prix"))
        continue

    schema = SCHEMA.get(table)
    main_fc = fc.most_common(1)[0][0]
    schema_ok = schema is not None and len(schema) == main_fc
    names = schema if schema_ok else [f"col_{i+1}" for i in range(main_fc)]

    # lecture pandas en texte, par blocs
    nulls = np.zeros(main_fc, dtype=np.int64)
    mins = [None] * main_fc
    maxs = [None] * main_fc
    distinct = [set() for _ in range(main_fc)]
    types, examples = [None] * main_fc, [""] * main_fc
    first = True
    reader = pd.read_csv(p, sep="|", header=None, names=names, dtype=str, keep_default_na=False,
                         na_filter=False, quoting=3, chunksize=CHUNK, encoding="utf-8",
                         encoding_errors="replace", on_bad_lines="warn", engine="c")
    nrows = 0
    for ch in reader:
        nrows += len(ch)
        nulls += (ch == "").sum().to_numpy()
        for i, c in enumerate(names):
            if first:
                types[i] = infer_type(ch[c])
                nz = ch[c][ch[c] != ""]
                examples[i] = nz.iloc[0][:60] if len(nz) else ""
            if types[i] in ("entier", "decimal"):
                v = pd.to_numeric(ch[c].replace("", np.nan), errors="coerce")
                if v.notna().any():
                    mins[i] = v.min() if mins[i] is None else min(mins[i], v.min())
                    maxs[i] = v.max() if maxs[i] is None else max(maxs[i], v.max())
            elif types[i] in ("date", "heure"):
                nz = ch[c][ch[c] != ""]
                if len(nz):
                    mins[i] = nz.min() if mins[i] is None else min(mins[i], nz.min())
                    maxs[i] = nz.max() if maxs[i] is None else max(maxs[i], nz.max())
            if first or nrows <= BIG:
                if types[i] != "texte" or len(distinct[i]) < 200_000:
                    distinct[i].update(ch[c].unique())
        first = False
    sampled = nrows > BIG
    for i, c in enumerate(names):
        col_rows.append(dict(
            lot=lot, table=table, position=i + 1, colonne=c,
            statut_nom="Deduit (schema TPCx-BB)" if schema_ok else "Inconnu (pas de schema)",
            type_observe=types[i], nb_vides=int(nulls[i]),
            pct_vides=round(100 * nulls[i] / nrows, 2) if nrows else 0,
            nb_distinct=len(distinct[i] - {""}) if (types[i] != "texte" or len(distinct[i]) < 200_000) else ">=200000",
            distinct_sur="1er bloc 1M lignes" if sampled else "fichier complet",
            min=mins[i], max=maxs[i], exemple=examples[i]))
    inv_rows.append(dict(
        lot=lot, table=table, fichier=p.name, chemin=str(rel), format="Texte delimite '|' sans en-tete",
        taille_octets=p.stat().st_size, taille=human(p.stat().st_size), lignes=nlines,
        nb_colonnes=main_fc,
        nb_champs_observes="; ".join(f"{k} champs: {v} lignes" for k, v in sorted(fc.items())),
        entete="non", encodage=enc, fin_de_ligne="CRLF" if crlf else "LF", md5=md5,
        schema_applique="oui" if schema_ok else f"NON (attendu {len(schema) if schema else '?'})",
        domaine=DOMAIN.get(table, "?")))
    log(f"{rel}: {nlines} lignes, {main_fc} col, champs={dict(fc)}, schema_ok={schema_ok}, {time.time()-t0:.1f}s")


def write_csv(name, rows):
    if not rows:
        return
    with open(OUT / name, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()), delimiter=";")
        w.writeheader()
        w.writerows(rows)


write_csv("inventaire_fichiers.csv", inv_rows)
write_csv("colonnes.csv", col_rows)
(OUT / "apercu_fichiers.txt").write_text("\n".join(preview), encoding="utf-8")

# ---------------------------------------------------------------- 3. cles et relations
def load(lot, table, cols, dtype="float64"):
    p = ROOT / lot / table / f"{table}.dat"
    if not p.exists():
        return None
    names = SCHEMA[table]
    return pd.read_csv(p, sep="|", header=None, names=names, usecols=cols, quoting=3,
                       dtype={c: dtype for c in cols}, engine="c")


key_rows, rel_rows, q_rows = [], [], []


def q(table, lot, controle, valeur, total=None, commentaire=""):
    q_rows.append(dict(lot=lot, table=table, controle=controle, valeur=valeur,
                       total=total, pct=round(100 * valeur / total, 3) if total else "",
                       commentaire=commentaire))


# cles primaires des dimensions (data et data_refresh)
DIM_PK = {"date_dim": "d_date_sk", "time_dim": "t_time_sk", "item": "i_item_sk", "store": "s_store_sk",
          "customer": "c_customer_sk", "customer_address": "ca_address_sk",
          "customer_demographics": "cd_demo_sk", "household_demographics": "hd_demo_sk",
          "income_band": "ib_income_band_sk", "promotion": "p_promo_sk", "reason": "r_reason_sk",
          "ship_mode": "sm_ship_mode_sk", "warehouse": "w_warehouse_sk", "web_page": "wp_web_page_sk",
          "web_site": "web_site_sk", "item_marketprices": "imp_sk", "product_reviews": "pr_review_sk"}
dimkeys = {}
for t, k in DIM_PK.items():
    allk = []
    for lot in ("data", "data_refresh"):
        d = load(lot, t, [k])
        if d is None:
            continue
        s = d[k]
        allk.append(s)
        key_rows.append(dict(lot=lot, table=t, cle=k, lignes=len(s), nulls=int(s.isna().sum()),
                             distinct=int(s.nunique()), doublons=int(s.duplicated().sum()),
                             min=s.min(), max=s.max(),
                             unique="oui" if s.notna().all() and not s.duplicated().any() else "NON"))
    if allk:
        u = pd.concat(allk)
        dimkeys[t] = set(u.dropna().astype(np.int64))
        key_rows.append(dict(lot="data + data_refresh", table=t, cle=k, lignes=len(u),
                             nulls=int(u.isna().sum()), distinct=int(u.nunique()),
                             doublons=int(u.duplicated().sum()), min=u.min(), max=u.max(),
                             unique="oui" if not u.duplicated().any() else "NON (chevauchement des lots)"))
log("cles des dimensions controlees")

# date_dim pour convertir les *_date_sk
dd = load("data", "date_dim", ["d_date_sk", "d_date"], dtype=str)
dd["d_date_sk"] = dd["d_date_sk"].astype(np.int64)
DATE = dict(zip(dd["d_date_sk"], dd["d_date"]))


def sk2date(v):
    return DATE.get(int(v), "?") if pd.notna(v) else ""


FK = {
    "store_sales": {"ss_sold_date_sk": "date_dim", "ss_sold_time_sk": "time_dim", "ss_item_sk": "item",
                    "ss_customer_sk": "customer", "ss_cdemo_sk": "customer_demographics",
                    "ss_hdemo_sk": "household_demographics", "ss_addr_sk": "customer_address",
                    "ss_store_sk": "store", "ss_promo_sk": "promotion"},
    "web_sales": {"ws_sold_date_sk": "date_dim", "ws_sold_time_sk": "time_dim", "ws_ship_date_sk": "date_dim",
                  "ws_item_sk": "item", "ws_bill_customer_sk": "customer",
                  "ws_bill_cdemo_sk": "customer_demographics", "ws_bill_addr_sk": "customer_address",
                  "ws_web_page_sk": "web_page", "ws_web_site_sk": "web_site", "ws_ship_mode_sk": "ship_mode",
                  "ws_warehouse_sk": "warehouse", "ws_promo_sk": "promotion"},
    "store_returns": {"sr_returned_date_sk": "date_dim", "sr_item_sk": "item", "sr_customer_sk": "customer",
                      "sr_store_sk": "store", "sr_reason_sk": "reason"},
    "web_returns": {"wr_returned_date_sk": "date_dim", "wr_item_sk": "item",
                    "wr_returning_customer_sk": "customer", "wr_web_page_sk": "web_page",
                    "wr_reason_sk": "reason"},
    "inventory": {"inv_date_sk": "date_dim", "inv_item_sk": "item", "inv_warehouse_sk": "warehouse"},
    "web_clickstreams": {"wcs_click_date_sk": "date_dim", "wcs_click_time_sk": "time_dim",
                         "wcs_item_sk": "item", "wcs_web_page_sk": "web_page", "wcs_user_sk": "customer"},
    "product_reviews": {"pr_item_sk": "item", "pr_user_sk": "customer"},
    "item_marketprices": {"imp_item_sk": "item", "imp_start_date": "date_dim", "imp_end_date": "date_dim"},
    "household_demographics": {"hd_income_band_sk": "income_band"},
    "promotion": {"p_item_sk": "item", "p_start_date_sk": "date_dim", "p_end_date_sk": "date_dim"},
}

facts = {}
for t, fks in FK.items():
    for lot in ("data", "data_refresh"):
        cols = list(fks)
        extra = {"store_sales": ["ss_ticket_number", "ss_quantity", "ss_sales_price", "ss_list_price",
                                 "ss_ext_sales_price", "ss_net_paid", "ss_net_profit", "ss_ext_discount_amt",
                                 "ss_ext_list_price"],
                 "web_sales": ["ws_order_number", "ws_quantity", "ws_sales_price", "ws_list_price",
                               "ws_ext_sales_price", "ws_net_paid", "ws_net_profit", "ws_ext_discount_amt",
                               "ws_ext_list_price"],
                 "store_returns": ["sr_ticket_number", "sr_return_quantity", "sr_return_amt"],
                 "web_returns": ["wr_order_number", "wr_return_quantity", "wr_return_amt"],
                 "inventory": ["inv_quantity_on_hand"],
                 "web_clickstreams": ["wcs_sales_sk"],
                 "product_reviews": ["pr_review_rating", "pr_order_sk"],
                 "item_marketprices": ["imp_competitor_price"]}.get(t, [])
        df = load(lot, t, cols + extra, dtype="float32" if t == "inventory" else "float64")
        if df is None:
            continue
        facts[(lot, t)] = df
        n = len(df)
        for c, dim in fks.items():
            s = df[c]
            nn = s.dropna()
            if dim in dimkeys:
                keys = np.fromiter(dimkeys[dim], dtype=np.int64)
                orphan = int((~nn.astype(np.int64).isin(keys)).sum())
                dimtxt = dim + (" (data_refresh uniquement)" if dim in ("customer", "customer_address") else "")
            else:
                orphan, dimtxt = None, dim + " (absente)"
            rel_rows.append(dict(
                lot=lot, table_source=t, colonne=c, table_cible=dimtxt, cle_cible=DIM_PK.get(dim, "?"),
                lignes=n, nulls=int(s.isna().sum()), pct_nulls=round(100 * s.isna().mean(), 2),
                distinct=int(nn.nunique()), sans_correspondance=orphan,
                pct_sans_correspondance=round(100 * orphan / len(nn), 2) if orphan is not None and len(nn) else "",
                min=nn.min() if len(nn) else "", max=nn.max() if len(nn) else "",
                periode=f"{sk2date(nn.min())} -> {sk2date(nn.max())}" if dim == "date_dim" and len(nn) else "",
                statut=("Verifie (100% correspondance)" if orphan == 0 else
                        "A confirmer (orphelins)" if orphan else "Non verifiable")))
        log(f"relations {lot}/{t} controlees ({n} lignes)")

# ---------------------------------------------------------------- 4. controles qualite metier
for lot in ("data", "data_refresh"):
    ss = facts.get((lot, "store_sales"))
    if ss is not None:
        n = len(ss)
        q("store_sales", lot, "Lignes (granularite : 1 ligne = 1 article d'un ticket)", n)
        q("store_sales", lot, "Tickets distincts (ss_ticket_number)", int(ss.ss_ticket_number.nunique()),
          commentaire="Base du nombre de transactions")
        q("store_sales", lot, "Lignes par ticket (moyenne)",
          round(n / max(ss.ss_ticket_number.nunique(), 1), 2))
        q("store_sales", lot, "Doublons (ticket, article)",
          int(ss.duplicated(["ss_ticket_number", "ss_item_sk"]).sum()), n)
        q("store_sales", lot, "Quantite vide", int(ss.ss_quantity.isna().sum()), n)
        q("store_sales", lot, "Quantite <= 0", int((ss.ss_quantity <= 0).sum()), n)
        q("store_sales", lot, "Prix de vente vide", int(ss.ss_sales_price.isna().sum()), n)
        q("store_sales", lot, "Prix de vente > prix catalogue", int((ss.ss_sales_price > ss.ss_list_price).sum()), n)
        ecart = (ss.ss_ext_sales_price - ss.ss_sales_price * ss.ss_quantity).abs() > 0.011
        q("store_sales", lot, "ext_sales_price != sales_price x quantite", int(ecart.sum()), n,
          "Coherence interne du montant de ligne")
        q("store_sales", lot, "Marge nette negative (ss_net_profit < 0)", int((ss.ss_net_profit < 0).sum()), n,
          "Possible (remise, coupon) : a interpreter, pas une erreur")
        q("store_sales", lot, "CA total ss_ext_sales_price", round(float(ss.ss_ext_sales_price.sum()), 2),
          commentaire="Unite monetaire non documentee")
        q("store_sales", lot, "CA total ss_net_paid", round(float(ss.ss_net_paid.sum()), 2))
        q("store_sales", lot, "Remises totales ss_ext_discount_amt", round(float(ss.ss_ext_discount_amt.sum()), 2))
        q("store_sales", lot, "Ventes sans client (ss_customer_sk vide)", int(ss.ss_customer_sk.isna().sum()), n)
    ws = facts.get((lot, "web_sales"))
    if ws is not None:
        n = len(ws)
        q("web_sales", lot, "Lignes (granularite : 1 ligne = 1 article d'une commande)", n)
        q("web_sales", lot, "Commandes distinctes (ws_order_number)", int(ws.ws_order_number.nunique()))
        q("web_sales", lot, "Lignes par commande (moyenne)", round(n / max(ws.ws_order_number.nunique(), 1), 2))
        q("web_sales", lot, "Doublons (commande, article)",
          int(ws.duplicated(["ws_order_number", "ws_item_sk"]).sum()), n)
        q("web_sales", lot, "Quantite vide", int(ws.ws_quantity.isna().sum()), n)
        q("web_sales", lot, "Quantite <= 0", int((ws.ws_quantity <= 0).sum()), n)
        q("web_sales", lot, "Prix de vente > prix catalogue", int((ws.ws_sales_price > ws.ws_list_price).sum()), n)
        ecart = (ws.ws_ext_sales_price - ws.ws_sales_price * ws.ws_quantity).abs() > 0.011
        q("web_sales", lot, "ext_sales_price != sales_price x quantite", int(ecart.sum()), n)
        q("web_sales", lot, "Expedition avant vente (ship_date < sold_date)",
          int((ws.ws_ship_date_sk < ws.ws_sold_date_sk).sum()), n)
        q("web_sales", lot, "Marge nette negative", int((ws.ws_net_profit < 0).sum()), n)
        q("web_sales", lot, "CA total ws_ext_sales_price", round(float(ws.ws_ext_sales_price.sum()), 2))
        q("web_sales", lot, "CA total ws_net_paid", round(float(ws.ws_net_paid.sum()), 2))
        q("web_sales", lot, "Ventes sans client (ws_bill_customer_sk vide)", int(ws.ws_bill_customer_sk.isna().sum()), n)
    for rt, st, num, rnum, item, ritem in (("store_returns", "store_sales", "ss_ticket_number", "sr_ticket_number",
                                             "ss_item_sk", "sr_item_sk"),
                                            ("web_returns", "web_sales", "ws_order_number", "wr_order_number",
                                             "ws_item_sk", "wr_item_sk")):
        r = facts.get((lot, rt))
        if r is None:
            continue
        n = len(r)
        qty = rt[:1] + "r_return_quantity" if rt == "store_returns" else "wr_return_quantity"
        q(rt, lot, "Lignes", n)
        q(rt, lot, "Quantite retournee <= 0", int((r[qty] <= 0).sum()), n)
        q(rt, lot, "Doublons (ticket/commande, article)", int(r.duplicated([rnum, ritem]).sum()), n)
        sales = pd.concat([facts[(l, st)][[num, item]] for l in ("data", "data_refresh") if (l, st) in facts])
        m = r[[rnum, ritem]].merge(sales.drop_duplicates(), left_on=[rnum, ritem], right_on=[num, item],
                                   how="left", indicator=True)
        q(rt, lot, f"Retour sans vente correspondante dans {st} (data+refresh)",
          int((m["_merge"] == "left_only").sum()), n, f"Jointure ({rnum},{ritem}) -> ({num},{item})")
    inv = facts.get((lot, "inventory"))
    if inv is not None:
        n = len(inv)
        q("inventory", lot, "Lignes (granularite : date x article x entrepot)", n)
        q("inventory", lot, "Quantite en stock vide", int(inv.inv_quantity_on_hand.isna().sum()), n)
        q("inventory", lot, "Quantite en stock < 0", int((inv.inv_quantity_on_hand < 0).sum()), n)
        q("inventory", lot, "Dates d'inventaire distinctes", int(inv.inv_date_sk.nunique()),
          commentaire="Photos de stock periodiques (pas des mouvements)")
        d = np.sort(inv.inv_date_sk.dropna().unique())
        if len(d) > 1:
            q("inventory", lot, "Ecart le plus frequent entre 2 dates (jours)",
              int(pd.Series(np.diff(d)).mode()[0]))
        key = (inv.inv_date_sk.astype(np.int64) * 1_000_000 + inv.inv_item_sk.astype(np.int64) * 100
               + inv.inv_warehouse_sk.astype(np.int64))
        q("inventory", lot, "Doublons (date, article, entrepot)", int(key.duplicated().sum()), n)
        del key
    wc = facts.get((lot, "web_clickstreams"))
    if wc is not None:
        n = len(wc)
        q("web_clickstreams", lot, "Clics", n)
        q("web_clickstreams", lot, "Clics lies a une vente (wcs_sales_sk renseigne)", int(wc.wcs_sales_sk.notna().sum()), n,
          "Seuls ces clics peuvent etre relies a un achat")
        q("web_clickstreams", lot, "Clics anonymes (wcs_user_sk vide)", int(wc.wcs_user_sk.isna().sum()), n)
        q("web_clickstreams", lot, "Clics sans article (wcs_item_sk vide)", int(wc.wcs_item_sk.isna().sum()), n)
        if (lot, "web_sales") in facts:
            ws_orders = set(pd.concat([facts[(l, "web_sales")].ws_order_number for l in ("data", "data_refresh")
                                       if (l, "web_sales") in facts]).dropna().astype(np.int64))
            s = wc.wcs_sales_sk.dropna().astype(np.int64)
            q("web_clickstreams", lot, "wcs_sales_sk absent de ws_order_number (hypothese de jointure)",
              int((~s.isin(ws_orders)).sum()), len(s), "Hypothese : wcs_sales_sk = ws_order_number")
    pr = facts.get((lot, "product_reviews"))
    if pr is not None:
        n = len(pr)
        q("product_reviews", lot, "Avis", n)
        q("product_reviews", lot, "Note hors [1;5]", int(((pr.pr_review_rating < 1) | (pr.pr_review_rating > 5)).sum()), n)
        q("product_reviews", lot, "Avis sans utilisateur", int(pr.pr_user_sk.isna().sum()), n)

# item : historisation (SCD) - plusieurs sk pour un meme i_item_id ?
it = pd.concat([pd.read_csv(ROOT / l / "item" / "item.dat", sep="|", header=None, names=SCHEMA["item"],
                            usecols=["i_item_sk", "i_item_id", "i_rec_start_date", "i_rec_end_date",
                                     "i_category", "i_current_price"], dtype=str, quoting=3,
                            keep_default_na=False).assign(lot=l) for l in ("data", "data_refresh")])
q("item", "data + data_refresh", "Articles (i_item_sk)", len(it))
q("item", "data + data_refresh", "Identifiants metier distincts (i_item_id)", int(it.i_item_id.nunique()),
  commentaire="Si < nb de sk : plusieurs versions d'un meme article (historisation)")
q("item", "data + data_refresh", "Versions fermees (i_rec_end_date renseigne)", int((it.i_rec_end_date != "").sum()), len(it))
q("item", "data + data_refresh", "Categorie vide", int((it.i_category == "").sum()), len(it))
q("item", "data + data_refresh", "Categories distinctes", int(it[it.i_category != ""].i_category.nunique()),
  commentaire=", ".join(sorted(it[it.i_category != ""].i_category.unique())[:15]))
q("item", "data + data_refresh", "Prix courant vide", int((it.i_current_price == "").sum()), len(it))

st = pd.read_csv(ROOT / "data" / "store" / "store.dat", sep="|", header=None, names=SCHEMA["store"], dtype=str,
                 keep_default_na=False, quoting=3)
q("store", "data", "Magasins (lignes)", len(st))
q("store", "data", "Identifiants metier distincts (s_store_id)", int(st.s_store_id.nunique()))
q("store", "data", "Etats distincts (s_state)", int(st[st.s_state != ""].s_state.nunique()),
  commentaire=", ".join(sorted(st[st.s_state != ""].s_state.unique())))
q("store", "data", "Magasins fermes (s_closed_date_sk renseigne)", int((st.s_closed_date_sk != "").sum()), len(st))

write_csv("controles_cles.csv", key_rows)
write_csv("controles_relations.csv", rel_rows)
write_csv("controles_qualite.csv", q_rows)
log("termine")
LOG.close()
