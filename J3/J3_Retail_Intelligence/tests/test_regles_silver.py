"""Test des règles de nettoyage R01 à R05 sur des lignes SYNTHÉTIQUES (UC-06, §8.2).

Pourquoi : sur les vraies données TPCx-BB, aucune ligne ne part en quarantaine. Pour prouver que le mécanisme
fonctionne, on fabrique 8 lignes de store_sales, **inventées pour le test et identifiées comme telles**
(_source_file = 'TEST_SYNTHETIQUE'). Elles ne sont écrites nulle part : ni Bronze, ni Silver, ni HDFS.

Usage : bash scripts/tp3.sh python tests/test_regles_silver.py
"""
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "transformations"))
import common as C  # noqa: E402

spec = importlib.util.spec_from_file_location("silver", os.path.join(HERE, "..", "transformations", "02_silver.py"))
silver = importlib.util.module_from_spec(spec)
spec.loader.exec_module(silver)

COLS = [c for c, _ in C.SOURCES["store_sales"]]
# ligne valide : ext_sales_price = 23.08 × 31 = 715.48 ; net_paid = 715.48 − 0 = 715.48
VALIDE = dict(zip(COLS, ["36890", "71480", "10001", "44404", "493944", "2898", "44093", "10", "294", "0", "31", "18.00",
                         "30.78", "23.08", "238.70", "715.48", "558.00", "954.18", "21.46", "0.00", "715.48", "736.94",
                         "157.48"]))
CAS = [  # (nom du cas, modifications, motif attendu ou None)
    ("ligne valide", {}, None),
    ("marge négative = conservée (R08)", {"ss_net_profit": "-856.98"}, None),
    ("quantité non numérique", {"ss_quantity": "abc"}, "R01_type_invalide:ss_quantity"),
    ("montant non numérique", {"ss_net_paid": "12,50"}, "R01_type_invalide:ss_net_paid"),
    ("ticket absent", {"ss_ticket_number": ""}, "R03_obligatoire_nul:ss_ticket_number"),
    ("quantité nulle", {"ss_quantity": "0", "ss_ext_sales_price": "0.00", "ss_net_paid": "0.00"},
     "R04_quantite_non_positive"),
    ("montant négatif", {"ss_coupon_amt": "-1.00", "ss_net_paid": "716.48"}, "R04_montant_negatif:ss_coupon_amt"),
    ("calcul incohérent", {"ss_ext_sales_price": "999.99"}, "R05_incoherence:ext_sales_price"),
]


def main():
    spark = C.spark_session("TP3-Tests")
    rows = []
    for i, (nom, modif, _) in enumerate(CAS):
        r = {**VALIDE, **modif, "ss_ticket_number": modif.get("ss_ticket_number", str(900000 + i))}
        rows.append([r[c] for c in COLS] + ["TEST_SYNTHETIQUE", "test", nom])
    df = spark.createDataFrame(rows, COLS + ["_source_file", "_lot", "_run_id"])
    valides, quarantaine = silver.separer(silver.typer(df, "store_sales"), silver.regles_ventes())
    obtenus = {r["_run_id"]: list(r["_motifs"]) for r in quarantaine.select("_run_id", "_motifs").collect()}
    gardes = {r["_run_id"] for r in valides.select("_run_id").collect()}
    echecs = 0
    for nom, _, attendu in CAS:
        if attendu is None:
            ok = nom in gardes
            detail = "conservée en Silver"
        else:
            ok = nom in obtenus and attendu in obtenus[nom]
            detail = f"quarantaine {obtenus.get(nom)}"
        echecs += not ok
        print(f"[{'OK' if ok else 'ECHEC':5s}] {nom:34s} attendu={attendu or 'Silver'} -> {detail}")
    print(f"\n{len(CAS) - echecs}/{len(CAS)} cas conformes")
    spark.stop()
    sys.exit(1 if echecs else 0)


if __name__ == "__main__":
    main()
