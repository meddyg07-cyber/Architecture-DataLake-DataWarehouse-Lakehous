"""Étape Silver -> Gold (UC-06) : jeux analytiques répondant aux questions métier du J1.

G1  ventes_mensuelles_categorie   grain (annee, mois, categorie)  -> Q1 évolution du CA, Q3 catégories, Q7 remises
G2  performance_magasin_annuelle  grain (annee, magasin)          -> Q5 comparaison des magasins

Montant de référence (« CA ») : ss_net_paid = prix de vente × quantité − coupons, hors taxes (KPI-01 du J1).
Usage : bash scripts/tp3.sh python transformations/03_gold.py
"""
from pyspark.sql import Window
from pyspark.sql import functions as F

import common as C

DERNIERE_VENTE = "2005-12-13"   # constat de l'exploration : décembre 2005 et l'année 2005 sont incomplets


def main():
    spark = C.spark_session("TP3-03-Gold")
    rid = C.run_id()
    ventes = spark.read.parquet(f"{C.SILVER}/store_sales")
    item = spark.read.parquet(f"{C.SILVER}/item")
    store = spark.read.parquet(f"{C.SILVER}/store")
    bilan = {"run_id": rid, "etape": "gold", "jeux": {}}

    # ------------------------------------------------ jointure ventes -> produit (vérifiée)
    # Relation N-1 : i_item_sk est unique dans item (0 doublon) ; 0 vente orpheline (R06). Jointure gauche pour
    # conserver toutes les ventes : le nombre de lignes doit rester identique.
    prod = item.select(F.col("i_item_sk"), F.col("i_category").alias("categorie"))
    n_avant = ventes.count()
    v = ventes.join(F.broadcast(prod), ventes.ss_item_sk == prod.i_item_sk, "left")
    n_apres = v.count()
    non_rapprochees = v.filter(F.col("i_item_sk").isNull()).count()
    bilan["jointure_ventes_item"] = {"cle": "ss_item_sk = i_item_sk", "relation": "N-1", "type": "left",
                                     "lignes_avant": n_avant, "lignes_apres": n_apres,
                                     "non_rapprochees": non_rapprochees}
    C.log(f"jointure ventes->item : avant={n_avant:,d} après={n_apres:,d} non rapprochées={non_rapprochees}")

    # ------------------------------------------------ G1 ventes mensuelles par catégorie
    g1 = (v.groupBy(F.col("sold_year").alias("annee"), F.col("sold_month").alias("mois"), "categorie")
          .agg(F.sum("ss_net_paid").alias("ca_net_paid"),
               F.sum("ss_ext_list_price").alias("montant_prix_catalogue"),
               F.sum("ss_ext_discount_amt").alias("remise"),
               F.sum("ss_coupon_amt").alias("coupons"),
               F.sum("ss_net_profit").alias("marge_nette"),
               F.sum("ss_quantity").cast("long").alias("quantite"),
               F.count("*").alias("nb_lignes"),
               F.countDistinct("ss_store_sk", "ss_ticket_number").alias("nb_tickets"))
          .withColumn("taux_remise_pct", F.round(100 * F.col("remise") / F.col("montant_prix_catalogue"), 2))
          .withColumn("mois_complet", ~((F.col("annee") == 2005) & (F.col("mois") == 12)))
          .withColumn("_source", F.lit("silver/tpcxbb/store_sales + silver/tpcxbb/item"))
          .withColumn("_run_id_gold", F.lit(rid))
          .orderBy("annee", "mois", "categorie"))
    dest1 = f"{C.GOLD}/ventes_mensuelles_categorie"
    g1.write.mode("overwrite").partitionBy("annee").parquet(dest1)

    # ------------------------------------------------ G2 performance annuelle des magasins
    mag = store.select("s_store_sk", "s_store_id", "s_store_name", "s_city", "s_state")
    base = (ventes.groupBy(F.col("sold_year").alias("annee"), "ss_store_sk")
            .agg(F.sum("ss_net_paid").alias("ca_net_paid"),
                 F.countDistinct("ss_ticket_number").alias("nb_tickets"),
                 F.sum("ss_quantity").cast("long").alias("quantite"),
                 F.count("*").alias("nb_lignes"),
                 F.sum("ss_net_profit").alias("marge_nette")))
    w = Window.partitionBy("annee")
    g2 = (base.join(F.broadcast(mag), base.ss_store_sk == mag.s_store_sk, "left").drop("s_store_sk")
          .withColumn("panier_moyen", F.round(F.col("ca_net_paid") / F.col("nb_tickets"), 2))
          .withColumn("part_ca_annee_pct", F.round(100 * F.col("ca_net_paid") / F.sum("ca_net_paid").over(w), 2))
          .withColumn("ecart_moyenne_pct",
                      F.round(100 * (F.col("ca_net_paid") / F.avg("ca_net_paid").over(w) - 1), 2))
          .withColumn("rang_ca_annee", F.rank().over(w.orderBy(F.desc("ca_net_paid"))))
          .withColumn("annee_complete", F.col("annee") < 2005)
          .withColumn("_source", F.lit("silver/tpcxbb/store_sales + silver/tpcxbb/store"))
          .withColumn("_run_id_gold", F.lit(rid))
          .orderBy("annee", "rang_ca_annee"))
    dest2 = f"{C.GOLD}/performance_magasin_annuelle"
    g2.write.mode("overwrite").parquet(dest2)

    # ------------------------------------------------ relecture et bilan
    for nom, dest, grain in [("ventes_mensuelles_categorie", dest1, ["annee", "mois", "categorie"]),
                             ("performance_magasin_annuelle", dest2, ["annee", "ss_store_sk"])]:
        relu = spark.read.parquet(dest)
        n = relu.count()
        uniques = relu.select(*grain).distinct().count()
        bilan["jeux"][nom] = {"chemin": dest, "grain": grain, "lignes": n, "grain_unique": n == uniques,
                              "ca_total": float(relu.agg(F.sum("ca_net_paid")).first()[0]),
                              "octets": C.hdfs_du(spark, dest),
                              "schema": [f"{f.name}:{f.dataType.simpleString()}" for f in relu.schema.fields]}
        C.log(f"{nom}: {n} lignes, grain unique={n == uniques} -> {dest}")
    bilan["ca_total_silver"] = float(ventes.agg(F.sum("ss_net_paid")).first()[0])

    print("\nG1 – CA annuel par catégorie (M$) :")
    (spark.read.parquet(dest1).groupBy("annee").pivot("categorie").agg(F.round(F.sum("ca_net_paid") / 1e6, 2))
     .orderBy("annee").show(truncate=False))
    print("G2 – classement 2004 (dernière année complète) :")
    (spark.read.parquet(dest2).filter("annee = 2004")
     .select("rang_ca_annee", "s_store_id", "s_store_name", "s_state", "ca_net_paid", "nb_tickets", "panier_moyen",
             "part_ca_annee_pct", "ecart_moyenne_pct").orderBy("rang_ca_annee").show(truncate=False))
    print(C.save_json(bilan, "07_gold_bilan.json"))
    spark.stop()


if __name__ == "__main__":
    main()
