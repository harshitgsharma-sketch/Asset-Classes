"""Nifty 500 Stock Screener — Entry/Exit Oscillator (v1, indicative) — "Asset Mgmt" project.

Same engine as nifty_oscillator.py / sector_oscillator.py:
  per-indicator score = clamp(1 + 99*(x - cheap)/(rich - cheap), 1, 100)
  weight W = Impact x Severity x Reliability x Stability; blanks skipped, weights
  re-normalised inside each bucket; a missing bucket drops out. High score = expensive / headwind.
Three buckets: Valuation (own history + vs sector) 50% / Quality 25% / Momentum 25%.
Thin-bucket rule: a bucket resting on one indicator moves only half-way from 50.

Files (project, under claude/):
  nifty500-stocks-config.json         per-stock set-up: sector, sector index, type, flags
  nifty500-stocks-inputs-monthly.csv  long format, one row per (month, ticker); raw inputs.
                                      Row ticker=NIFTY50 holds the benchmark px1/px3 and gsec10.
  nifty-sectors-inputs-monthly.csv    (read only) sector index PE for V1
  nifty500-stocks-score-log.csv       output (regenerated)

Any ticker in the inputs CSV is scored, even if not in the config (as nonfin vs Nifty 50, flagged),
so the universe grows by appending rows. scripts/fetch_stock_fundamentals.py fills the Nifty 500 from
Yahoo Finance and writes name/sector/sector_index/type columns used for stocks not in the config.
Usage: python3 stock_oscillator.py [score|drivers|table|all] [TICKER ...]
"""
import json, sys, math, os
import numpy as np, pandas as pd

CONFIG, INPUTS, LOG = "nifty500-stocks-config.json", "nifty500-stocks-inputs-monthly.csv", "nifty500-stocks-score-log.csv"
SECTOR_INPUTS = "nifty-sectors-inputs-monthly.csv"

# id: (name, bucket, type, I, S, R, St, cheap, rich, applies_to)
# applies_to: "all" or list of stock types (nonfin, lender, insurer, holdco)
SPEC = {
 # ---- Valuation (own history + vs sector)
 "V1": ("PE / sector index PE (x)",                    "V", "Leading", 5, 4, 0.875, 0.875, 0.6, 1.8, "all"),
 "V2": ("Re-rating: price CAGR - EPS CAGR, 5 or 3 yr (pp/yr)", "V", "Leading", 4, 4, 0.75, 0.75, -10, 10, "all"),
 "V3": ("Earnings yield - 10-yr G-sec (pp)",           "V", "Leading", 4, 3, 0.875, 1.0, 3, -5, "all"),
 "V4": ("P/B / (5-yr ROE / 12.5%) (x)",                "V", "Leading", 5, 4, 0.875, 0.875, 0.7, 2.5, ["lender"]),
 "V5": ("PE vs own 5-yr median PE (%)",                "V", "Leading", 5, 5, 1.0, 0.75, -35, 35, "all"),
 # ---- Quality (low score = high quality)
 "Q1": ("ROE, 5-yr average (%)",                       "Q", "Lagging", 5, 4, 0.875, 0.875, 25, 8, "all"),
 "Q2": ("Debt / equity (x)",                           "Q", "Lagging", 4, 4, 0.875, 0.875, 0.0, 1.5, ["nonfin"]),
 "Q3": ("EPS stability: down or loss years of last 5", "Q", "Lagging", 3, 3, 0.75, 0.75, 0, 3, "all"),
 "Q4": ("ROE trend: latest - 5-yr avg (pp)",           "Q", "Coincident", 3, 3, 0.75, 0.75, 5, -8, "all"),
 # ---- Momentum
 "M1": ("1-yr price return - Nifty 50 (pp)",           "M", "Coincident", 4, 4, 0.875, 0.75, 30, -30, "all"),
 "M2": ("3-yr price CAGR - Nifty 50 (pp/yr), reversal", "M", "Leading", 2, 3, 0.625, 0.75, -15, 15, "all"),
}
TYPE_ANCHORS = {"lender": {"Q1": (18, 8)}}
BUCKETS = {"V": .50, "Q": .25, "M": .25}
BUCKET_NAME = {"V": "Valuation", "Q": "Quality", "M": "Momentum"}
THIN_SHRINK = 0.5
# Design set = the 11 indicators above (V5 needs own PE history; not sourced in v1).

def band(x):
    return ("STRONG BUY" if x <= 20 else "BUY" if x <= 35 else "ACCUMULATE" if x <= 50
            else "HOLD" if x <= 65 else "TRIM" if x <= 80 else "EXIT")

def ind_score(c, r, x):
    return float(np.clip(1 + 99*(x - c)/(r - c), 1, 100))

def num(v):
    try:
        f = float(v); return None if math.isnan(f) else f
    except (TypeError, ValueError):
        return None

def eps_list(s):
    if not isinstance(s, str): return []
    return [float(x) for x in s.split() if num(x) is not None]

def derive(row, bench, sector_pe, ci):
    """Raw columns -> indicator inputs. Returns (inputs, data-flags)."""
    out, notes = {}, []
    pe, price, bv = num(row.get("pe")), num(row.get("price")), num(row.get("bv"))
    gsec = num(bench.get("gsec10"))
    if pe is not None and pe <= 0: pe = None
    if pe is None: notes.append("no PE (loss or n/a)")
    if pe is not None and sector_pe:
        out["V1"] = pe/sector_pe
    eps = eps_list(row.get("eps_hist"))
    e_cagr = None
    # V2 horizon: 5 yrs when 6 annual EPS are known (screener.in), else 3 yrs on the last 4 (Yahoo)
    span = 5 if len(eps) >= 6 else 3 if len(eps) >= 4 else None
    px_n = num(row.get("px5")) if span == 5 else num(row.get("px3"))
    if span:
        base, last = eps[-(span + 1)], eps[-1]
        if base > 0 and last > 0:
            e_cagr = ((last/base)**(1/span) - 1)*100
            if span == 3: notes.append("V2 on 3-yr window")
        else:
            notes.append("V2 skipped: loss-year EPS base")
    elif num(row.get("pg5")) is not None:
        e_cagr = num(row.get("pg5")); px_n = num(row.get("px5")); notes.append("V2 uses profit CAGR (EPS history short)")
    if None not in (px_n, e_cagr): out["V2"] = px_n - e_cagr
    if None not in (pe, gsec): out["V3"] = 100/pe - gsec
    roe5, roe = num(row.get("roe5")), num(row.get("roe"))
    if roe5 is None and num(row.get("roe3")) is not None:
        roe5 = num(row.get("roe3")); notes.append("Q1/Q4/V4 use 3-yr ROE (no 5-yr)")
    if ci["type"] == "lender" and None not in (price, bv, roe5) and bv > 0 and roe5 > 0:
        out["V4"] = (price/bv)/(roe5/12.5)
    med = num(row.get("pe_med5"))
    if None not in (pe, med): out["V5"] = (pe/med - 1)*100
    if roe5 is not None: out["Q1"] = roe5
    debt, eq = num(row.get("debt")), num(row.get("equity"))
    if None not in (debt, eq) and eq > 0: out["Q2"] = debt/eq
    if len(eps) >= 4:
        last = eps[-6:]
        bad = sum(1 for a, b in zip(last, last[1:]) if b < a) + sum(1 for e in last[1:] if e <= 0)
        out["Q3"] = min(bad, 5)
        if len(eps) < 6: notes.append(f"Q3 on {len(eps)} yrs of EPS")
    if None not in (roe, roe5): out["Q4"] = roe - roe5
    p1, b1 = num(row.get("px1")), num(bench.get("px1"))
    if None not in (p1, b1): out["M1"] = p1 - b1
    p3, b3 = num(row.get("px3")), num(bench.get("px3"))
    if None not in (p3, b3): out["M2"] = p3 - b3
    return out, notes

def applies(k, ci):
    a = SPEC[k][9]
    return a == "all" or ci["type"] in a

def anchors(k, ci):
    ov = ci.get("anchors", {}).get(k) or TYPE_ANCHORS.get(ci["type"], {}).get(k)
    return (ov[0], ov[1]) if ov else (SPEC[k][7], SPEC[k][8])

def score_stock(ind, ci, pg_ttm):
    res, drivers, have_n, all_n = {}, [], 0, 0
    for b in BUCKETS:
        num_ = den = 0.0
        for k in SPEC:
            if SPEC[k][1] != b or not applies(k, ci) or k in ci.get("skip", []): continue
            all_n += 1
            x = ind.get(k)
            if x is None: continue
            _, _, _, I, S, R, St, *_ = SPEC[k]; w = I*S*R*St
            c, r = anchors(k, ci); s = ind_score(c, r, x)
            num_ += w*s; den += w; have_n += 1
            drivers.append({"id": k, "name": SPEC[k][0], "bucket": b, "type": SPEC[k][2],
                            "value": round(x, 2), "score": round(s), "w": round(w, 1)})
        res[b] = num_/den if den else None
        if sum(1 for d in drivers if d["bucket"] == b) == 1:
            res[b] = 50 + (res[b] - 50)*THIN_SHRINK
            for d in drivers:
                if d["bucket"] == b: d["thin"] = True
    have = {b: v for b, v in res.items() if v is not None}
    tot = sum(BUCKETS[b] for b in have)
    osc = sum(BUCKETS[b]*v for b, v in have.items())/tot if tot else None
    for d in drivers:
        b = d["bucket"]; bden = sum(x["w"] for x in drivers if x["bucket"] == b)
        d["pull"] = round((BUCKETS[b]/tot)*(d["w"]/bden)*(d["score"] - 50)*(THIN_SHRINK if d.get("thin") else 1), 2) if tot else 0
    sig = band(osc) if osc is not None else "n/a"
    flags = []
    V, Q, M = res.get("V"), res.get("Q"), res.get("M")
    if V is None:
        sig = "NOT RATED (no valuation input)"
    # Veto: falling knife = cheap overall but profits collapsing or price trend broken
    if osc is not None and osc <= 35 and ((pg_ttm is not None and pg_ttm <= -20) or (M is not None and M >= 75)):
        sig = "BUY VETOED - wait (falling knife)"
    if V is not None and Q is not None and V <= 35 and Q >= 65:
        flags.append("value-trap check: cheap but weak quality")
    if V is not None and Q is not None and V >= 66 and Q <= 30:
        flags.append("quality at a price: great business, rich valuation")
    return {"osc": osc, "buckets": res, "signal": sig, "coverage": f"{have_n}/{all_n}",
            "drivers": drivers, "flags": flags}

def load():
    cfg = json.load(open(CONFIG))
    df = pd.read_csv(INPUTS, dtype={"month": str})
    sec = pd.read_csv(SECTOR_INPUTS, dtype={"month": str}) if os.path.exists(SECTOR_INPUTS) else None
    return cfg, df, sec

def sector_pe_for(sec, month, key):
    if sec is None: return None, None
    g = sec[(sec["index"] == key) & (sec.month <= month)].sort_values("month")
    if g.empty: return None, None
    r = g.iloc[-1]
    return num(r["pe"]), r["month"]

def run(keys=None, verbose=True):
    cfg, df, sec = load()
    idx = {c["ticker"]: c for c in cfg["stocks"]}
    rows = []
    for month, g in df.groupby("month"):
        g = g.set_index("ticker")
        if "NIFTY50" not in g.index: continue
        bench = g.loc["NIFTY50"].to_dict()
        for t, r in g.iterrows():
            if t == "NIFTY50": continue
            if t in idx:
                ci = dict(idx[t])
            else:   # auto-classified by scripts/fetch_stock_fundamentals.py (NSE industry + Yahoo industry)
                rr = r.to_dict(); g_ = lambda k, d: rr.get(k) if isinstance(rr.get(k), str) and rr.get(k) else d
                ci = {"ticker": t, "name": g_("name", t), "sector": g_("sector", "?"),
                      "sector_index": g_("sector_index", "NIFTY50"), "type": g_("type", "nonfin"),
                      "flags": [] if g_("sector_index", None) else ["not classified: scored as nonfin vs Nifty 50"]}
            spe, smonth = sector_pe_for(sec, month, ci["sector_index"])
            ind, notes = derive(r.to_dict(), bench, spe, ci)
            s = score_stock(ind, ci, num(r.get("pg_ttm")))
            if s["osc"] is None: continue
            if smonth and smonth != month: notes.append(f"sector PE from {smonth} (stale)")
            flags = s["flags"] + list(ci.get("flags", [])) + notes
            bk = s["buckets"]
            rows.append({"month": month, "ticker": t, "name": ci["name"], "sector": ci["sector"], "type": ci["type"],
                         "score": round(s["osc"], 1), "signal": s["signal"],
                         "valuation": None if bk.get("V") is None else round(bk["V"], 1),
                         "quality": None if bk.get("Q") is None else round(bk["Q"], 1),
                         "momentum": None if bk.get("M") is None else round(bk["M"], 1),
                         "coverage": s["coverage"], "pe": num(r.get("pe")), "sector_index": ci["sector_index"],
                         "sector_pe": spe, "flags": "; ".join(flags), "source": r.get("source")})
            if verbose and (not keys or t in keys) and month == df.month.max():
                print(f"\n=== {ci['name']} ({t}) {month}: SCORE {s['osc']:.1f} {s['signal']} | coverage {s['coverage']}"
                      f" | PE {r.get('pe')} vs {ci['sector_index']} {spe}")
                print("   buckets: " + " | ".join(f"{BUCKET_NAME[b]} {'—' if v is None else round(v,1)}" for b, v in bk.items()))
                for d in sorted(s["drivers"], key=lambda d: -d["pull"]):
                    print(f"   {d['id']:<3} {d['name']:<46} {d['bucket']} {d['type']:<10} value={d['value']:<8} score={d['score']:>3} W={d['w']:<5} pull={d['pull']:+.2f}")
                if flags: print("   flags: " + "; ".join(flags))
    log = pd.DataFrame(rows).sort_values(["month", "score"])
    log.to_csv(LOG, index=False)
    return log

def table(log, n=10):
    m = log.month.max(); last = log[log.month == m].sort_values("score")
    cols = ["ticker", "sector", "score", "signal", "valuation", "quality", "momentum", "pe", "coverage"]
    print(f"\nCHEAPEST {n} ({m})"); print(last.head(n)[cols].to_string(index=False))
    print(f"\nRICHEST {n} ({m})"); print(last.tail(n).iloc[::-1][cols].to_string(index=False))
    print(f"\nFULL RANKED TABLE ({len(last)} stocks, cheapest first)"); print(last[cols].to_string(index=False))
    print("\nSignal counts: " + ", ".join(f"{k} {v}" for k, v in last.signal.value_counts().items()))
    print("\nFlags:")
    for _, r in last.iterrows():
        if isinstance(r["flags"], str) and r["flags"]: print(f"  {r['ticker']}: {r['flags']}")

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    keys = sys.argv[2:]
    log = run(keys, verbose=cmd in ("drivers", "score") or (cmd == "all" and bool(keys)))
    if cmd in ("all", "table"): table(log)
