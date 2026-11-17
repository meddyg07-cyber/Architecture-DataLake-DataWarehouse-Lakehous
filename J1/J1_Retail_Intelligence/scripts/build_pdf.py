"""Convertit les livrables Markdown (*.md) d'un dossier en PDF via Edge headless.

Usage : python build_pdf.py <dossier> [<dossier> ...]
Chaque X.md produit X.pdf a cote (le HTML intermediaire est supprime).
"""
import subprocess
import sys
from pathlib import Path

import markdown

EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
CSS = """
@page { size: A4; margin: 16mm 14mm; }
body { font-family: 'Segoe UI', Arial, sans-serif; font-size: 10pt; color: #1b2733; line-height: 1.45; }
h1 { color: #1b3550; border-bottom: 3px solid #1d8a8a; padding-bottom: 4px; font-size: 19pt; }
h2 { color: #1b3550; margin-top: 20px; font-size: 14pt; border-bottom: 1px solid #c9d3dc; }
h3 { color: #1d8a8a; font-size: 11.5pt; margin-top: 14px; }
table { border-collapse: collapse; width: 100%; margin: 8px 0 12px; font-size: 8.6pt; page-break-inside: auto; }
tr { page-break-inside: avoid; }
th { background: #1b3550; color: #fff; text-align: left; padding: 4px 5px; }
td { border: 1px solid #c9d3dc; padding: 3px 5px; vertical-align: top; }
tr:nth-child(even) td { background: #f3f6f8; }
code { background: #eef2f5; padding: 0 3px; border-radius: 3px; font-size: 8.8pt; }
pre { background: #f3f6f8; border: 1px solid #c9d3dc; padding: 8px; font-size: 8pt; white-space: pre-wrap; }
blockquote { border-left: 4px solid #b85c00; background: #fff6e8; margin: 8px 0; padding: 6px 10px; }
.meta { color: #5a6b7b; font-size: 9pt; }
svg { max-width: 100%; }
"""


def build(md_path: Path):
    body = markdown.markdown(md_path.read_text(encoding="utf-8"),
                             extensions=["tables", "fenced_code", "sane_lists", "attr_list", "md_in_html"])
    html = md_path.with_suffix(".html")
    html.write_text(f"<!doctype html><html lang='fr'><head><meta charset='utf-8'><title>{md_path.stem}</title>"
                    f"<style>{CSS}</style></head><body>{body}</body></html>", encoding="utf-8")
    pdf = md_path.with_suffix(".pdf").resolve()
    subprocess.run([EDGE, "--headless", "--disable-gpu", "--no-pdf-header-footer", "--no-first-run",
                    f"--user-data-dir={Path(__file__).parent / '.edge_profile'}",
                    f"--print-to-pdf={pdf}", html.resolve().as_uri()], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120)
    if not pdf.exists():
        raise SystemExit(f"ECHEC : {pdf} non cree")
    html.unlink()
    print(f"OK {pdf}")


for d in sys.argv[1:]:
    for md in sorted(Path(d).glob("*.md")):
        build(md)
