"""Test de l'environnement (TP J3, §1.4.1 et étape 1) : session Spark locale, lecture HDFS, écriture de test.

Usage (Ubuntu, venv activé) : python scripts/test_spark.py
"""
import platform
import sys

from pyspark.sql import SparkSession

HDFS = "hdfs://localhost:9000"

spark = (
    SparkSession.builder
    .appName("Test-Retail-Intelligence")
    .master("local[*]")
    .config("spark.ui.showConsoleProgress", "false")
    .getOrCreate()
)
spark.sparkContext.setLogLevel("ERROR")

print("Python        :", sys.version.split()[0], platform.platform())
print("Version Spark :", spark.version)
print("Master        :", spark.sparkContext.master, "| cœurs :", spark.sparkContext.defaultParallelism)
print("Java          :", spark.sparkContext._jvm.System.getProperty("java.version"))

# 1. Petit jeu de test du sujet
df = spark.createDataFrame([("Magasin A", 1200.0), ("Magasin B", 850.0), ("Magasin C", 1600.0)],
                           ["magasin", "chiffre_affaires"])
df.show()

# 2. Lecture d'un fichier réel dans HDFS (zone Raw, déposé au J2)
store = spark.read.option("header", False).option("sep", "|").option("inferSchema", True) \
    .csv(f"{HDFS}/retail-lake/raw/tpcxbb/initial/store/store.dat")
store.printSchema()
print("store.dat : lignes =", store.count(), "| colonnes =", len(store.columns))

# 3. Écriture de test dans un répertoire autorisé (jamais dans Raw), puis relecture
sortie = f"{HDFS}/retail-lake/logs/tp3_test_spark"
df.write.mode("overwrite").parquet(sortie)
print("Relecture du test Parquet :", spark.read.parquet(sortie).count(), "lignes ->", sortie)

spark.stop()
