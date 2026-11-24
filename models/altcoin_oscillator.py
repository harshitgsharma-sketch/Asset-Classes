"""Top-coin Entry/Exit Oscillator (v1, indicative, 24-Nov-2026): Ethereum, XRP, BNB, Solana.

Same engine as the other models: per-indicator score = clamp(1 + 99*(x - cheap)/(rich - cheap), 1, 100)
(high = rich / headwind); weight W = Impact x Severity x Reliability x Stability; blank inputs are
skipped and weights re-normalised inside each bucket; a bucket resting on one live indicator moves only
half-way from 50; Oscillator = 0.45 Valuation + 0.35 Timing + 0.20 Filter (Bitcoin model's split).

All inputs are price-derived from models/crypto-prices-monthly.csv (scripts/fetch_crypto_history.py),
plus the Bitcoin model's Filter bucket (macro and liquidity), imported from btc-score-log.csv.
Staging rule as for Bitcoin: Filter >= 70 while Oscillator <= 35 -> "BUY - STAGED (macro filter high)".

No on-chain or flow data yet, so these are price-and-cycle readings, not full models.
Not investment advice.

Usage: python3 altcoin_oscillator.py [score|all]
"""
import math
import sys

import numpy as np
import pandas as pd

PRICES, BTC_LOG, LOG = "crypto-prices-monthly.csv", "btc-score-log.csv", "altcoin-score-log.csv"
BUCKETS = {"Valuation": 0.45, "Timing": 0.35, "Filter": 0.20}
THIN_SHRINK, MIN_LIVE, FIRST = 0.5, 6, "2021-11"
COINS = [("ETH", "Ethereum", "eth_usd"), ("XRP", "XRP", "xrp_usd"), ("BNB", "BNB", "bnb_usd"), ("SOL", "Solana", "sol_usd")]
# id, name, bucket, derive, I, S, R, St, cheap, rich
IND = [
    ("V1", "Price percentile in its own history", "Valuation", "pctl", 5, 4, 0.75, 0.75, 5, 95),
    ("V2", "Price vs its 4-year average (%)", "Valuation", "vs48", 4, 4, 0.75, 1.0, -50, 150),
    ("V3", "Price in BTC: percentile in its own history", "Valuation", "btc_pctl", 3, 3, 0.75, 1.0, 5, 95),
    ("T1", "Price / 10-month average (~200-DMA)", "Timing", "ma10", 4, 5, 1.0, 1.0, 0.6, 1.6),
    ("T2", "Monthly RSI(14)", "Timing", "rsi", 2, 4, 0.75, 1.0, 30, 85),
    ("T3", "12-month change (%)", "Timing", "chg12", 2, 3, 0.75, 1.0, -60, 200),
    ("T4", "Distance from all-time high (%)", "Timing", "dath", 3, 3, 0.75, 1.0, -85, 0),
    ("F1", "Bitcoin model Filter bucket (macro, liquidity)", "Filter", "btc_filter", 4, 4, 0.875, 1.0, 1, 100),
]


def band(x):
    return ("STRONG BUY" if x <= 20 else "BUY" if x <= 35 else "ACCUMULATE" if x <= 50
            else "HOLD" if x <= 65 else "TRIM" if x <= 80 else "EXIT")


def rsi(s, n=14):
    d = s.diff()
    up = d.clip(lower=0).ewm(alpha=1/n, adjust=False, min_periods=n).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1/n, adjust=False, min_periods=n).mean()
    return 100 - 100/(1 + up/dn)


def pctl(s, minp=24):
    return s.expanding(min_periods=minp).apply(lambda w: (w <= w[-1]).mean()*100, raw=True)


def derive(px, btc, filt):
    p = px.dropna()
    d = pd.DataFrame(index=p.index)
    d["price"] = p
    d["pctl"] = pctl(p)
    d["vs48"] = (p/p.rolling(48, min_periods=24).mean() - 1)*100
    r = (p/btc.reindex(p.index)).dropna()
    d["btc_pctl"] = pctl(r)
    d["ma10"] = p/p.rolling(10).mean()
    d["rsi"] = rsi(p)
    d["chg12"] = (p/p.shift(12) - 1)*100
    d["dath"] = (p/p.cummax() - 1)*100
    d["btc_filter"] = filt.reindex(p.index)
    return d


def score_row(row):
    bsc, drivers, live, w_all, w_live = {}, [], 0, 0.0, 0.0
    for b in BUCKETS:
        num = den = 0.0
        n = 0
        for i in IND:
            if i[2] != b:
                continue
            w = i[4]*i[5]*i[6]*i[7]
            w_all += w
            x = row.get(i[3])
            if x is None or (isinstance(x, float) and math.isnan(x)):
                continue
            s = float(np.clip(1 + 99*(x - i[8])/(i[9] - i[8]), 1, 100))
            num += w*s
            den += w
            n += 1
            w_live += w
            drivers.append((i[0], i[1], round(float(x), 2), round(s)))
        live += n
        if den:
            sc = num/den
            bsc[b] = 50 + (sc - 50)*THIN_SHRINK if n == 1 else sc
    if live < MIN_LIVE or not bsc:
        return None
    osc = sum(BUCKETS[b]*bsc[b] for b in bsc)/sum(BUCKETS[b] for b in bsc)
    sig = band(osc)
    if bsc.get("Filter", 0) >= 70 and osc <= 35:
        sig = "BUY - STAGED (macro filter high)"
    return {"osc": osc, "b": bsc, "sig": sig, "live": live, "cov": w_live/w_all, "drivers": drivers}


def cmd_score():
    px = pd.read_csv(PRICES, dtype={"month": str}).set_index("month")
    bl = pd.read_csv(BTC_LOG, dtype={"month": str}).set_index("month")["filter"]
    rows = []
    for key, name, col in COINS:
        d = derive(px[col], px["btc_usd"], bl)
        for m, r in d.iterrows():
            if m < FIRST:
                continue
            s = score_row(r.to_dict())
            if s is None:
                continue
            rows.append({"month": m, "coin": key, "name": name, "price_usd": round(float(r["price"]), 6),
                         "oscillator": round(s["osc"], 1), "valuation": round(s["b"].get("Valuation", float("nan")), 1),
                         "timing": round(s["b"].get("Timing", float("nan")), 1), "filter": round(s["b"].get("Filter", float("nan")), 1),
                         "coverage": round(s["cov"], 2), "live": f"{s['live']}/{len(IND)}", "signal": s["sig"]})
    log = pd.DataFrame(rows).sort_values(["coin", "month"]).reset_index(drop=True)
    log.to_csv(LOG, index=False)
    last = log.groupby("coin").tail(1)
    print("TOP-COIN OSCILLATOR (1 = cheap/buy, 100 = rich/sell) — v1, indicative, price-and-cycle only")
    print(last[["coin", "month", "price_usd", "oscillator", "valuation", "timing", "filter", "live", "signal"]].to_string(index=False))
    return log


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "score"
    if cmd in ("score", "all", "table", "drivers"):
        cmd_score()
    else:
        print(__doc__)
