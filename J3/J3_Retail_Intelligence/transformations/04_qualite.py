"""Étape 9 – Contrôles qualité sur Silver et Gold (UC-06).

Chaque contrôle produit : dimension, jeu, règle, résultat mesuré, statut.
  OK      la règle est respectée
  ALERTE  anomalie connue, documentée, conservée (n'empêche pas l'usage, limite l'interprétation)
  ECHEC   règle bloquante non respectée -> le jeu ne doit pas être publié
Le rapport est écrit dans preuves/ (CSV + JSON) et ajouté (mode append, historique) dans /retail-lake/quality.

Usage : bash scripts/tp3.sh python transformations/04_qualite.py
"""
import csv
import os

from pyspark.sql import functions as F

import common as C

TYPES_ATTENDUS = {c: t for c, t in C.SOURCES["store_sales"]}


def main():
    spark = C.spark_session("TP3-04-Qualite")
    rid = C.run_id()
    R = []

    def ctrl(dimension, jeu, regle, resultat, statut):
        R.append({"run_id": rid, "dimension": dimension, "jeu": jeu, "regle": regle,
                  "resultat": str(resultat), "statut": statut})
        C.log(f"[{statut:6s}] {dimension:12s} {jeu:30s} {regle} -> {resultat}")

    ss = spark.read.parquet(f"{C.SILVER}/store_sales").cache()
    it = spark.read.parquet(f"{C.SILVER}/item")
    st = spark.read.parquet(f"{C.SILVER}/store")
    dd = spark.read.parquet(f"{C.SILVER}/date_dim")
    g1 = spark.read.parquet(f"{C.GOLD}/ventes_mensuelles_categorie")
    g2 = spark.read.parquet(f"{C.GOLD}/performance_magasin_annuelle")
    n = ss.count()

    # ---------------- volumes : Raw = Bronze = Silver + quarantaine
    for t in C.SOURCES:
        n_raw = C.read_raw(spark, t).count()
        n_br = spark.read.parquet(f"{C.BRONZE}/{t}").count()
        n_si = spark.read.parquet(f"{C.SILVER}/{t}").count()
        try:
            n_q = spark.read.parquet(f"{C.QUALITY}/quarantaine/{t}").count()
        except Exception:   # pas de quarantaine écrite = 0 ligne rejetée
            n_q = 0
        ok = n_raw == n_br == n_si + n_q
        ctrl("Volume", f"silver/{t}", "raw = bronze = silver + quarantaine",
             f"{n_raw} = {n_br} = {n_si} + {n_q}", "OK" if ok else "ECHEC")

    # ---------------- validité des types (schéma Silver = types cibles)
    reel = {f.name: f.dataType.simpleString() for f in ss.schema.fields}
    ecarts = [c for c, t in TYPES_ATTENDUS.items() if reel.get(c) != t]
    ctrl("Validite", "silver/store_sales", "23 colonnes au type cible (int, bigint, decimal(7,2))",
         "conformes" if not ecarts else f"écarts : {ecarts}", "OK" if not ecarts else "ECHEC")

    # ---------------- complétude
    oblig = ["ss_ticket_number", "ss_item_sk", "ss_sold_date_sk", "ss_store_sk", "ss_quantity", "ss_net_paid", "sold_date"]
    nuls = ss.agg(*[F.sum(F.col(c).isNull().cast("int")).alias(c) for c in oblig]).first().asDict()
    ctrl("Completude", "silver/store_sales", "champs obligatoires non nuls", nuls,
         "OK" if not any(nuls.values()) else "ECHEC")
    opt = ss.agg(*[F.round(100 * F.avg(F.col(c).isNull().cast("int")), 3).alias(c)
                   for c in ["ss_cdemo_sk", "ss_hdemo_sk", "ss_addr_sk", "ss_promo_sk"]]).first().asDict()
    ctrl("Completude", "silver/store_sales", "clés facultatives : % de nuls (< 1 % toléré)", opt,
         "OK" if max(opt.values()) < 1 else "ALERTE")
    n_cat = it.filter("i_category IS NULL").count()
    ctrl("Completude", "silver/item", "catégorie renseignée", f"{n_cat} nulle(s)", "OK" if n_cat == 0 else "ECHEC")
    marq = it.filter("i_brand IS NULL").count()
    ctrl("Completude", "silver/item", "marque renseignée (non utilisée en Gold)", f"{marq} nulle(s) sur {it.count()}",
         "OK" if marq == 0 else "ALERTE")

    # ---------------- unicité / clés candidates
    for jeu, df, cle in [("silver/item", it, ["i_item_sk"]), ("silver/store", st, ["s_store_sk"]),
                         ("silver/date_dim", dd, ["d_date_sk"]), ("silver/date_dim", dd, ["d_date"])]:
        d = df.count() - df.select(*cle).distinct().count()
        ctrl("Unicite", jeu, f"clé {cle} unique", f"{d} doublon(s)", "OK" if d == 0 else "ECHEC")
    exacts = n - ss.select(*TYPES_ATTENDUS).distinct().count()
    ctrl("Unicite", "silver/store_sales", "aucun doublon exact (23 colonnes)", f"{exacts}", "OK" if exacts == 0 else "ECHEC")
    surplus = n - ss.select("ss_ticket_number", "ss_item_sk").distinct().count()
    marquees = ss.filter("_flag_cle_partagee").count()
    ctrl("Unicite", "silver/store_sales", "clé candidate (ticket, article)",
         f"non unique : {surplus} ligne(s) en surplus, {marquees} lignes signalées (_flag_cle_partagee), conservées",
         "ALERTE")

    # ---------------- cohérence des valeurs
    coh = ss.agg(
        F.sum((F.col("ss_quantity") <= 0).cast("int")).alias("quantite<=0"),
        F.sum((F.col("ss_net_paid") < 0).cast("int")).alias("net_paid<0"),
        F.sum((F.abs(F.col("ss_ext_sales_price") - F.col("ss_sales_price") * F.col("ss_quantity")) > 0.01)
              .cast("int")).alias("ext_sales!=prix*qte"),
        F.sum((F.abs(F.col("ss_net_paid") - F.col("ss_ext_sales_price") + F.col("ss_coupon_amt")) > 0.01)
              .cast("int")).alias("net_paid!=ext-coupon"),
        F.sum((F.col("sold_year") != F.year("sold_date")).cast("int")).alias("annee!=date"),
    ).first().asDict()
    ctrl("Coherence", "silver/store_sales", "quantités > 0, montants >= 0, calculs cohérents", coh,
         "OK" if not any(coh.values()) else "ECHEC")
    neg = ss.filter("_flag_marge_negative").count()
    ctrl("Coherence", "silver/store_sales", "marge nette négative (conservée, signalée)",
         f"{neg} lignes ({100 * neg / n:.1f} %)", "ALERTE")
    atyp = ss.filter("_flag_montant_atypique").count()
    ctrl("Coherence", "silver/store_sales", "montants atypiques Tukey (conservés, signalés)",
         f"{atyp} lignes ({100 * atyp / n:.2f} %)", "ALERTE")
    zero = ss.filter("ss_net_paid = 0").count()
    ctrl("Coherence", "silver/store_sales", "ventes à 0 (remise totale ?)", f"{zero} lignes", "OK" if zero == 0 else "ALERTE")
    fiables = st.filter("s_closed_date_fiable").count()
    statuts = {r[0]: r[1] for r in st.groupBy("s_closed_date_statut").count().collect()}
    ctrl("Coherence", "silver/store", "date de fermeture exploitable", f"{fiables}/12 fiable(s) ; {statuts}", "ALERTE")

    # ---------------- intégrité référentielle
    for col, dim, k, jeu in [("ss_item_sk", it, "i_item_sk", "item"), ("ss_store_sk", st, "s_store_sk", "store"),
                             ("ss_sold_date_sk", dd, "d_date_sk", "date_dim")]:
        o = ss.join(dim.select(F.col(k).alias(col)), col, "left_anti").count()
        ctrl("Integrite", "silver/store_sales", f"{col} -> {jeu}.{k}", f"{o} orphelin(s)", "OK" if o == 0 else "ECHEC")

    # ---------------- fraîcheur / période
    pmin, pmax = ss.agg(F.min("sold_date"), F.max("sold_date")).first()
    ctrl("Fraicheur", "silver/store_sales", "période couverte", f"{pmin} -> {pmax} (2005 incomplète)", "ALERTE")
    par_an = {r[0]: r[1] for r in ss.groupBy("sold_year").count().collect()}
    moy = sum(v for a, v in par_an.items() if a < 2005) / 4
    ecart = {a: round(100 * (v / moy - 1), 1) for a, v in sorted(par_an.items())}
    ctrl("Volume", "silver/store_sales", "lignes par année : écart à la moyenne 2001-2004 (%)", ecart,
         "OK" if all(abs(e) < 10 for e in ecart.values()) else "ALERTE")

    # ---------------- Gold : grain et réconciliation
    for jeu, df, grain in [("gold/ventes_mensuelles_categorie", g1, ["annee", "mois", "categorie"]),
                           ("gold/performance_magasin_annuelle", g2, ["annee", "ss_store_sk"])]:
        d = df.count() - df.select(*grain).distinct().count()
        ctrl("Unicite", jeu, f"grain {grain} unique", f"{d} doublon(s), {df.count()} lignes", "OK" if d == 0 else "ECHEC")
    ca_s = ss.agg(F.sum("ss_net_paid")).first()[0]
    ca_1 = g1.agg(F.sum("ca_net_paid")).first()[0]
    ca_2 = g2.agg(F.sum("ca_net_paid")).first()[0]
    ctrl("Coherence", "gold (2 jeux)", "réconciliation : somme CA Gold = somme CA Silver",
         f"silver={ca_s} | G1={ca_1} | G2={ca_2}", "OK" if ca_s == ca_1 == ca_2 else "ECHEC")
    q_s = ss.agg(F.sum("ss_quantity")).first()[0]
    q_1 = g1.agg(F.sum("quantite")).first()[0]
    ctrl("Coherence", "gold/ventes_mensuelles_categorie", "réconciliation des quantités", f"silver={q_s} | G1={q_1}",
         "OK" if q_s == q_1 else "ECHEC")
    p = g2.groupBy("annee").agg(F.round(F.sum("part_ca_annee_pct"), 1).alias("s")).filter("abs(s - 100) > 0.1").count()
    ctrl("Coherence", "gold/performance_magasin_annuelle", "parts de CA = 100 % par année", f"{p} année(s) en écart",
         "OK" if p == 0 else "ECHEC")
    nb_mag = g2.groupBy("annee").count().filter("count != 12").count()
    ctrl("Completude", "gold/performance_magasin_annuelle", "12 magasins présents chaque année",
         f"{nb_mag} année(s) incomplète(s)", "OK" if nb_mag == 0 else "ALERTE")

    # ---------------- écritures
    bilan = {s: sum(1 for r in R if r["statut"] == s) for s in ("OK", "ALERTE", "ECHEC")}
    C.log(f"BILAN : {bilan}")
    os.makedirs(C.PREUVES, exist_ok=True)
    with open(os.path.join(C.PREUVES, "08_rapport_qualite.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(R[0]), delimiter=";")
        w.writeheader()
        w.writerows(R)
    C.save_json({"run_id": rid, "bilan": bilan, "controles": R}, "08_rapport_qualite.json")
    spark.createDataFrame(R).withColumn("_controle_at", F.current_timestamp()).coalesce(1) \
        .write.mode("append").parquet(f"{C.QUALITY}/rapport_controles")      # historique des exécutions
    spark.stop()
    if bilan["ECHEC"]:
        raise SystemExit(f"{bilan['ECHEC']} contrôle(s) en ECHEC")


if __name__ == "__main__":
    main()
