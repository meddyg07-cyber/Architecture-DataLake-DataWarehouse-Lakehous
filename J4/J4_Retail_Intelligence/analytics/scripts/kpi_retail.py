"""KPI du TP J4 (UC-08) : une seule définition, utilisée par le notebook et par la ligne de commande.

Les formules reprennent le dictionnaire des KPI du J1 (UC01_dictionnaire_KPI.xlsx), restreint au canal magasin :
c'est le seul canal présent en Silver (web_sales n'a pas été transformé au J3).

Usage en ligne de commande (automatisation, partie avancée AV-01) :
    python analytics/scripts/kpi_retail.py --axes annee --annees 2001-2004 --sortie analytics/outputs/kpi_cli.csv
    python analytics/scripts/kpi_retail.py --axes annee,categorie --periode-egale
"""
from __future__ import annotations

import argparse
import os
import sys
from decimal import Decimal

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F

# ---------------------------------------------------------------- paramètres (séparés du traitement)
HDFS = os.environ.get("TP4_HDFS", "hdfs://localhost:9000")
SILVER = f"{HDFS}/retail-lake/silver/tpcxbb"
GOLD = f"{HDFS}/retail-lake/gold/retail"
DERNIER_JOUR_OBSERVE = (12, 13)     # 13/12/2005 : dernier jour de vente du lot initial (constat J3)
ANNEES_COMPLETES = (2001, 2004)     # 2005 est incomplète : les comparaisons annuelles portent sur 2001-2004

# axe demandé -> colonne réelle (après enrichissement)
AXES = {
    "annee": "sold_year",
    "mois": "sold_month",
    "magasin": "magasin",
    "categorie": "i_category",
}


def spark_session(app: str = "TP4-Retail-Intelligence") -> SparkSession:
    return (
        SparkSession.builder.appName(app)
        .master("local[*]")
        .config("spark.sql.shuffle.partitions", "12")
        .config("spark.sql.session.timeZone", "Europe/Paris")
        .config("spark.ui.showConsoleProgress", "false")
        .getOrCreate()
    )


def charger_ventes(spark: SparkSession) -> DataFrame:
    """Silver store_sales enrichi de la catégorie (item) et du magasin (store). Jointures gauches, vérifiées au J3."""
    ventes = spark.read.parquet(f"{SILVER}/store_sales")
    item = spark.read.parquet(f"{SILVER}/item").select("i_item_sk", "i_category")
    store = spark.read.parquet(f"{SILVER}/store").select(
        "s_store_sk", F.concat_ws(" ", "s_store_name", F.concat(F.lit("("), "s_state", F.lit(")"))).alias("magasin")
    )
    return (
        ventes.join(F.broadcast(item), ventes.ss_item_sk == item.i_item_sk, "left")
        .join(F.broadcast(store), ventes.ss_store_sk == store.s_store_sk, "left")
    )


def periode_egale(df: DataFrame) -> DataFrame:
    """Garde du 01/01 au 13/12 de chaque année, pour comparer 2005 aux autres années à période égale."""
    mois, jour = DERNIER_JOUR_OBSERVE
    return df.filter((F.col("sold_month") < mois) | ((F.col("sold_month") == mois) & (F.dayofmonth("sold_date") <= jour)))


def kpis(df: DataFrame, axes: list[str]) -> DataFrame:
    """Calcule les KPI-01 à KPI-05 du dictionnaire au grain demandé.

    KPI-01a CA brut       = SUM(ss_ext_sales_price)              (après remise, avant coupons, hors taxe, avant retours)
    KPI-01b CA net payé   = SUM(ss_net_paid)                     (= CA brut - coupons ; mesure du Gold J3)
    KPI-02  Transactions  = COUNT(DISTINCT magasin, ticket)      (1 ticket = 1 magasin, 1 date, 1 client : vérifié)
    KPI-03  Panier moyen  = KPI-01 / KPI-02                      (net et brut)
    KPI-04  Quantités     = SUM(ss_quantity)
    KPI-05  Taux de remise = SUM(ss_ext_discount_amt) / SUM(ss_ext_list_price)
    """
    cols = [AXES[a] for a in axes]
    out = (
        df.groupBy(*cols)
        .agg(
            F.sum("ss_ext_sales_price").alias("ca_brut"),
            F.sum("ss_net_paid").alias("ca_net_paye"),
            F.countDistinct("ss_store_sk", "ss_ticket_number").alias("nb_transactions"),
            F.count("*").alias("nb_lignes"),
            F.sum("ss_quantity").alias("quantites"),
            F.sum("ss_ext_discount_amt").alias("_remise"),
            F.sum("ss_ext_list_price").alias("_prix_catalogue"),
        )
        .withColumn("panier_moyen_net", F.round(F.col("ca_net_paye") / F.col("nb_transactions"), 2))
        .withColumn("panier_moyen_brut", F.round(F.col("ca_brut") / F.col("nb_transactions"), 2))
        .withColumn("lignes_par_transaction", F.round(F.col("nb_lignes") / F.col("nb_transactions"), 2))
        .withColumn("taux_remise_pct", F.round(100 * F.col("_remise") / F.col("_prix_catalogue"), 2))
        .drop("_remise", "_prix_catalogue")
    )
    for a, c in zip(axes, cols):
        out = out.withColumnRenamed(c, a)
    return out.orderBy(*axes)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Calcule les KPI magasin du Silver et les exporte en CSV.")
    p.add_argument("--axes", default="annee", help=f"axes séparés par des virgules parmi {sorted(AXES)}")
    p.add_argument("--annees", default="2001-2005", help="intervalle d'années, ex. 2001-2004")
    p.add_argument("--periode-egale", action="store_true", help="limiter chaque année au 01/01-13/12")
    p.add_argument("--sortie", default="analytics/outputs/kpi_cli.csv")
    a = p.parse_args(argv)

    axes = [x.strip() for x in a.axes.split(",") if x.strip()]
    inconnus = [x for x in axes if x not in AXES]
    if inconnus:
        p.error(f"axe inconnu : {inconnus}")
    debut, fin = (int(x) for x in a.annees.split("-"))

    spark = spark_session("TP4-KPI-CLI")
    df = charger_ventes(spark).filter(F.col("sold_year").between(debut, fin))
    if a.periode_egale:
        df = periode_egale(df)
    res = kpis(df, axes).toPandas()     # résultat agrégé : quelques dizaines de lignes au plus
    for c in res.columns:               # decimal exact de Spark -> float pour un CSV au format français
        if res[c].map(lambda v: isinstance(v, Decimal)).any():
            res[c] = res[c].astype(float)
    os.makedirs(os.path.dirname(a.sortie) or ".", exist_ok=True)
    res.to_csv(a.sortie, index=False, sep=";", decimal=",")
    print(f"Paramètres : axes={axes} années={debut}-{fin} période_égale={a.periode_egale}")
    print(res.to_string(index=False))
    print(f"{len(res)} lignes écrites dans {a.sortie}")
    spark.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
