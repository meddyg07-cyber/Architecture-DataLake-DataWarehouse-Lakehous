"""Genere les schemas UC-02 : architecture_cible.svg et schema_flux.svg.

Usage : python gen_schemas_uc02.py <dossier_preuves>
"""
import sys
from pathlib import Path
from xml.sax.saxutils import escape

OUT = Path(sys.argv[1])
HEAD = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" font-family="Segoe UI, Arial" font-size="11">'
        '<defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">'
        '<path d="M0,0 L10,5 L0,10 z" fill="#5a6b7b"/></marker></defs>')


def box(x, y, w, h, title, lines, color, dash=False):
    d = ' stroke-dasharray="6,3"' if dash else ""
    s = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="#fff" stroke="{color}" stroke-width="2"{d}/>',
         f'<rect x="{x}" y="{y}" width="{w}" height="24" rx="8" fill="{color}"/>',
         f'<text x="{x + w / 2}" y="{y + 16}" text-anchor="middle" fill="#fff" font-weight="bold">{escape(title)}</text>']
    for i, l in enumerate(lines):
        s.append(f'<text x="{x + 8}" y="{y + 42 + i * 15}" fill="#1b2733">{escape(l)}</text>')
    return s


def arrow(x1, y1, x2, y2, label=""):
    s = [f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#5a6b7b" stroke-width="2" marker-end="url(#a)"/>']
    if label:
        s.append(f'<text x="{(x1 + x2) / 2}" y="{y1 - 5}" text-anchor="middle" fill="#5a6b7b" font-size="10">{label}</text>')
    return s


# ---------------------------------------------------------------- architecture cible
s = [HEAD.format(w=1180, h=470)]
s += box(10, 40, 165, 120, "Sources TPCx-BB", ["data/ : 22 fichiers .dat", "data_refresh/ : 12 fichiers", "Texte '|' sans en-tete", "968 Mo, batch"], "#1b3550")
s += box(10, 180, 165, 80, "Sources complementaires", ["Aucune a ce jour", "(identifiees a part)"], "#8795a1", dash=True)
s += box(200, 40, 165, 220, "Ingestion", ["Apache NiFi", "- detection des lots", "- controle : nb champs,", "  md5, nb lignes", "- ajout metadonnees", "  (lot, date, source)", "- depot dans HDFS", "Batch (pas de temps reel)"], "#4a5e8c")
s += box(390, 40, 175, 220, "Bronze / Raw", ["HDFS (local) / ADLS Gen2", "Fichiers .dat tels que recus", "Immuables, horodates", "/bronze/tpcxbb/<table>/", "  lot=<lot>/ingest=<date>/", "+ manifeste du lot", "Retention : tout l'historique"], "#8d5524")
s += box(590, 40, 175, 220, "Silver", ["Spark / PySpark", "- schema + types appliques", "- dates sk -> vraies dates", "- data + refresh fusionnes", "- controles qualite", "- rejets -> quarantaine", "Format : Parquet", "partition : annee/mois"], "#6b7b8c")
s += box(790, 40, 185, 220, "Gold", ["Modele en etoile (Parquet)", "Faits : ventes (magasin+web),", "  retours, stock hebdo", "Dimensions : produit,", "  magasin, date, canal,", "  demographie", "Agregats KPI-01 a 08"], "#b8860b")
s += box(1000, 40, 170, 220, "Usages", ["Tableaux de bord KPI", "(direction, magasins,", " controle de gestion)", "Requetes SQL ad hoc", "(Spark SQL)", "Exploration Data", "(Python / notebooks)"], "#2e7d32")
for x1, x2 in ((175, 200), (365, 390), (565, 590), (765, 790), (975, 1000)):
    s += arrow(x1, 150, x2, 150)
s += ['<line x1="175" y1="220" x2="200" y2="220" stroke="#8795a1" stroke-width="2" stroke-dasharray="5,4" marker-end="url(#a)"/>']
s += box(10, 285, 1160, 75, "Gouvernance et supervision (transverse)",
         ["Tracabilite : lot, fichier source, md5 et date d'ingestion conserves jusqu'en Gold    |    Catalogue : dictionnaire des tables et colonnes",
          "Qualite : regles par zone, taux de rejet suivis    |    Acces : Bronze = equipe Data seule ; Gold = metiers en lecture    |    Journaux NiFi / Spark"], "#1d8a8a")
s += box(10, 380, 1160, 75, "Stockage et traitement : statut des composants",
         ["Obligatoire : Linux/Ubuntu, Python, Hadoop/HDFS, NiFi, Spark/PySpark, Parquet (format de reference), ADLS Gen2 (cible cloud, Jour 4)",
          "Facultatif : Delta Lake (ACID en Silver/Gold), HBase (acces cle-valeur)    |    Etudies : Azure Data Factory, Azure Synapse    |    PDGF : selon le kit"], "#5a6b7b")
s.append("</svg>")
(OUT / "architecture_cible.svg").write_text("\n".join(s), encoding="utf-8")

# ---------------------------------------------------------------- flux
rows = [("F1 Ventes", "store_sales, web_sales", "fait_ventes", "CA, transactions, panier"),
        ("F2 Retours", "store_returns, web_returns", "fait_retours", "Taux de retour"),
        ("F3 Stocks", "inventory", "fait_stock", "Stock moyen"),
        ("F4 Referentiels", "item, store, date_dim...", "dimensions", "Axes d'analyse"),
        ("F5 Clients (refresh)", "customer, customer_address", "dim_client (protegee)", "Pseudonymise"),
        ("F6 Navigation / avis", "clickstreams, reviews", "Silver seulement", "Exploration")]
cols = [("Source (.dat)", 170), ("NiFi", 110), ("Bronze HDFS", 110), ("Spark -> Silver", 120), ("Gold", 150), ("Usage", 145)]
s = [HEAD.format(w=1090, h=60 + 52 * len(rows))]
x = 140
xs = []
for name, w in cols:
    xs.append((x, w))
    s.append(f'<text x="{x + w / 2}" y="22" text-anchor="middle" font-weight="bold" fill="#1b3550">{name}</text>')
    x += w + 22
for r, (flux, src, gold, use) in enumerate(rows):
    y = 38 + r * 52
    s.append(f'<text x="8" y="{y + 22}" font-weight="bold" fill="#1b3550">{escape(flux)}</text>')
    vals = [src, "GetFile -> PutHDFS", "brut + manifeste", "typage, controles", gold, use]
    dash = r >= 4
    for k, ((x, w), v) in enumerate(zip(xs, vals)):
        col = "#8795a1" if (dash and k >= 4) else "#4a5e8c"
        d = ' stroke-dasharray="5,3"' if dash and k >= 4 else ""
        s.append(f'<rect x="{x}" y="{y}" width="{w}" height="34" rx="6" fill="#f3f6f8" stroke="{col}"{d}/>')
        s.append(f'<text x="{x + w / 2}" y="{y + 21}" text-anchor="middle" fill="#1b2733" font-size="10">{escape(v)}</text>')
        if k < len(xs) - 1:
            s += arrow(x + w, y + 17, x + w + 22, y + 17)
s.append("</svg>")
(OUT / "schema_flux.svg").write_text("\n".join(s), encoding="utf-8")
print("OK")
