"""Génère azure/architecture/schema_architecture.svg (UC-07, livrable J4-07).

Deux couloirs alignés colonne par colonne : la cible Azure (étudiée, non déployée) et la plateforme locale du parcours B
(réellement déployée et exécutée du J2 au J4). Usage : python azure/architecture/gen_schema_architecture.py
"""
from html import escape
from pathlib import Path

W, H = 1320, 860
COLS = ["Sources", "Ingestion / orchestration", "Stockage Data Lake", "Traitement", "Requêtes / analyse", "Restitution"]
X0, CW, GAP = 30, 190, 28                  # première colonne, largeur, espace
STYLE = {   # statut -> (bordure, fond, pointillés)
    "deploye": ("#2e7d32", "#e8f5e9", ""),
    "etudie": ("#c26a12", "#fff4e6", "7 5"),
    "propose": ("#8a8a8a", "#f4f4f4", "3 4"),
}
out = []


def x(col):
    return X0 + col * (CW + GAP)


def boite(col, y, h, titre, lignes, statut, w=None, xx=None):
    bord, fond, dash = STYLE[statut]
    xx = x(col) if xx is None else xx
    w = CW if w is None else w
    out.append(f'<rect x="{xx}" y="{y}" width="{w}" height="{h}" rx="8" fill="{fond}" stroke="{bord}" '
               f'stroke-width="2" stroke-dasharray="{dash}"/>')
    out.append(f'<text x="{xx + 10}" y="{y + 22}" class="t">{escape(titre)}</text>')
    for i, l in enumerate(lignes):
        out.append(f'<text x="{xx + 10}" y="{y + 42 + i * 17}" class="l">{escape(l)}</text>')


def fleche(x1, y1, x2, y2, statut="deploye"):
    bord, _, dash = STYLE[statut]
    out.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{bord}" stroke-width="2" '
               f'stroke-dasharray="{dash}" marker-end="url(#m_{statut})"/>')


def bandeau(y, texte, couleur):
    out.append(f'<text x="{X0}" y="{y}" class="lane" fill="{couleur}">{escape(texte)}</text>')


# ---------------------------------------------------------------- en-têtes de colonnes
for i, c in enumerate(COLS):
    out.append(f'<text x="{x(i) + CW / 2}" y="62" class="col" text-anchor="middle">{escape(c)}</text>')

# ---------------------------------------------------------------- couloir 1 : cible Azure (étudiée)
bandeau(96, "CIBLE AZURE : étudiée et simulée, AUCUNE ressource créée (parcours B)", "#c26a12")
Y1, H1 = 110, 150
boite(0, Y1, H1, "Sources TPCx-BB", ["lot initial (.dat, sep |)", "lot data_refresh", "Données complémentaires :",
                                      "aucune"], "etudie")
boite(1, Y1, H1, "Azure Data Factory", ["pipeline Copy (dépôt Raw)", "déclencheur planifié", "Managed Identity",
                                         "suivi des exécutions"], "etudie")
boite(2, Y1, H1, "ADLS Gen2 (HNS activé)", ["conteneur retail-intelligence", "raw / bronze / silver / gold",
                                             "quality / documentation", "abfss://…dfs.core.windows.net"], "etudie")
boite(3, Y1, H1, "Synapse Spark pool", ["mêmes scripts PySpark", "chemins hdfs:// → abfss://", "pool à arrêt auto",
                                         "(coût à l'usage)"], "etudie")
boite(4, Y1, H1, "Synapse SQL serverless", ["vues SQL sur le Gold", "OPENROWSET (Parquet)", "facturé au volume lu"],
      "etudie")
boite(5, Y1, H1, "Power BI", ["rapports KPI", "lecture du Gold", "(non installé)"], "etudie")
for i in range(5):
    fleche(x(i) + CW, Y1 + H1 / 2, x(i + 1) - 4, Y1 + H1 / 2, "etudie")
boite(0, 276, 66, "Sécurité Azure (étudiée)", ["Entra ID (groupes) · RBAC (rôles sur le compte) · ACL ADLS (répertoires) · "
                                               "Key Vault (secrets) · budget et alertes de coût"], "etudie",
      w=6 * CW + 5 * GAP, xx=X0)

# ---------------------------------------------------------------- correspondances
for i in range(6):
    out.append(f'<line x1="{x(i) + CW / 2}" y1="350" x2="{x(i) + CW / 2}" y2="392" stroke="#9aa4b2" '
               f'stroke-width="1.5" stroke-dasharray="2 4"/>')
out.append(f'<text x="{x(2) + CW / 2 + 8}" y="376" class="eq">≈ équivalent fonctionnel</text>')

# ---------------------------------------------------------------- couloir 2 : local (déployé)
bandeau(414, "PLATEFORME LOCALE (parcours B) : DÉPLOYÉE ET EXÉCUTÉE, preuves J2 à J4", "#2e7d32")
Y2, H2 = 428, 150
boite(0, Y2, H2, "Sources TPCx-BB", ["fichiers .dat locaux", "lot initial traité", "data_refresh : non intégré",
                                      "aucune donnée ajoutée"], "deploye")
boite(1, Y2, H2, "Apache NiFi 2.12 (J2)", ["GetFile → PutHDFS", "provenance, erreurs", "+ scripts run_all.sh",
                                            "(enchaînement J3-J4)"], "deploye")
boite(2, Y2, H2, "HDFS 3.5 (J2)", ["/retail-lake : raw (555),", "bronze, silver, gold,", "quality, logs",
                                    "+ démo ACL (J4)"], "deploye")
boite(3, Y2, H2, "PySpark 4.3 local[*] (J3)", ["Bronze → Silver → Gold", "règles R01-R13", "31 contrôles qualité",
                                                "Parquet snappy"], "deploye")
boite(4, Y2, H2, "Spark SQL / DataFrame", ["KPI (kpi_retail.py)", "statistiques, analyses", "notebook UC-08 (J4)"],
      "deploye")
boite(5, Y2, H2, "Jupyter + Matplotlib", ["4 visualisations PNG", "exports CSV", "notebook exécuté (J4)"], "deploye")
for i in range(5):
    fleche(x(i) + CW, Y2 + H2 / 2, x(i + 1) - 4, Y2 + H2 / 2, "deploye")
boite(0, 594, 66, "Sécurité locale (démontrée au J4)", ["permissions POSIX + ACL HDFS par zone (13 tests sur 13) · "
                                                        "identifiants NiFi hors Git · limite : authentification "
                                                        "« simple », sans Kerberos"], "deploye",
      w=6 * CW + 5 * GAP, xx=X0)

# ---------------------------------------------------------------- briques open source proposées (non installées)
bandeau(694, "BRIQUES OPEN SOURCE PROPOSÉES : étudiées, non installées (le socle obligatoire ne les exige pas)", "#6b6b6b")
boite(1, 708, 58, "Apache Airflow", ["orchestration planifiée"], "propose")
boite(2, 708, 58, "MinIO (API S3)", ["stockage objet local"], "propose")
boite(3, 708, 58, "Apache Iceberg", ["format de table ACID"], "propose")
boite(4, 708, 58, "Trino + catalogue", ["SQL distribué, Nessie / HMS"], "propose")
boite(5, 708, 58, "Apache Superset", ["tableaux de bord SQL"], "propose")

# ---------------------------------------------------------------- légende
ly = 800
for i, (st, lib) in enumerate([("deploye", "Déployé et exécuté (captures, journaux)"),
                               ("etudie", "Étudié / simulé : aucune ressource Azure créée"),
                               ("propose", "Proposé : composant open source non installé")]):
    bord, fond, dash = STYLE[st]
    lx = X0 + i * 420
    out.append(f'<rect x="{lx}" y="{ly}" width="34" height="18" rx="4" fill="{fond}" stroke="{bord}" stroke-width="2" '
               f'stroke-dasharray="{dash}"/>')
    out.append(f'<text x="{lx + 44}" y="{ly + 14}" class="l">{escape(lib)}</text>')
out.append(f'<text x="{X0}" y="{ly + 44}" class="src">Retail Intelligence Platform · TP J4 · UC-07 · 19/11/2026 · '
           f'Données TPCx-BB synthétiques. Usages analytiques : KPI et analyses UC-08 sur le Gold.</text>')

defs = "".join(
    f'<marker id="m_{k}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">'
    f'<path d="M0,0 L10,5 L0,10 z" fill="{v[0]}"/></marker>' for k, v in STYLE.items())
svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="Segoe UI, Arial, sans-serif">
<defs>{defs}</defs>
<style>
.t {{ font-size: 14px; font-weight: 700; fill: #1f2937; }}
.l {{ font-size: 12.5px; fill: #374151; }}
.col {{ font-size: 14px; font-weight: 700; fill: #111827; }}
.lane {{ font-size: 13px; font-weight: 700; letter-spacing: .3px; }}
.eq {{ font-size: 12px; fill: #6b7280; font-style: italic; }}
.src {{ font-size: 11.5px; fill: #6b7280; }}
</style>
<rect width="{W}" height="{H}" fill="#ffffff"/>
<text x="{X0}" y="32" font-size="19" font-weight="700" fill="#111827">Architecture Retail Intelligence : cible Azure et équivalent local / open source</text>
{chr(10).join(out)}
</svg>"""
dest = Path(__file__).with_name("schema_architecture.svg")
dest.write_text(svg, encoding="utf-8")
print("écrit :", dest)
