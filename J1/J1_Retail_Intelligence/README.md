# J1 – Retail Intelligence Platform

TP Jour 1 (UC-01 et UC-02), IPSSI Mastère Data & IA.

## Contenu

| Dossier | Contenu |
|---|---|
| `01_UC01_besoin_exploration/` | Cadrage, questions décisionnelles, dictionnaire KPI (xlsx), inventaire des sources (xlsx), qualification, limites + `preuves/` |
| `02_UC02_architecture/` | Comparaison DW / Lake / Lakehouse, architecture cible, flux, composants, gouvernance, local → Azure + `preuves/` (schémas SVG) |
| `scripts/` | Scripts Python ayant produit l'inventaire, les contrôles et les schémas |

Chaque livrable existe en `.md` (source) et en `.pdf`.

## Reproduire

```bash
python scripts/profile_sources.py <retail_project/retail_project> 01_UC01_besoin_exploration/preuves
python scripts/test_kpi.py <retail_project/retail_project> 01_UC01_besoin_exploration/preuves
python scripts/build_xlsx.py 01_UC01_besoin_exploration
python scripts/gen_schema_uc01.py 01_UC01_besoin_exploration/preuves/schema_fonctionnel_besoins.svg
python scripts/gen_schemas_uc02.py 02_UC02_architecture/preuves
python scripts/build_pdf.py 01_UC01_besoin_exploration 02_UC02_architecture
```

Prérequis : Python 3.11, pandas, openpyxl, markdown, Microsoft Edge (export PDF).

## Usage de l'IA

Exploration et rédaction réalisées avec l'assistance de Claude (Anthropic). Les résultats ont été vérifiés et relus par moi.
