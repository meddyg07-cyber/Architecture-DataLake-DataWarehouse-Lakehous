"""Étape Raw -> Bronze (UC-06).

Bronze = copie fidèle de la source, au format Parquet : noms de colonnes officiels, valeurs **en texte, non
modifiées**, plus 5 colonnes de provenance (_source_file, _source_table, _lot, _run_id, _ingested_at).
La zone Raw (.dat déposés au J2) n'est jamais modifiée : elle est en lecture seule.

Usage : bash scripts/tp3.sh python transformations/01_bronze.py
"""
import common as C


def main():
    spark = C.spark_session("TP3-01-Bronze")
    rid = C.run_id()
    bilan = {"run_id": rid, "etape": "bronze", "tables": {}}
    for table in C.SOURCES:
        src = C.read_raw(spark, table)
        n_raw = src.count()
        df = C.add_provenance(src, table, rid)
        dest = f"{C.BRONZE}/{table}"
        df.write.mode("overwrite").parquet(dest)          # répertoire dédié au TP : overwrite autorisé
        relu = spark.read.parquet(dest)
        n_bronze = relu.count()
        ok = n_raw == n_bronze
        bilan["tables"][table] = {"raw": C.raw_path(table), "bronze": dest, "lignes_raw": n_raw,
                                  "lignes_bronze": n_bronze, "volume_conserve": ok,
                                  "octets_raw": C.hdfs_du(spark, C.raw_path(table)),
                                  "octets_bronze": C.hdfs_du(spark, dest)}
        C.log(f"{table:12s} raw={n_raw:>9,d} bronze={n_bronze:>9,d} {'OK' if ok else 'ECART'} -> {dest}")
    print(C.save_json(bilan, "05_bronze_bilan.json"))
    spark.stop()


if __name__ == "__main__":
    main()
