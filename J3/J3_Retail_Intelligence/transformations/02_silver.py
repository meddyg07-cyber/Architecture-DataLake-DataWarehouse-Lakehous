"""Étape Bronze -> Silver (UC-06) : typage, règles de nettoyage, quarantaine, enrichissement par date.

Chaque règle porte un identifiant (R01…R13) repris dans docs/UC06_regles_nettoyage.md.
Principe : on **n'efface rien en silence**. Une ligne invalide part en quarantaine (zone quality) avec son motif ;
une ligne valide mais surprenante est conservée avec un **indicateur** (_flag_…).

Usage : bash scripts/tp3.sh python transformations/02_silver.py
"""
from pyspark.sql import DataFrame
from pyspark.sql import functions as F

import common as C

PROV = ["_source_file", "_lot", "_run_id"]


def typer(df: DataFrame, table: str):
    """R01 + R02 : trim des textes, texte vide -> null, puis conversion dans le type cible.
    Retourne le DataFrame typé, avec la liste des motifs « type invalide » (valeur présente mais non convertible).
    try_cast et non cast : Spark 4 est en mode ANSI, un cast invalide y lève une erreur qui arrêterait tout le
    traitement (erreur rencontrée, voir le test tests/test_regles_silver.py)."""
    cols, motifs = [], []
    for c, typ in C.SOURCES[table]:
        brut = F.when(F.trim(F.col(c)) == "", None).otherwise(F.trim(F.col(c)))
        cols.append(brut.try_cast(typ).alias(c) if typ != "string" else brut.alias(c))
        if typ != "string":
            motifs.append(F.when(brut.isNotNull() & brut.try_cast(typ).isNull(), F.lit(f"R01_type_invalide:{c}")))
    typed = df.select(*cols, *[F.col(p) for p in PROV],
                      F.array_compact(F.array(*motifs)).alias("_motifs") if motifs
                      else F.array().cast("array<string>").alias("_motifs"))
    return typed


def separer(df: DataFrame, regles: dict):
    """Ajoute les motifs des règles bloquantes, puis sépare valides / quarantaine."""
    extra = [F.when(cond, F.lit(nom)) for nom, cond in regles.items()]
    df = df.withColumn("_motifs", F.array_compact(F.concat(F.col("_motifs"), F.array(*extra))))
    valides = df.filter(F.size("_motifs") == 0).drop("_motifs")
    quarantaine = df.filter(F.size("_motifs") > 0)
    return valides, quarantaine


def regles_ventes() -> dict:
    """Règles bloquantes R03 à R05 sur store_sales (une ligne qui en viole une part en quarantaine)."""
    montants = ["ss_wholesale_cost", "ss_list_price", "ss_sales_price", "ss_ext_discount_amt", "ss_ext_sales_price",
                "ss_ext_wholesale_cost", "ss_ext_list_price", "ss_ext_tax", "ss_coupon_amt", "ss_net_paid",
                "ss_net_paid_inc_tax"]
    obligatoires = ["ss_ticket_number", "ss_item_sk", "ss_sold_date_sk", "ss_store_sk", "ss_quantity", "ss_net_paid"]
    regles = {f"R03_obligatoire_nul:{c}": F.col(c).isNull() for c in obligatoires}
    regles["R04_quantite_non_positive"] = F.col("ss_quantity") <= 0
    regles.update({f"R04_montant_negatif:{c}": F.col(c) < 0 for c in montants})   # ss_net_profit exclu (R08)
    regles["R05_incoherence:ext_sales_price"] = \
        F.abs(F.col("ss_ext_sales_price") - F.col("ss_sales_price") * F.col("ss_quantity")) > 0.01
    regles["R05_incoherence:net_paid"] = \
        F.abs(F.col("ss_net_paid") - (F.col("ss_ext_sales_price") - F.col("ss_coupon_amt"))) > 0.01
    return regles


def ecrire(df: DataFrame, dest: str, partition: str | None = None):
    w = df.write.mode("overwrite")
    if partition:
        w = w.partitionBy(partition)
    w.parquet(dest)


def main():
    spark = C.spark_session("TP3-02-Silver")
    rid = C.run_id()
    bilan = {"run_id": rid, "etape": "silver", "tables": {}}
    bronze = {t: spark.read.parquet(f"{C.BRONZE}/{t}") for t in C.SOURCES}

    # ------------------------------------------------------------ dimensions
    # date_dim : typage seul (R01). La dimension est conservée entière (1900-2100) : on ne filtre pas une dimension.
    dd = typer(bronze["date_dim"], "date_dim")
    dd_ok, dd_q = separer(dd, {"R03_cle_nulle:d_date_sk": F.col("d_date_sk").isNull(),
                               "R03_date_nulle:d_date": F.col("d_date").isNull()})

    # item : R11 catégorie obligatoire (sert d'axe d'analyse) ; marque / description manquantes conservées à null.
    it = typer(bronze["item"], "item")
    it_ok, it_q = separer(it, {"R03_cle_nulle:i_item_sk": F.col("i_item_sk").isNull(),
                               "R11_categorie_nulle": F.col("i_category").isNull()})
    it_ok = it_ok.withColumn("i_version_courante", F.col("i_rec_end_date").isNull())

    # store : R12 date de fermeture. On garde la clé d'origine, on ajoute la date convertie et son statut.
    st = typer(bronze["store"], "store")
    st_ok, st_q = separer(st, {"R03_cle_nulle:s_store_sk": F.col("s_store_sk").isNull()})
    dates = dd_ok.select(F.col("d_date_sk").alias("_k"), F.col("d_date").alias("s_closed_date"))
    st_ok = st_ok.join(dates, st_ok.s_closed_date_sk == dates._k, "left").drop("_k")

    # ------------------------------------------------------------ fait store_sales
    ss = typer(bronze["store_sales"], "store_sales")
    regles = regles_ventes()
    # R06 intégrité référentielle : la ligne doit retrouver son article, sa date et son magasin
    for col, dim, k in [("ss_item_sk", it_ok, "i_item_sk"), ("ss_sold_date_sk", dd_ok, "d_date_sk"),
                        ("ss_store_sk", st_ok, "s_store_sk")]:
        ref = dim.select(F.col(k).alias(f"_ref_{col}")).distinct()
        ss = ss.join(F.broadcast(ref), ss[col] == ref[f"_ref_{col}"], "left")
        regles[f"R06_orphelin:{col}"] = F.col(col).isNotNull() & F.col(f"_ref_{col}").isNull()
    ss_ok, ss_q = separer(ss, regles)
    ss_ok = ss_ok.drop(*[c for c in ss_ok.columns if c.startswith("_ref_")])
    ss_q = ss_q.drop(*[c for c in ss_q.columns if c.startswith("_ref_")])

    # R07 doublons : les doublons EXACTS (toutes colonnes métier égales) sont retirés ; une clé (ticket, article)
    # partagée par des lignes différentes est CONSERVÉE et signalée (ce sont des ventes distinctes).
    metier = [c for c, _ in C.SOURCES["store_sales"]]
    n_avant = ss_ok.count()
    ss_ok = ss_ok.dropDuplicates(metier)
    doublons_exacts = n_avant - ss_ok.count()
    cle = C.KEYS["store_sales"]
    partagees = ss_ok.groupBy(*cle).count().filter("count > 1").select(*cle, F.lit(True).alias("_flag_cle_partagee"))
    ss_ok = ss_ok.join(partagees, cle, "left").fillna(False, ["_flag_cle_partagee"])

    # R08 marge négative conservée (cas métier possible : promotion, déstockage) -> indicateur
    ss_ok = ss_ok.withColumn("_flag_marge_negative", F.col("ss_net_profit") < 0)
    # R09 montants atypiques (Tukey Q3 + 3*IQR sur ss_net_paid) conservés -> indicateur
    q1, q3 = ss_ok.approxQuantile("ss_net_paid", [0.25, 0.75], 0.001)
    seuil = round(q3 + 3 * (q3 - q1), 2)
    ss_ok = ss_ok.withColumn("_flag_montant_atypique", F.col("ss_net_paid") > F.lit(seuil))
    # R10 enrichissement date (jointure vérifiée : 0 orphelin, relation N-1 sur la clé unique d_date_sk)
    cal = dd_ok.select(F.col("d_date_sk").alias("ss_sold_date_sk"), F.col("d_date").alias("sold_date"),
                       F.col("d_year").alias("sold_year"), F.col("d_moy").alias("sold_month"))
    n_avant_jointure = ss_ok.count()
    ss_ok = ss_ok.join(F.broadcast(cal), "ss_sold_date_sk", "left")
    n_apres_jointure = ss_ok.count()
    ss_ok = ss_ok.withColumnRenamed("_run_id", "_run_id_bronze").withColumn("_run_id_silver", F.lit(rid))

    # R12 statut de la date de fermeture, calculé par rapport aux ventes réellement observées par magasin
    periode = ss_ok.groupBy("ss_store_sk").agg(F.min("sold_date").alias("_premiere"), F.max("sold_date").alias("_derniere"))
    st_ok = (st_ok.join(periode, st_ok.s_store_sk == periode.ss_store_sk, "left")
             .withColumn("s_closed_date_statut",
                         F.when(F.col("s_closed_date").isNull(), "absente")
                         .when(F.col("s_closed_date") < F.col("_premiere"), "incoherente_avant_ventes")
                         .when(F.col("s_closed_date") <= F.col("_derniere"), "incoherente_pendant_ventes")
                         .otherwise("non_verifiable_apres_ventes"))
             .withColumn("s_closed_date_fiable", F.lit(False))
             .drop("ss_store_sk", "_premiere", "_derniere"))

    # ------------------------------------------------------------ écritures
    sorties = {
        "store_sales": (ss_ok, ss_q, "sold_year"),
        "item": (it_ok, it_q, None),
        "date_dim": (dd_ok, dd_q, None),
        "store": (st_ok, st_q, None),
    }
    for t, (ok, q, part) in sorties.items():
        if t != "store_sales":
            ok = ok.withColumnRenamed("_run_id", "_run_id_bronze").withColumn("_run_id_silver", F.lit(rid))
        dest = f"{C.SILVER}/{t}"
        ecrire(ok, dest, part)
        n_q = q.count()
        if n_q:
            ecrire(q.withColumn("_motifs", F.concat_ws(";", "_motifs")).withColumn("_run_id_silver", F.lit(rid)),
                   f"{C.QUALITY}/quarantaine/{t}")
        relu = spark.read.parquet(dest)
        n_b, n_s = bronze[t].count(), relu.count()
        motifs = {}
        if n_q:
            motifs = {r["m"]: r["n"] for r in q.select(F.explode("_motifs").alias("m")).groupBy("m")
                      .agg(F.count("*").alias("n")).collect()}
        bilan["tables"][t] = {"silver": dest, "partition": part, "lignes_bronze": n_b, "lignes_silver": n_s,
                              "lignes_quarantaine": n_q, "motifs_quarantaine": motifs,
                              "volume_reconcilie": n_b == n_s + n_q + (doublons_exacts if t == "store_sales" else 0),
                              "octets_silver": C.hdfs_du(spark, dest),
                              "schema": [f"{f.name}:{f.dataType.simpleString()}" for f in relu.schema.fields]}
        C.log(f"{t:12s} bronze={n_b:>9,d} silver={n_s:>9,d} quarantaine={n_q:>6,d} -> {dest}")

    ss_s = spark.read.parquet(f"{C.SILVER}/store_sales")
    flags = ss_s.agg(*[F.sum(F.col(c).cast("int")).alias(c) for c in
                       ["_flag_cle_partagee", "_flag_marge_negative", "_flag_montant_atypique"]]).first().asDict()
    bilan["store_sales_details"] = {"doublons_exacts_retires": doublons_exacts, "seuil_tukey_net_paid": seuil,
                                    "q1": q1, "q3": q3, "lignes_avant_jointure_date": n_avant_jointure,
                                    "lignes_apres_jointure_date": n_apres_jointure, "indicateurs": flags,
                                    "partitions": sorted(r[0] for r in ss_s.select("sold_year").distinct().collect())}
    bilan["store_statut_fermeture"] = {r["s_store_id"]: [str(r["s_closed_date"]), r["s_closed_date_statut"]] for r in
                                       spark.read.parquet(f"{C.SILVER}/store").collect()}
    C.log(f"store_sales : doublons exacts retirés={doublons_exacts}, seuil Tukey={seuil}, indicateurs={flags}")
    C.log(f"jointure date : avant={n_avant_jointure:,d} après={n_apres_jointure:,d}")
    print(C.save_json(bilan, "06_silver_bilan.json"))
    spark.stop()


if __name__ == "__main__":
    main()
