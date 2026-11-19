"""Paramètres et fonctions communes du TP J3 (UC-06).

Tout ce qui dépend de l'environnement est ici : chemins HDFS, sources retenues, schémas, session Spark.
Les scripts 01 à 04 et le notebook d'exploration importent ce module.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import sys

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import StringType, StructField, StructType

# ---------------------------------------------------------------- chemins
HDFS = os.environ.get("TP3_HDFS", "hdfs://localhost:9000")
LAKE = f"{HDFS}/retail-lake"
RAW = f"{LAKE}/raw/tpcxbb/initial"          # déposé au J2, en lecture seule (chmod 555)
BRONZE = f"{LAKE}/bronze/tpcxbb"
SILVER = f"{LAKE}/silver/tpcxbb"
GOLD = f"{LAKE}/gold/retail"
QUALITY = f"{LAKE}/quality/tpcxbb"         # quarantaine + rapport de contrôles
LOGS = f"{LAKE}/logs/tp3"

LOT = "initial"                             # lot TPCx-BB traité (data/) ; data_refresh hors périmètre
PREUVES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "preuves")

# ---------------------------------------------------------------- sources retenues
# Noms de colonnes : schéma public TPC-DS / TPCx-BB (les .dat n'ont pas d'en-tête), déjà validés au J1
# en comparant le nombre de champs. Types cibles décidés à l'étape 4 (règles de nettoyage).
SOURCES: dict[str, list[tuple[str, str]]] = {
    "store_sales": [
        ("ss_sold_date_sk", "int"), ("ss_sold_time_sk", "int"), ("ss_item_sk", "int"),
        ("ss_customer_sk", "int"), ("ss_cdemo_sk", "int"), ("ss_hdemo_sk", "int"), ("ss_addr_sk", "int"),
        ("ss_store_sk", "int"), ("ss_promo_sk", "int"), ("ss_ticket_number", "bigint"),
        ("ss_quantity", "int"), ("ss_wholesale_cost", "decimal(7,2)"), ("ss_list_price", "decimal(7,2)"),
        ("ss_sales_price", "decimal(7,2)"), ("ss_ext_discount_amt", "decimal(7,2)"),
        ("ss_ext_sales_price", "decimal(7,2)"), ("ss_ext_wholesale_cost", "decimal(7,2)"),
        ("ss_ext_list_price", "decimal(7,2)"), ("ss_ext_tax", "decimal(7,2)"), ("ss_coupon_amt", "decimal(7,2)"),
        ("ss_net_paid", "decimal(7,2)"), ("ss_net_paid_inc_tax", "decimal(7,2)"), ("ss_net_profit", "decimal(7,2)"),
    ],
    "item": [
        ("i_item_sk", "int"), ("i_item_id", "string"), ("i_rec_start_date", "date"), ("i_rec_end_date", "date"),
        ("i_item_desc", "string"), ("i_current_price", "decimal(7,2)"), ("i_wholesale_cost", "decimal(7,2)"),
        ("i_brand_id", "int"), ("i_brand", "string"), ("i_class_id", "int"), ("i_class", "string"),
        ("i_category_id", "int"), ("i_category", "string"), ("i_manufact_id", "int"), ("i_manufact", "string"),
        ("i_size", "string"), ("i_formulation", "string"), ("i_color", "string"), ("i_units", "string"),
        ("i_container", "string"), ("i_manager_id", "int"), ("i_product_name", "string"),
    ],
    "date_dim": [
        ("d_date_sk", "int"), ("d_date_id", "string"), ("d_date", "date"), ("d_month_seq", "int"),
        ("d_week_seq", "int"), ("d_quarter_seq", "int"), ("d_year", "int"), ("d_dow", "int"), ("d_moy", "int"),
        ("d_dom", "int"), ("d_qoy", "int"), ("d_fy_year", "int"), ("d_fy_quarter_seq", "int"),
        ("d_fy_week_seq", "int"), ("d_day_name", "string"), ("d_quarter_name", "string"), ("d_holiday", "string"),
        ("d_weekend", "string"), ("d_following_holiday", "string"), ("d_first_dom", "int"), ("d_last_dom", "int"),
        ("d_same_day_ly", "int"), ("d_same_day_lq", "int"), ("d_current_day", "string"),
        ("d_current_week", "string"), ("d_current_month", "string"), ("d_current_quarter", "string"),
        ("d_current_year", "string"),
    ],
    "store": [
        ("s_store_sk", "int"), ("s_store_id", "string"), ("s_rec_start_date", "date"), ("s_rec_end_date", "date"),
        ("s_closed_date_sk", "int"), ("s_store_name", "string"), ("s_number_employees", "int"),
        ("s_floor_space", "int"), ("s_hours", "string"), ("s_manager", "string"), ("s_market_id", "int"),
        ("s_geography_class", "string"), ("s_market_desc", "string"), ("s_market_manager", "string"),
        ("s_division_id", "int"), ("s_division_name", "string"), ("s_company_id", "int"),
        ("s_company_name", "string"), ("s_street_number", "string"), ("s_street_name", "string"),
        ("s_street_type", "string"), ("s_suite_number", "string"), ("s_city", "string"), ("s_county", "string"),
        ("s_state", "string"), ("s_zip", "string"), ("s_country", "string"), ("s_gmt_offset", "decimal(5,2)"),
        ("s_tax_precentage", "decimal(5,2)"),
    ],
}

# clé candidate (grain) de chaque source
KEYS = {
    "store_sales": ["ss_ticket_number", "ss_item_sk"],
    "item": ["i_item_sk"],
    "date_dim": ["d_date_sk"],
    "store": ["s_store_sk"],
}


def raw_path(table: str) -> str:
    return f"{RAW}/{table}/{table}.dat"


def string_schema(table: str) -> StructType:
    """Schéma de lecture Bronze : noms officiels, tout en texte (aucune conversion silencieuse)."""
    return StructType([StructField(c, StringType(), True) for c, _ in SOURCES[table]])


# ---------------------------------------------------------------- session
def spark_session(app: str) -> SparkSession:
    spark = (
        SparkSession.builder
        .appName(app)
        .master(os.environ.get("TP3_MASTER", "local[*]"))
        .config("spark.sql.session.timeZone", "Europe/Paris")
        .config("spark.sql.shuffle.partitions", "12")
        .config("spark.ui.showConsoleProgress", "false")
        .config("spark.sql.parquet.compression.codec", "snappy")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("ERROR")
    return spark


def read_raw(spark: SparkSession, table: str) -> DataFrame:
    """Lit un .dat de la zone Raw : séparateur |, sans en-tête, colonnes nommées, tout en texte."""
    return (
        spark.read
        .option("header", False)
        .option("sep", "|")
        .option("encoding", "UTF-8")
        .option("mode", "PERMISSIVE")
        .schema(string_schema(table))
        .csv(raw_path(table))
    )


# ---------------------------------------------------------------- traçabilité
def run_id() -> str:
    return dt.datetime.now().strftime("%Y%m%d_%H%M%S")


def add_provenance(df: DataFrame, table: str, rid: str) -> DataFrame:
    return (
        df.withColumn("_source_file", F.input_file_name())
        .withColumn("_source_table", F.lit(table))
        .withColumn("_lot", F.lit(LOT))
        .withColumn("_run_id", F.lit(rid))
        .withColumn("_ingested_at", F.current_timestamp())
    )


def log(msg: str) -> None:
    print(f"[{dt.datetime.now():%H:%M:%S}] {msg}", flush=True)


def save_json(obj, name: str) -> str:
    os.makedirs(PREUVES, exist_ok=True)
    path = os.path.join(PREUVES, name)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=2, default=str)
    return path


def hdfs_du(spark: SparkSession, path: str) -> int:
    """Taille en octets d'un chemin HDFS (via l'API Hadoop de la JVM Spark)."""
    jvm = spark.sparkContext._jvm
    conf = spark.sparkContext._jsc.hadoopConfiguration()
    p = jvm.org.apache.hadoop.fs.Path(path)
    fs = p.getFileSystem(conf)
    return int(fs.getContentSummary(p).getLength())


if __name__ == "__main__":
    print("Module de configuration ; voir README.md.", file=sys.stderr)
