#!/usr/bin/env python3
"""Render bom/meshthingy-bom.csv as a print-ready A4 PDF.

    pip install weasyprint
    python bom/render_bom_pdf.py            # -> bom/meshthingy-bom.pdf
"""
import csv
import datetime
import html
import re
import subprocess
import sys
from pathlib import Path

from weasyprint import HTML

HERE = Path(__file__).resolve().parent
SRC = HERE / "meshthingy-bom.csv"
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "meshthingy-bom.pdf"

# Rows still needing a decision before parts are ordered.
OPEN_ITEM = re.compile(r"TODO|TBD|\?|verify|Choose", re.IGNORECASE)


def git_rev():
    try:
        return subprocess.check_output(
            ["git", "describe", "--always", "--dirty"], cwd=HERE, text=True
        ).strip()
    except Exception:
        return "unknown"


def esc(s):
    return html.escape(s or "")


def refs(s):
    # Let long reference lists wrap after each comma.
    return esc(s).replace(",", ",<wbr>")


def row_html(r):
    is_open = bool(OPEN_ITEM.search(r["MPN"] + " " + r["Notes"]))
    mfr = esc(r["Manufacturer"])
    mpn = esc(r["MPN"])
    part = f'<div class="mpn">{mpn}</div><div class="mfr">{mfr}</div>' if mpn else '<span class="any">generic</span>'
    return f"""
    <tr class="{'open' if is_open else ''}">
      <td class="chk"><span class="box"></span></td>
      <td class="num">{esc(r['Item'])}</td>
      <td class="qty">{esc(r['Qty'])}</td>
      <td class="ref">{refs(r['Reference'])}</td>
      <td class="val">{esc(r['Value'])}</td>
      <td class="desc">{esc(r['Description'])}</td>
      <td class="part">{part}</td>
      <td class="fp">{esc(r['Footprint']).replace('_', '_<wbr>')}</td>
      <td class="notes">{'<span class="flag">OPEN</span> ' if is_open else ''}{esc(r['Notes'])}</td>
    </tr>"""


def table(rows):
    head = """
    <thead><tr>
      <th class="chk"></th><th class="num">#</th><th class="qty">Qty</th>
      <th class="ref">Reference</th><th class="val">Value</th><th class="desc">Description</th>
      <th class="part">MPN / Manufacturer</th><th class="fp">Footprint</th><th class="notes">Notes</th>
    </tr></thead>"""
    return f"<table>{head}<tbody>{''.join(row_html(r) for r in rows)}</tbody></table>"


CSS = """
@page {
  size: A4 landscape;
  margin: 10mm 10mm 12mm 10mm;
  @bottom-left  { content: "meshthingy BOM · rev %(rev)s · %(date)s"; font: 7pt Inter, sans-serif; color: #777; }
  @bottom-right { content: "Page " counter(page) " of " counter(pages); font: 7pt Inter, sans-serif; color: #777; }
}
* { box-sizing: border-box; }
body { font-family: Inter, "DejaVu Sans", sans-serif; font-size: 7.3pt; color: #111; margin: 0; }
header { display: flex; justify-content: space-between; align-items: flex-end;
         border-bottom: 1.5pt solid #111; padding-bottom: 3mm; margin-bottom: 3mm; }
h1 { font-size: 16pt; margin: 0; letter-spacing: -0.2pt; }
h1 small { font-weight: 400; color: #555; font-size: 10pt; margin-left: 2mm; }
.meta { text-align: right; font-size: 8pt; color: #444; line-height: 1.45; }
.stats { display: flex; gap: 6mm; margin: 0 0 3mm 0; font-size: 8pt; }
.stats b { font-size: 11pt; margin-right: 1mm; }
.legend { margin-left: auto; color: #555; }
h2 { font-size: 9.5pt; margin: 4mm 0 1.5mm 0; text-transform: uppercase; letter-spacing: 0.6pt; }
table { width: 100%%; border-collapse: collapse; table-layout: fixed; }
thead { display: table-header-group; }
tr, .keep { page-break-inside: avoid; }
th { text-align: left; font-weight: 600; font-size: 6.6pt; text-transform: uppercase; letter-spacing: 0.3pt;
     background: #eee; border-bottom: 1pt solid #111; padding: 1.2mm 1.4mm; }
td { padding: 0.8mm 1.4mm; border-bottom: 0.5pt solid #ccc; vertical-align: top; line-height: 1.25; }
tbody tr:nth-child(even) td { background: #f7f7f7; }
tr.open td { background: #fff4d6 !important; }
th.chk, td.chk { width: 6mm; }  th.num, td.num { width: 6mm; color: #666; }
th.qty, td.qty { width: 8mm; text-align: right; } td.qty { font-weight: 700; font-size: 8.5pt; }
th.ref { width: 30mm; } th.val { width: 25mm; } th.desc { width: 50mm; }
th.part { width: 36mm; } th.fp { width: 38mm; }
td.ref { font-family: "DejaVu Sans Mono", monospace; font-size: 7pt; }
td.val { font-weight: 600; }
td.fp { font-family: "DejaVu Sans Mono", monospace; font-size: 6.4pt; color: #444; }
td.notes { font-size: 7pt; color: #333; }
.mpn { font-family: "DejaVu Sans Mono", monospace; font-size: 7pt; font-weight: 600; }
.mfr { color: #555; font-size: 6.8pt; }
.any { color: #999; font-style: italic; }
.box { display: inline-block; width: 3.2mm; height: 3.2mm; border: 0.8pt solid #333; border-radius: 0.5mm; }
.flag { display: inline-block; background: #b26a00; color: #fff; font-weight: 700; font-size: 5.8pt;
        padding: 0.2mm 1mm; border-radius: 0.6mm; letter-spacing: 0.3pt; }
"""


def main():
    with SRC.open(newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    board = [r for r in rows if not r["Reference"].startswith("(")]
    offboard = [r for r in rows if r["Reference"].startswith("(")]
    n_open = sum(bool(OPEN_ITEM.search(r["MPN"] + " " + r["Notes"])) for r in rows)
    n_parts = sum(int(r["Qty"]) for r in board)
    rev, date = git_rev(), datetime.date.today().isoformat()

    doc = f"""<!doctype html><html><head><meta charset="utf-8">
    <style>{CSS % {'rev': rev, 'date': date}}</style></head><body>
    <header>
      <h1>meshthingy <small>Bill of Materials</small></h1>
      <div class="meta">Source: bom/meshthingy-bom.csv<br>Rev {esc(rev)} · {date}</div>
    </header>
    <div class="stats">
      <span><b>{len(board)}</b>board lines</span>
      <span><b>{n_parts}</b>placed parts</span>
      <span><b>{len(offboard)}</b>off-board items</span>
      <span><b>{n_open}</b>open items</span>
      <span class="legend">☐ tick when kitted · <span class="flag">OPEN</span> = decide before ordering</span>
    </div>
    <h2>Board assembly</h2>{table(board)}
    <section class="keep"><h2>Off-board items</h2>{table(offboard)}</section>
    </body></html>"""

    HTML(string=doc, base_url=str(HERE)).write_pdf(OUT)
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
