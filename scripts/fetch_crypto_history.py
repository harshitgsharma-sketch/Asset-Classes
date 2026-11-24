#!/usr/bin/env python3
"""Month-end USD closes for Bitcoin and the largest coins after it (stablecoins excluded).

Writes models/crypto-prices-monthly.csv for models/altcoin_oscillator.py, from Yahoo Finance
monthly closes (same chart API as fetch_parabolic.py). A coin that fails keeps its previous
values. Run daily by the refresh workflow.

Usage: python3 -I scripts/fetch_crypto_history.py
"""
import csv
import datetime
import json
import os
import time
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "models", "crypto-prices-monthly.csv")
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"}
COINS = {"btc_usd": "BTC-USD", "eth_usd": "ETH-USD", "xrp_usd": "XRP-USD", "bnb_usd": "BNB-USD", "sol_usd": "SOL-USD"}


def monthly(symbol):
    url = ("https://query1.finance.yahoo.com/v8/finance/chart/" + urllib.parse.quote(symbol, safe="")
           + "?range=max&interval=1mo")
    last = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
                res = json.load(r)["chart"]["result"][0]
            out = {}
            for t, c in zip(res["timestamp"], res["indicators"]["quote"][0]["close"]):
                if c:
                    out[datetime.datetime.utcfromtimestamp(t).strftime("%Y-%m")] = float(c)
            if len(out) < 24:
                raise ValueError(f"only {len(out)} months")
            return out
        except Exception as e:
            last = e
            time.sleep(2 * (attempt + 1))
    raise last


def main():
    old = {}
    if os.path.exists(OUT):
        for r in csv.DictReader(open(OUT)):
            old[r["month"]] = r
    data, failed = {}, []
    for col, sym in COINS.items():
        try:
            data[col] = monthly(sym)
        except Exception as e:
            failed.append(f"{col} ({type(e).__name__})")
            data[col] = {m: float(r[col]) for m, r in old.items() if r.get(col)}
    months = sorted(set().union(*[set(v) for v in data.values()]))
    with open(OUT, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["month"] + list(COINS))
        for m in months:
            w.writerow([m] + [(f"{data[c][m]:.6g}" if m in data[c] else "") for c in COINS])
    print(f"crypto history: {len(months)} months ({months[0]} to {months[-1]}) -> {os.path.relpath(OUT, ROOT)}"
          + (f"; failed, kept previous: {', '.join(failed)}" if failed else ""))


if __name__ == "__main__":
    main()
