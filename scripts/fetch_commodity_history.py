#!/usr/bin/env python3
"""Monthly price history for the commodities the board scores from long history.

Writes models/commodity-prices-monthly.csv (month, one column per series).
  1. Base: World Bank Commodity Price Data ("Pink Sheet"), monthly averages since 1960,
     usually published early in the following month. Parsed with the standard library
     (an .xlsx file is zipped XML), so the GitHub Action needs no extra package.
  2. Current month: Yahoo Finance month-to-date close for series whose Yahoo future trades
     daily (aluminium, iron ore, natural gas). Zinc has no live Yahoo series (the COMEX zinc
     future barely trades), so it stays on the latest World Bank month.
A source that fails keeps the previous values. Run daily by the refresh workflow.

Usage: python3 -I scripts/fetch_commodity_history.py
"""
import csv
import datetime
import io
import json
import os
import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "models", "commodity-prices-monthly.csv")
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"}
# The World Bank keeps a yearly folder; newest first. Add next year's folder here when it appears.
WB_URLS = [
    "https://thedocs.worldbank.org/en/doc/74e8be41ceb20fa0da750cda2f6b9e4e-0050012026/related/CMO-Historical-Data-Monthly.xlsx",
    "https://thedocs.worldbank.org/en/doc/18675f1d1639c7a34d463f59263ba0a2-0050012025/related/CMO-Historical-Data-Monthly.xlsx",
]
# column -> (World Bank 'Monthly Prices' header, Yahoo symbol for the current month or None)
SERIES = {
    "aluminium_usd_t": ("Aluminum", "ALI=F"),          # $/mt
    "zinc_usd_t": ("Zinc", None),                      # $/mt
    "ironore_usd_t": ("Iron ore, cfr spot", "TIO=F"),  # $/dmtu (~$/t)
    "natgas_usd_mmbtu": ("Natural gas, US", "NG=F"),   # $/mmbtu, Henry Hub
}
NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
      "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships"}


def get(url, timeout=60):
    last = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
                return r.read()
        except Exception as e:
            last = e
            time.sleep(2 * (attempt + 1))
    raise last


def world_bank():
    """{column: {YYYY-MM: value}} from the Pink Sheet 'Monthly Prices' sheet."""
    err = None
    for url in WB_URLS:
        try:
            raw = get(url)
            if raw[:2] != b"PK":
                raise ValueError("not an xlsx")
            z = zipfile.ZipFile(io.BytesIO(raw))
            wb = ET.fromstring(z.read("xl/workbook.xml"))
            rels = {r.get("Id"): r.get("Target") for r in ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))}
            sheets = {s.get("name"): rels[s.get("{%s}id" % NS["r"])] for s in wb.find("m:sheets", NS)}
            ss = ["".join(t.text or "" for t in si.iter("{%s}t" % NS["m"]))
                  for si in ET.fromstring(z.read("xl/sharedStrings.xml")).findall("m:si", NS)]
            target = sheets["Monthly Prices"].lstrip("/")
            sh = ET.fromstring(z.read(target if target.startswith("xl/") else "xl/" + target))
            rows = []
            for row in sh.iter("{%s}row" % NS["m"]):
                r = {}
                for c in row.findall("m:c", NS):
                    v = c.find("m:v", NS)
                    if v is not None:
                        r[re.match(r"[A-Z]+", c.get("r")).group()] = ss[int(v.text)] if c.get("t") == "s" else v.text
                rows.append(r)
            hdr = next(r for r in rows if any(str(v).strip() == "Aluminum" for v in r.values()))
            colof = {str(v).strip(): k for k, v in hdr.items()}
            out = {c: {} for c in SERIES}
            for r in rows:
                m = re.match(r"^(\d{4})M(\d{2})$", str(r.get("A", "")))
                if not m:
                    continue
                ym = f"{m.group(1)}-{m.group(2)}"
                for col, (name, _) in SERIES.items():
                    x = r.get(colof[name])
                    try:
                        out[col][ym] = round(float(x), 4)
                    except (TypeError, ValueError):
                        pass
            return out, url
        except Exception as e:
            err = e
    raise err


def yahoo_month_close(symbol):
    url = ("https://query1.finance.yahoo.com/v8/finance/chart/" + urllib.parse.quote(symbol, safe="")
           + "?range=1mo&interval=1d")
    res = json.loads(get(url, 30))["chart"]["result"][0]
    pts = [(datetime.datetime.utcfromtimestamp(t), c) for t, c in zip(res["timestamp"], res["indicators"]["quote"][0]["close"]) if c]
    t, c = pts[-1]
    return t.strftime("%Y-%m"), round(float(c), 4)


def main():
    old = {}
    if os.path.exists(OUT):
        for r in csv.DictReader(open(OUT)):
            old[r["month"]] = r
    data = {c: {m: float(r[c]) for m, r in old.items() if r.get(c)} for c in SERIES}
    notes = []
    try:
        wb, url = world_bank()
        for c in SERIES:
            data[c] = wb[c]
        last = max(max(v) for v in wb.values() if v)
        notes.append(f"World Bank to {last}")
    except Exception as e:
        notes.append(f"World Bank failed ({type(e).__name__}); kept previous")
        last = max((m for v in data.values() for m in v), default="")
    for c, (_, sym) in SERIES.items():
        if not sym:
            continue
        try:
            ym, px = yahoo_month_close(sym)
            if ym > max(data[c], default=""):
                data[c][ym] = px
                notes.append(f"{c} {ym} from Yahoo")
        except Exception as e:
            notes.append(f"{c} Yahoo failed ({type(e).__name__})")
    months = sorted(set().union(*[set(v) for v in data.values()]))
    months = [m for m in months if m >= "2000-01"]
    with open(OUT, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["month"] + list(SERIES))
        for m in months:
            w.writerow([m] + [data[c].get(m, "") for c in SERIES])
    print(f"commodity history: {len(months)} months ({months[0]} to {months[-1]}) -> {os.path.relpath(OUT, ROOT)}; " + "; ".join(notes))


if __name__ == "__main__":
    main()
