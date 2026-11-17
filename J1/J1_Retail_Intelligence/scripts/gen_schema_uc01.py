"""Genere le schema fonctionnel UC-01 (SVG) : utilisateurs -> questions -> KPI -> domaines/fichiers.

Usage : python gen_schema_uc01.py <fichier_svg>
"""
import sys
from xml.sax.saxutils import escape

W, BW, BH = 1100, 200, 40
COLX = [10, 290, 570, 850]
COLOR = {"user": "#1b3550", "q": "#1d8a8a", "kpi": "#4a5e8c",
         "ok": "#2e7d32", "part": "#c77700", "ko": "#b3261e"}

users = ["Direction generale", "Direction commerciale", "Responsable magasin", "Controleur de gestion",
         "Responsable stocks", "Equipe Data (transverse)"]
themes = ["Evolution de l'activite", "Performance produits", "Performance magasins", "Ventes par canal",
          "Retours produits", "Connaissance client", "Niveaux de stock"]
kpis = ["KPI-01/06 CA, evolution", "KPI-02/03/04 Transac., panier, qte", "KPI-05 Taux de remise",
        "KPI-07 Taux de retour", "CA par profil demographique", "KPI-08 Stock moyen"]
doms = [("Ventes : store_sales, web_sales", "ok"), ("Produits : item, item_marketprices", "ok"),
        ("Magasins : store", "ok"), ("Dates : date_dim, time_dim", "ok"),
        ("Retours : store/web_returns, reason", "ok"),
        ("Demographie : cdemo, hdemo, income", "ok"),
        ("Clients : customer (refresh seul.)", "part"),
        ("Stocks : inventory, warehouse", "ok"),
        ("Stock magasin, CRM complet", "ko")]

U2T = {0: [0, 3], 1: [1, 5], 2: [2, 4], 3: [1, 4], 4: [6]}
T2K = {0: [0], 1: [0, 1, 2], 2: [0, 1], 3: [0, 1], 4: [3], 5: [4], 6: [5]}
K2D = {0: [0, 1, 2, 3], 1: [0, 3], 2: [0, 1], 3: [4, 0], 4: [5, 6, 8], 5: [7, 8]}


def ys(n, top=60, h=620):
    step = h / n
    return [top + step * i + (step - BH) / 2 for i in range(n)]


Y = [ys(len(users)), ys(len(themes)), ys(len(kpis)), ys(len(doms))]
out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} 740" font-family="Segoe UI, Arial" font-size="12">',
       '<defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto">'
       '<path d="M0,0 L10,5 L0,10 z" fill="#8795a1"/></marker></defs>']
for x, t in zip(COLX, ["Utilisateurs metier", "Questions decisionnelles", "Indicateurs (KPI)",
                       "Domaines / fichiers observes"]):
    out.append(f'<text x="{x + BW / 2}" y="30" text-anchor="middle" font-weight="bold" font-size="14" fill="#1b3550">{t}</text>')


def link(c1, i, c2, j, dash=False):
    x1, y1 = COLX[c1] + BW, Y[c1][i] + BH / 2
    x2, y2 = COLX[c2], Y[c2][j] + BH / 2
    mx = (x1 + x2) / 2
    d = ' stroke-dasharray="5,4"' if dash else ""
    out.append(f'<path d="M{x1},{y1} C{mx},{y1} {mx},{y2} {x2 - 2},{y2}" fill="none" stroke="#8795a1" '
               f'stroke-width="1.2"{d} marker-end="url(#a)"/>')


for i, js in U2T.items():
    for j in js:
        link(0, i, 1, j)
for i, js in T2K.items():
    for j in js:
        link(1, i, 2, j)
for i, js in K2D.items():
    for j in js:
        link(2, i, 3, j, dash=doms[j][1] != "ok")


def box(c, i, label, color, dash=False):
    x, y = COLX[c], Y[c][i]
    d = ' stroke-dasharray="6,3"' if dash else ""
    fill = "#ffffff" if c == 3 else color
    tc = color if c == 3 else "#ffffff"
    fs = ' font-size="11"' if c == 3 else ""
    out.append(f'<rect x="{x}" y="{y}" width="{BW}" height="{BH}" rx="6" fill="{fill}" stroke="{color}" '
               f'stroke-width="2"{d}/>')
    out.append(f'<text x="{x + BW / 2}" y="{y + BH / 2 + 4}" text-anchor="middle" fill="{tc}"{fs}>{escape(label)}</text>')


for i, u in enumerate(users):
    box(0, i, u, COLOR["user"])
for i, t in enumerate(themes):
    box(1, i, t, COLOR["q"])
for i, k in enumerate(kpis):
    box(2, i, k, COLOR["kpi"])
for i, (d, s) in enumerate(doms):
    box(3, i, d, COLOR[s], dash=s != "ok")
ly = 710
for k, (lab, col, dash) in enumerate([("Source verifiee (observee, jointures controlees)", COLOR["ok"], False),
                                      ("Source partielle (presente mais incomplete)", COLOR["part"], True),
                                      ("Source souhaitee, absente du kit", COLOR["ko"], True)]):
    x = 20 + k * 360
    d = ' stroke-dasharray="6,3"' if dash else ""
    out.append(f'<rect x="{x}" y="{ly}" width="26" height="14" rx="3" fill="#fff" stroke="{col}" stroke-width="2"{d}/>')
    out.append(f'<text x="{x + 34}" y="{ly + 12}" fill="#1b2733">{lab}</text>')
out.append("</svg>")
open(sys.argv[1], "w", encoding="utf-8").write("\n".join(out))
print("OK", sys.argv[1])
