"""Étape 8 – Comparaison des formats CSV, JSON et Parquet sur les mêmes données (UC-06).

Mesures réelles, faites sur ce poste (indicatives : mode local, 1 machine, cache disque de l'OS) :
  1. volume de stockage de store_sales en .dat (CSV |), CSV avec en-tête, JSON, Parquet (Bronze texte, Silver typé)
  2. types relus SANS fournir de schéma (ce que chaque format conserve)
  3. temps d'une agrégation (CA par magasin) qui n'a besoin que de 2 colonnes sur 23
Les copies CSV/JSON sont écrites dans /retail-lake/logs/tp3/formats (zone technique), jamais dans Silver/Gold.

Usage : bash scripts/tp3.sh python transformations/05_formats.py
"""
import statistics
import time

from pyspark.sql import functions as F

import common as C

ESSAIS = 5


def chrono(fn):
    mesures = []
    for _ in range(ESSAIS):
        t0 = time.perf_counter()
        fn()
        mesures.append(time.perf_counter() - t0)
    return round(statistics.median(mesures), 3), [round(m, 3) for m in mesures]


def main():
    spark = C.spark_session("TP3-05-Formats")
    base = f"{C.LOGS}/formats"
    silver = spark.read.parquet(f"{C.SILVER}/store_sales")
    metier = [c for c, _ in C.SOURCES["store_sales"]]
    ventes = silver.select(*metier)

    ventes.write.mode("overwrite").option("header", True).csv(f"{base}/store_sales_csv")
    ventes.write.mode("overwrite").json(f"{base}/store_sales_json")
    ventes.write.mode("overwrite").parquet(f"{base}/store_sales_parquet")   # mêmes 23 colonnes, sans partition

    volumes = {
        "dat_raw (CSV |, sans en-tete)": C.hdfs_du(spark, C.raw_path("store_sales")),
        "csv (en-tete, ,)": C.hdfs_du(spark, f"{base}/store_sales_csv"),
        "json (1 objet par ligne)": C.hdfs_du(spark, f"{base}/store_sales_json"),
        "parquet bronze (texte + provenance)": C.hdfs_du(spark, f"{C.BRONZE}/store_sales"),
        "parquet silver (typé, partitionné, + indicateurs)": C.hdfs_du(spark, f"{C.SILVER}/store_sales"),
        "parquet 23 colonnes typées (snappy)": C.hdfs_du(spark, f"{base}/store_sales_parquet"),
    }
    ref = volumes["dat_raw (CSV |, sans en-tete)"]
    for k, v in volumes.items():
        C.log(f"volume {k:50s} {v / 1e6:8.2f} Mo  ({100 * v / ref:5.1f} % du .dat)")

    # types relus sans schéma
    def types(df, cols=("ss_quantity", "ss_net_paid", "ss_ticket_number")):
        return {c: df.schema[c].dataType.simpleString() for c in cols}
    relus = {
        "csv (header, sans inferSchema)": types(spark.read.option("header", True).csv(f"{base}/store_sales_csv")),
        "csv (header + inferSchema)": types(spark.read.option("header", True).option("inferSchema", True)
                                            .csv(f"{base}/store_sales_csv")),
        "json": types(spark.read.json(f"{base}/store_sales_json")),
        "parquet": types(spark.read.parquet(f"{base}/store_sales_parquet")),
    }
    for k, v in relus.items():
        C.log(f"types relus {k:32s} {v}")

    # agrégation sur 2 colonnes
    def agg_csv():
        (spark.read.option("header", True).csv(f"{base}/store_sales_csv")
         .groupBy("ss_store_sk").agg(F.sum(F.col("ss_net_paid").cast("decimal(7,2)"))).collect())

    def agg_json():
        spark.read.json(f"{base}/store_sales_json").groupBy("ss_store_sk").agg(F.sum("ss_net_paid")).collect()

    def agg_parquet():
        spark.read.parquet(f"{base}/store_sales_parquet").groupBy("ss_store_sk").agg(F.sum("ss_net_paid")).collect()

    temps = {}
    for nom, fn in [("csv", agg_csv), ("json", agg_json), ("parquet", agg_parquet)]:
        fn()  # préchauffage (JIT, cache)
        temps[nom] = chrono(fn)
        C.log(f"agrégation CA par magasin, {nom:8s} médiane={temps[nom][0]} s  essais={temps[nom][1]}")

    # octets réellement lus par Spark pour le Parquet (lecture de 2 colonnes seulement)
    plan = spark.read.parquet(f"{base}/store_sales_parquet").select("ss_store_sk", "ss_net_paid")._jdf \
        .queryExecution().executedPlan().toString()
    C.log("plan Parquet (extrait) : " + [l for l in plan.splitlines() if "ReadSchema" in l or "FileScan" in l][0][:200])
    print(C.save_json({"volumes_octets": volumes, "types_relus_sans_schema": relus,
                       "agregation_2_colonnes_s": {k: {"mediane": v[0], "essais": v[1]} for k, v in temps.items()},
                       "lignes": ventes.count(), "essais": ESSAIS}, "09_comparaison_formats.json"))
    spark.stop()


if __name__ == "__main__":
    main()
