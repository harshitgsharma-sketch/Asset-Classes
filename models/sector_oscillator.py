"""Nifty Sector / Size / Theme Index Entry-Exit Oscillator (v1) — "Asset Mgmt" project.

Same engine as nifty_oscillator.py:
  per-indicator score = clamp(1 + 99*(x - cheap)/(rich - cheap), 1, 100)
  weight W = Impact x Severity x Reliability x Stability; blanks skipped, weights
  re-normalised inside each bucket. High score = expensive / headwind.
Four buckets (Valuation / Sector cycle / Timing / Filter), weights set per family.
Two outputs per index: ABSOLUTE (all buckets) and RELATIVE vs Nifty 50 (Rel indicators only).

Files (project, under claude/):
  nifty-sectors-config.json         per-index set-up: family, primary metric, overrides
  nifty-sectors-inputs-monthly.csv  long format, one row per (month, index); raw inputs
  nifty-sectors-score-log.csv       output (regenerated)

v1 data notes (see nifty-sectors-run-procedure.md):
  - Percentile inputs (pe_pct, pb_pct) are already 0-100 vs the index's own history.
    PE percentile is derived from the indexpe.in quintile band (band k of 5, lo-hi).
  - C8 uses 1-yr total return vs Nifty 50 (6-m preferred, not available yet).
  - C14 uses 5-yr EPS CAGR; C16 uses 5-yr total return vs Nifty 50.
Usage: python3 sector_oscillator.py [score|drivers|table|all] [INDEX_KEY ...]
"""
import json, sys, math
import numpy as np, pandas as pd

CONFIG, INPUTS, LOG = "nifty-sectors-config.json", "nifty-sectors-inputs-monthly.csv", "nifty-sectors-score-log.csv"

# id: (name, bucket, type, I, S, R, St, cheap, rich, families, rel)
# families: "all" or list of family keys. Inputs are columns with the same id in the inputs CSV
# (or derived in derive()).
SPEC = {
 # ---- core: Valuation
 "C1":  ("Primary valuation metric, own-history pctl", "V", "Leading", 5, 5, 1.0, 0.75, 0, 100, "all", False),
 "C3":  ("Relative PE vs Nifty 50, vs 5-yr norm (%)",  "V", "Leading", 4, 4, 0.875, 1.0, -30, 30, "all", True),
 "C12": ("Secondary valuation metric, pctl",           "V", "Leading", 3, 3, 0.75, 0.75, 0, 100, "all", False),
 "C18": ("PE vs own 5-yr median (%)",                  "V", "Leading", 5, 4, 0.875, 0.75, -35, 35, "all", False),
 "C20": ("Short-history guard: PE / Nifty 500 PE",     "V", "Leading", 4, 4, 0.875, 1.0, 1.0, 2.0, ["defence"], False),
 # ---- core: Timing
 "C4":  ("Nifty 50 model Timing bucket (macro)",       "T", "Leading", 4, 4, 0.875, 1.0, 1, 100, "all", False),
 "C8":  ("1-yr return minus Nifty 50 (pp)",            "T", "Leading", 3, 4, 0.875, 1.0, -25, 25, "all", True),
 # ---- core: Filter
 "C14": ("EPS CAGR, 5-yr (%)",                         "F", "Lagging", 3, 3, 0.75, 0.75, 25, -5, "all", False),
 "C16": ("5-yr return minus Nifty 50 (pp/yr)",         "F", "Lagging", 2, 3, 0.75, 1.0, -10, 10, "all", True),
 "C19": ("5-yr re-rating: price CAGR - EPS CAGR (pp)", "F", "Lagging", 3, 3, 0.75, 1.0, -10, 10, "all", False),
 # ---- Sector cycle modules (bucket S)
 "S1":  ("Index PE / Nifty 50 PE",                     "S", "Leading", 4, 4, 0.875, 0.875, 0.9, 1.8, ["size"], False),
 "S2":  ("MTF book YoY (%)",                           "S", "Leading", 3, 3, 0.625, 0.75, -10, 60, ["size"], False),
 "S3":  ("Small/mid MF net inflow, 3-m avg (Rs '000 cr)", "S", "Coincident", 3, 3, 0.75, 0.75, 2, 12, ["size"], False),
 # S4: AMFI sectoral/thematic fund froth (backlog #17, knowledge/sector-froth-signals.md). Average
 # own-history percentile of three measures from amfi-thematic-monthly.csv. Applied to the
 # market-wide size indices and the themes the 2024 NFO wave targeted.
 "S4":  ("Thematic-fund froth, AMFI (pctl)",           "S", "Coincident", 3, 3, 0.75, 0.75, 0, 100, ["size", "psu", "defence", "infra"], False),
 "B1":  ("System credit growth YoY (%)",               "S", "Coincident", 4, 4, 0.875, 0.75, 8, 18, ["bank"], False),
 "B2":  ("Credit minus deposit growth (pp)",           "S", "Leading", 4, 3, 0.875, 1.0, -3, 5, ["bank"], False),
 "B3":  ("Expected repo change ~6m (bp)",              "S", "Leading", 4, 3, 0.75, 1.0, 50, -75, ["bank"], False),
 "B4":  ("Bank GNPA ratio (%)",                        "S", "Lagging", 3, 3, 0.75, 0.75, 8, 2, ["bank"], False),
 "I1":  ("Top-IT cc revenue growth YoY (%)",           "S", "Coincident", 4, 4, 0.875, 0.75, -2, 15, ["it"], False),
 "I2":  ("INR depreciation vs USD, 12-m (%)",          "S", "Coincident", 3, 3, 0.75, 1.0, 6, -3, ["it", "pharma"], False),
 "K1":  ("FMCG volume growth YoY (%)",                 "S", "Coincident", 4, 4, 0.75, 0.75, -3, 10, ["cons"], False),
 "K2":  ("Food inflation, CFPI YoY (%)",               "S", "Coincident", 3, 3, 0.875, 0.75, 2, 8, ["cons"], False),
 "K3":  ("Brent 6-m change, input-cost proxy (%)",     "S", "Leading", 3, 3, 0.75, 0.75, -20, 25, ["cons", "auto"], False),
 "K4":  ("Monsoon rainfall vs LPA (%)",                "S", "Leading", 2, 3, 0.75, 0.75, 105, 90, ["cons", "auto"], False),
 "A1":  ("Domestic auto volumes YoY (%)",              "S", "Coincident", 4, 4, 0.75, 0.75, -10, 20, ["auto"], False),
 "P1":  ("Domestic pharma market growth YoY (%)",      "S", "Coincident", 3, 3, 0.75, 0.75, 12, 5, ["pharma"], False),
 "M1":  ("Commodity price vs 5-yr range (pctl)",       "S", "Coincident", 4, 3, 0.75, 0.875, 0, 100, ["comm"], False),
 "M2":  ("Commodity price 6-m change (%)",             "S", "Coincident", 3, 3, 0.625, 0.75, -20, 25, ["comm"], False),
 "R1":  ("Housing sales YoY, top cities (%)",          "S", "Coincident", 4, 4, 0.75, 0.75, -15, 25, ["realty"], False),
 "R2":  ("Home-loan / repo rate level (%)",            "S", "Leading", 3, 3, 0.75, 1.0, 7.0, 4.0, ["realty"], False),
 "G1":  ("Govt capex growth YoY, budget (%)",          "S", "Leading", 4, 3, 0.75, 0.75, 25, -5, ["infra", "psu"], False),
 "G2":  ("Defence capital budget growth YoY (%)",      "S", "Leading", 4, 3, 0.75, 0.75, 15, 0, ["defence"], False),
}
FAMILY_BUCKETS = {   # V, S, T, F
 "size":    {"V": .40, "S": .15, "T": .30, "F": .15},
 "defens":  {"V": .45, "S": .20, "T": .20, "F": .15},
 "fin":     {"V": .35, "S": .30, "T": .20, "F": .15},
 "cyclic":  {"V": .30, "S": .35, "T": .20, "F": .15},
 "growth":  {"V": .35, "S": .25, "T": .25, "F": .15},
}
THIN_SHRINK = 0.5   # a bucket resting on one indicator moves only half-way from 50
# Design core =C1..C17 in nifty-sectors-model-design.md; v1 can source these seven.
DESIGN_CORE = ["C1", "C3", "C4", "C8", "C12", "C14", "C16"]
BUCKET_NAME = {"V": "Valuation", "S": "Sector cycle", "T": "Timing", "F": "Filter"}

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

AMFI_FILE = "amfi-thematic-monthly.csv"
AMFI_MEASURES = ["flow_3m_pct_aum", "share_3m", "new_schemes_6m"]
_AMFI = None

def amfi_froth():
    """month -> froth score 0-100: mean percentile of AMFI_MEASURES against all months up to
    and including that month (expanding window, needs 24 months of history)."""
    global _AMFI
    if _AMFI is not None: return _AMFI
    _AMFI = {}
    try:
        a = pd.read_csv(AMFI_FILE, dtype={"month": str}).sort_values("month").reset_index(drop=True)
    except FileNotFoundError:
        return _AMFI
    for i in range(len(a)):
        pcts = []
        for m in AMFI_MEASURES:
            hist = a.loc[:i, m].dropna()
            x = a.loc[i, m]
            if len(hist) >= 24 and not pd.isna(x):
                pcts.append(100*(hist < x).sum()/(len(hist) - 1) if len(hist) > 1 else 50)
        if pcts: _AMFI[a.loc[i, "month"]] = round(float(np.mean(pcts)), 1)
    return _AMFI

def amfi_froth_for(month):
    """Froth score for the latest AMFI month on or before `month` (AMFI publishes ~10 days after month end)."""
    f = amfi_froth()
    ms = [m for m in f if m <= month]
    return f[max(ms)] if ms else None

def derive(row, nifty, cfg_i):
    """Turn raw columns into indicator inputs. row/nifty are dicts for the same month."""
    out = {}
    pe, n_pe = num(row.get("pe")), num(nifty.get("pe"))
    # PE percentile from quintile band (indexpe.in): band k of 5 spanning lo..hi
    k, lo, hi = num(row.get("pe_band")), num(row.get("pe_band_lo")), num(row.get("pe_band_hi"))
    pe_pct = num(row.get("pe_pct"))
    if pe_pct is None and None not in (k, lo, hi, pe) and hi > lo:
        pe_pct = 20*(k - 1) + 20*min(max((pe - lo)/(hi - lo), 0), 1)
    pb_pct = num(row.get("pb_pct"))
    prim = cfg_i["primary"]
    out["C1"], out["C12"] = (pb_pct, pe_pct) if prim == "pb" else (pe_pct, pb_pct)
    med, n_med = num(row.get("pe_med5")), num(nifty.get("pe_med5"))
    if None not in (pe, med):
        out["C18"] = (pe/med - 1)*100
    if None not in (pe, n_pe, med, n_med) and cfg_i["key"] != "NIFTY50":
        out["C3"] = ((pe/n_pe)/(med/n_med) - 1)*100
    n500 = num(row.get("_n500_pe"))
    if cfg_i["module"] == "defence" and None not in (pe, n500):
        out["C20"] = pe/n500
    if cfg_i["family"] == "size" and None not in (pe, n_pe):
        out["S1"] = pe/n_pe
    r1, n_r1 = num(row.get("ret1y")), num(nifty.get("ret1y"))
    if None not in (r1, n_r1): out["C8"] = r1 - n_r1
    r5, n_r5 = num(row.get("ret5y")), num(nifty.get("ret5y"))
    if None not in (r5, n_r5): out["C16"] = r5 - n_r5
    e5, p5 = num(row.get("eps5")), num(row.get("px5"))
    if e5 is not None: out["C14"] = e5
    if None not in (e5, p5): out["C19"] = p5 - e5
    out["C4"] = num(nifty.get("nifty_timing"))
    froth = amfi_froth_for(str(row.get("month", "")))
    if froth is not None: out["S4"] = froth
    for k_ in SPEC:                       # direct sector-cycle inputs
        if k_[0] in "SBIKAPMRG" and k_ not in out:
            v = num(row.get(k_))
            if v is not None: out[k_] = v
    return out

def weight(k, cfg_i):
    _, b, _, I, S, R, St, *_ = SPEC[k]
    if k == "C4":
        if cfg_i.get("c4") == "half": return I*S*R*St/2
        if cfg_i.get("c4") == "impact5": return 5*S*R*St
    return I*S*R*St

def applies(k, cfg_i):
    fam = SPEC[k][9]
    return fam == "all" or cfg_i["module"] in fam

def anchors(k, cfg_i):
    ov = cfg_i.get("anchors", {}).get(k)
    return (ov[0], ov[1]) if ov else (SPEC[k][7], SPEC[k][8])

def score_index(ind, cfg_i):
    bw = FAMILY_BUCKETS[cfg_i["buckets"]]
    res, drivers, cov_have, cov_all = {}, [], 0.0, 0.0
    rel_num = rel_den = 0.0
    for b in bw:
        num_ = den = 0.0
        for k in SPEC:
            if SPEC[k][1] != b or not applies(k, cfg_i) or k in cfg_i.get("skip", []):
                continue
            w = weight(k, cfg_i); cov_all += w
            x = ind.get(k)
            if x is None: continue
            c, r = anchors(k, cfg_i); s = ind_score(c, r, x)
            num_ += w*s; den += w; cov_have += w
            drivers.append({"id": k, "name": SPEC[k][0], "bucket": b, "type": SPEC[k][2],
                            "value": round(x, 2), "score": round(s), "w": round(w, 1)})
            if SPEC[k][10]: rel_num += w*s; rel_den += w
        res[b] = num_/den if den else None
        n_in = sum(1 for d in drivers if d["bucket"] == b)
        if n_in == 1:                      # thin bucket: shrink half-way to neutral 50
            res[b] = 50 + (res[b] - 50)*THIN_SHRINK
            for d in drivers:
                if d["bucket"] == b: d["thin"] = True
    have = {b: v for b, v in res.items() if v is not None}
    tot = sum(bw[b] for b in have)
    osc = sum(bw[b]*v for b, v in have.items())/tot if tot else None
    # driver pull = contribution to (osc - 50), using effective bucket share
    for d in drivers:
        b = d["bucket"]
        bden = sum(x["w"] for x in drivers if x["bucket"] == b)
        d["pull"] = round((bw[b]/tot)*(d["w"]/bden)*(d["score"] - 50)*(THIN_SHRINK if d.get("thin") else 1), 2) if tot else 0
    rel = rel_num/rel_den if rel_den else None
    sig = band(osc) if osc is not None else "n/a"
    flags = list(cfg_i.get("flags", []))
    # Veto 1 falling knife (needs Filter; EPS revisions not yet sourced)
    if osc is not None and osc <= 35 and (res.get("F") or 0) >= 70:
        sig = "BUY VETOED - wait (falling knife)"
    # Veto 3 value trap: cyclicals scored on PE-led metric while PE pctl very low
    if cfg_i["buckets"] == "cyclic" and cfg_i["primary"] == "pe" and (ind.get("C1") or 100) <= 20:
        flags.append("value-trap check: low PE in a cyclical, confirm on P/B or EV/EBITDA")
    quad = None
    if osc is not None and rel is not None:
        a = "cheap" if osc <= 35 else "rich" if osc >= 66 else "mid"
        r_ = "cheap" if rel <= 35 else "rich" if rel >= 66 else "mid"
        quad = {("cheap", "cheap"): "Strongest buy: add + overweight",
                ("cheap", "rich"): "Buy market, prefer other sectors",
                ("rich", "cheap"): "Trim market; hold this sector",
                ("rich", "rich"): "Strongest sell: trim + underweight"}.get((a, r_),
                "Overweight vs Nifty" if r_ == "cheap" else "Underweight vs Nifty" if r_ == "rich" else "Neutral")
    core = sum(1 for k in DESIGN_CORE if ind.get(k) is not None)
    return {"osc": osc, "rel": rel, "buckets": res, "signal": sig, "coverage": cov_have/cov_all if cov_all else 0,
            "core": f"{core}/17",
            "drivers": drivers, "flags": flags, "quadrant": quad}

def load():
    cfg = json.load(open(CONFIG))
    df = pd.read_csv(INPUTS, dtype={"month": str})
    return cfg, df

def run(keys=None, verbose=True):
    cfg, df = load()
    idx = {c["key"]: c for c in cfg["indices"]}
    rows = []
    for month, g in df.groupby("month"):
        g = g.set_index("index")
        if "NIFTY50" not in g.index: continue
        nifty = g.loc["NIFTY50"].to_dict()
        n500 = g.loc["NIFTY500", "pe"] if "NIFTY500" in g.index else None
        for key, r in g.iterrows():
            if key not in idx or key == "NIFTY50": continue
            ci = idx[key]
            rd = r.to_dict(); rd["_n500_pe"] = n500
            ind = derive(rd, nifty, ci)
            s = score_index(ind, ci)
            if s["osc"] is None: continue
            rows.append({"month": month, "index": key, "name": ci["name"], "family": ci["family"],
                         "absolute": round(s["osc"], 1),
                         "valuation": None if s["buckets"].get("V") is None else round(s["buckets"]["V"], 1),
                         "sector_cycle": None if s["buckets"].get("S") is None else round(s["buckets"]["S"], 1),
                         "timing": None if s["buckets"].get("T") is None else round(s["buckets"]["T"], 1),
                         "filter": None if s["buckets"].get("F") is None else round(s["buckets"]["F"], 1),
                         "relative": None if s["rel"] is None else round(s["rel"], 1),
                         "signal": s["signal"], "quadrant": s["quadrant"],
                         "coverage": round(s["coverage"], 2), "core_of_17": s["core"], "flags": "; ".join(s["flags"]),
                         "pe": r.get("pe"), "source": r.get("source")})
            if verbose and (not keys or key in keys) and month == df.month.max():
                print(f"\n=== {ci['name']} ({key}) {month}: ABS {s['osc']:.1f} {s['signal']} | REL {s['rel'] if s['rel'] is None else round(s['rel'],1)} "
                      f"| {s['quadrant']} | coverage {s['coverage']:.0%} of v1 set, design core {s['core']}")
                print("   buckets: " + " | ".join(f"{BUCKET_NAME[b]} {'—' if v is None else round(v,1)}" for b, v in s["buckets"].items()))
                ds = sorted(s["drivers"], key=lambda d: -d["pull"])
                for d in ds:
                    print(f"   {d['id']:<4} {d['name']:<46} {d['bucket']} {d['type']:<10} value={d['value']:<8} score={d['score']:>3} W={d['w']:<5} pull={d['pull']:+.2f}")
                if s["flags"]: print("   flags: " + "; ".join(s["flags"]))
    log = pd.DataFrame(rows).sort_values(["month", "absolute"])
    log.to_csv(LOG, index=False)
    return log

def table(log):
    last = log[log.month == log.month.max()].sort_values("absolute")
    print(f"\nRANKED TABLE {log.month.max()} (cheapest first)")
    print(last[["index", "absolute", "signal", "relative", "quadrant", "valuation", "sector_cycle", "timing", "filter", "coverage", "core_of_17"]].to_string(index=False))
    print("\nFlags:")
    for _, r in last.iterrows():
        if isinstance(r["flags"], str) and r["flags"]: print(f"  {r['index']}: {r['flags']}")

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    keys = sys.argv[2:]
    log = run(keys, verbose=cmd in ("all", "drivers", "score"))
    if cmd in ("all", "table"): table(log)
