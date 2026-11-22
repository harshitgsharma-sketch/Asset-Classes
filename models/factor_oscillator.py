"""Nifty Factor / Smart-Beta Index Rotation Oscillator (v1, indicative) — "Asset Mgmt" project.

Same engine as nifty_oscillator.py and sector_oscillator.py:
  per-indicator score = clamp(1 + 99*(x - cheap)/(rich - cheap), 1, 100)
  weight W = Impact x Severity x Reliability x Stability; blanks skipped, weights
  re-normalised inside each bucket. High score = expensive / headwind.
Four buckets (Valuation / Factor cycle / Timing / Filter), weights set per factor family.
Two outputs per index: ABSOLUTE (all buckets) and RELATIVE vs Nifty 50 (Rel indicators only).
Plus a ROTATION read: rank of the relative score across the factor indices.

Files (project, under claude/):
  nifty-factors-config.json          per-index set-up: family, bucket set, beta, VIX direction, sector map
  nifty-factors-inputs-monthly.csv   long format, one row per (month, index); raw inputs
  nifty-factors-sector-weights.csv   long format, (month, index, NSE sector, weight) for the look-through
  nifty-sectors-score-log.csv        IMPORTED from the sector model (run sectors first)
  nifty-factors-score-log.csv        output (regenerated)

v1 data notes (see nifty-factors-run-procedure.md):
  - C1 = PB percentile vs own 5-yr history (indexpe.in, measured).
  - C12 = PE percentile ESTIMATED from indexpe.in's valuation-zone label (ZONE_PCT below).
  - C4 import is scaled by the index's beta vs Nifty 50 (NSE Index Dashboard).
  - X1/X2 look-through = sector-model absolute / relative scores weighted by the index's sector mix.
Usage: python3 factor_oscillator.py [score|drivers|table|all] [INDEX_KEY ...]
"""
import json, sys, math
import numpy as np, pandas as pd

CONFIG, INPUTS, WEIGHTS = "nifty-factors-config.json", "nifty-factors-inputs-monthly.csv", "nifty-factors-sector-weights.csv"
SECTOR_LOG, LOG = "nifty-sectors-score-log.csv", "nifty-factors-score-log.csv"

# id: (name, bucket, type, I, S, R, St, cheap, rich, rel)
SPEC = {
 # ---- Valuation
 "C1":  ("PB percentile vs own 5-yr history",           "V", "Leading", 5, 5, 0.875, 0.75, 0, 100, False),
 "C12": ("PE percentile, est. from zone label",         "V", "Leading", 3, 3, 0.625, 0.75, 0, 100, False),
 "C18": ("PE vs own 5-yr median (%)",                   "V", "Leading", 5, 4, 0.875, 0.75, -35, 35, False),
 "C3":  ("Relative PE vs Nifty 50, vs 5-yr norm (%)",   "V", "Leading", 4, 4, 0.875, 1.0, -30, 30, True),
 # ---- Factor cycle
 "X1":  ("Sector look-through: sector-model absolute",  "X", "Leading", 4, 3, 0.75, 0.75, 1, 100, False),
 "X2":  ("Sector look-through: sector-model relative",  "X", "Leading", 4, 3, 0.75, 0.75, 1, 100, True),
 "X3":  ("India VIX regime fit",                        "X", "Coincident", 2, 3, 0.625, 0.75, 11, 25, False),
 # ---- Timing
 "C4":  ("Nifty 50 model Timing bucket x beta",         "T", "Leading", 4, 4, 0.875, 1.0, 1, 100, False),
 "C8":  ("1-yr return minus Nifty 50 (pp)",             "T", "Leading", 3, 4, 0.875, 1.0, -25, 25, True),
 # ---- Filter
 "C14": ("EPS CAGR, 5-yr (%)",                          "F", "Lagging", 3, 3, 0.625, 0.75, 25, -5, False),
 "C16": ("3-yr return minus Nifty 50 (pp/yr)",          "F", "Lagging", 2, 3, 0.75, 1.0, -10, 10, True),
 "C19": ("5-yr re-rating: price CAGR - EPS CAGR (pp)",  "F", "Lagging", 3, 3, 0.75, 1.0, -10, 10, False),
}
FAMILY_BUCKETS = {   # V, X, T, F
 "momentum": {"V": .30, "X": .20, "T": .35, "F": .15},
 "low_vol":  {"V": .40, "X": .20, "T": .25, "F": .15},
 "quality":  {"V": .45, "X": .15, "T": .25, "F": .15},
 "value":    {"V": .40, "X": .20, "T": .25, "F": .15},
 "equal":    {"V": .40, "X": .15, "T": .30, "F": .15},
}
# indexpe.in zone label -> estimated PE percentile (midpoint of the matching band)
ZONE_PCT = {"significantly undervalued": 10, "moderately undervalued": 25, "slightly undervalued": 40,
            "fairly valued": 50, "slightly overvalued": 60, "moderately overvalued": 75,
            "significantly overvalued": 90}
THIN_SHRINK = 0.5   # a bucket resting on one indicator moves only half-way from 50
BUCKET_NAME = {"V": "Valuation", "X": "Factor cycle", "T": "Timing", "F": "Filter"}

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

def sector_scores(month):
    """Sector-model absolute/relative scores for month (latest <= month)."""
    try:
        s = pd.read_csv(SECTOR_LOG, dtype={"month": str})
    except FileNotFoundError:
        return None, None
    s = s[s.month <= month]
    if s.empty: return None, None
    m = s.month.max(); s = s[s.month == m].set_index("index")
    return s, m

def look_through(wts, smap, sec):
    """Weighted sector-model absolute and relative score for one index's sector mix."""
    if wts is None or wts.empty or sec is None: return None, None, 0.0
    a = r = tot = 0.0; unmapped = 0.0
    for _, w in wts.iterrows():
        key = smap.get(w["sector"], smap["_other"])
        if w["sector"] not in smap: unmapped += w["weight"]
        if key not in sec.index: key = smap["_other"]
        ab = num(sec.loc[key, "absolute"]); rl = num(sec.loc[key, "relative"])
        if ab is None: continue
        a += w["weight"]*ab; r += w["weight"]*(rl if rl is not None else 50); tot += w["weight"]
    return (a/tot, r/tot, unmapped) if tot else (None, None, unmapped)

def derive(row, nifty, ci, lt):
    out = {}
    pe, n_pe = num(row.get("pe")), num(nifty.get("pe"))
    out["C1"] = num(row.get("pb_pct"))
    pe_pct = num(row.get("pe_pct"))
    z = row.get("pe_zone")
    if pe_pct is None and isinstance(z, str):
        pe_pct = ZONE_PCT.get(z.strip().lower())
    out["C12"] = pe_pct
    med, n_med = num(row.get("pe_med5")), num(nifty.get("pe_med5"))
    if None not in (pe, med): out["C18"] = (pe/med - 1)*100
    if None not in (pe, n_pe, med, n_med): out["C3"] = ((pe/n_pe)/(med/n_med) - 1)*100
    out["X1"], out["X2"] = lt[0], lt[1]
    vix = num(nifty.get("vix"))
    if vix is not None: out["X3"] = vix
    out["C4"] = num(nifty.get("nifty_timing"))
    r1, n1 = num(row.get("ret1y")), num(nifty.get("ret1y"))
    if None not in (r1, n1): out["C8"] = r1 - n1
    r3, n3 = num(row.get("ret3y")), num(nifty.get("ret3y"))
    if None not in (r3, n3): out["C16"] = r3 - n3
    e5, p5 = num(row.get("eps5")), num(row.get("px5"))
    if e5 is not None: out["C14"] = e5
    if None not in (e5, p5): out["C19"] = p5 - e5
    return {k: v for k, v in out.items() if v is not None}

def weight(k, ci):
    _, b, _, I, S, R, St, *_ = SPEC[k]
    w = I*S*R*St
    if k == "C4": w *= ci.get("beta", 1.0)       # high-beta factors carry more market timing
    return w

def anchors(k, ci):
    ov = ci.get("anchors", {}).get(k)
    if ov: return ov[0], ov[1]
    if k == "X3" and ci.get("vix") == "contra": return SPEC[k][8], SPEC[k][7]
    return SPEC[k][7], SPEC[k][8]

def score_index(ind, ci):
    bw = FAMILY_BUCKETS[ci["buckets"]]
    res, drivers, cov_have, cov_all = {}, [], 0.0, 0.0
    rel_num = rel_den = 0.0
    for b in bw:
        num_ = den = 0.0
        for k in SPEC:
            if SPEC[k][1] != b or k in ci.get("skip", []): continue
            w = weight(k, ci); cov_all += w
            x = ind.get(k)
            if x is None: continue
            c, r = anchors(k, ci); s = ind_score(c, r, x)
            num_ += w*s; den += w; cov_have += w
            drivers.append({"id": k, "name": SPEC[k][0], "bucket": b, "type": SPEC[k][2],
                            "value": round(x, 2), "score": round(s), "w": round(w, 1)})
            if SPEC[k][9]: rel_num += w*s; rel_den += w
        res[b] = num_/den if den else None
        if sum(1 for d in drivers if d["bucket"] == b) == 1:
            res[b] = 50 + (res[b] - 50)*THIN_SHRINK
            for d in drivers:
                if d["bucket"] == b: d["thin"] = True
    have = {b: v for b, v in res.items() if v is not None}
    tot = sum(bw[b] for b in have)
    osc = sum(bw[b]*v for b, v in have.items())/tot if tot else None
    for d in drivers:
        b = d["bucket"]; bden = sum(x["w"] for x in drivers if x["bucket"] == b)
        d["pull"] = round((bw[b]/tot)*(d["w"]/bden)*(d["score"] - 50)*(THIN_SHRINK if d.get("thin") else 1), 2) if tot else 0
    rel = rel_num/rel_den if rel_den else None
    sig = band(osc) if osc is not None else "n/a"
    flags = list(ci.get("flags", []))
    if osc is not None and osc <= 35 and (res.get("F") or 0) >= 70:
        sig = "BUY VETOED - wait (falling knife)"
    if ci["family"] == "momentum" and (ind.get("X3") or 0) >= 22:
        flags.append("momentum-crash watch: India VIX >= 22")
    if ci["family"] == "value" and (ind.get("C19") or 0) >= 5:
        flags.append("re-rating already large: value spread may have closed")
    quad = None
    if osc is not None and rel is not None:
        a = "cheap" if osc <= 35 else "rich" if osc >= 66 else "mid"
        r_ = "cheap" if rel <= 35 else "rich" if rel >= 66 else "mid"
        quad = {("cheap", "cheap"): "Strongest buy: add + overweight",
                ("cheap", "rich"): "Buy market, prefer other factors",
                ("rich", "cheap"): "Trim market; hold this factor",
                ("rich", "rich"): "Strongest sell: trim + underweight"}.get((a, r_),
                "Overweight vs Nifty" if r_ == "cheap" else "Underweight vs Nifty" if r_ == "rich" else "Neutral")
    n_have = sum(1 for k in SPEC if ind.get(k) is not None)
    return {"osc": osc, "rel": rel, "buckets": res, "signal": sig, "coverage": cov_have/cov_all if cov_all else 0,
            "n_ind": f"{n_have}/{len(SPEC)}", "drivers": drivers, "flags": flags, "quadrant": quad}

def run(keys=None, verbose=True):
    cfg = json.load(open(CONFIG))
    smap = cfg["sector_map"]
    idx = {c["key"]: c for c in cfg["indices"]}
    df = pd.read_csv(INPUTS, dtype={"month": str})
    try:
        wdf = pd.read_csv(WEIGHTS, dtype={"month": str})
    except FileNotFoundError:
        wdf = pd.DataFrame(columns=["month", "index", "sector", "weight"])
    rows = []
    for month, g in df.groupby("month"):
        g = g.set_index("index")
        if "NIFTY50" not in g.index: continue
        nifty = g.loc["NIFTY50"].to_dict()
        sec, sec_m = sector_scores(month)
        wm = wdf[wdf.month == month]
        n_lt = look_through(wm[wm["index"] == "NIFTY50"], smap, sec)
        for key, r in g.iterrows():
            if key not in idx or key == "NIFTY50": continue
            ci = idx[key]
            lt = look_through(wm[wm["index"] == key], smap, sec)
            ind = derive(r.to_dict(), nifty, ci, lt)
            s = score_index(ind, ci)
            if s["osc"] is None: continue
            rows.append({"month": month, "index": key, "name": ci["name"], "family": ci["family"],
                         "absolute": round(s["osc"], 1),
                         **{n: (None if s["buckets"].get(b) is None else round(s["buckets"][b], 1))
                            for b, n in (("V", "valuation"), ("X", "factor_cycle"), ("T", "timing"), ("F", "filter"))},
                         "relative": None if s["rel"] is None else round(s["rel"], 1),
                         "signal": s["signal"], "quadrant": s["quadrant"],
                         "coverage": round(s["coverage"], 2), "indicators": s["n_ind"],
                         "lookthrough_abs": None if lt[0] is None else round(lt[0], 1),
                         "lookthrough_rel": None if lt[1] is None else round(lt[1], 1),
                         "sector_log_month": sec_m, "flags": "; ".join(s["flags"]),
                         "pe": r.get("pe"), "source": r.get("source")})
            if verbose and (not keys or key in keys) and month == df.month.max():
                print(f"\n=== {ci['name']} ({key}) {month}: ABS {s['osc']:.1f} {s['signal']} | REL {s['rel'] if s['rel'] is None else round(s['rel'],1)} "
                      f"| {s['quadrant']} | coverage {s['coverage']:.0%}, indicators {s['n_ind']}")
                print("   buckets: " + " | ".join(f"{BUCKET_NAME[b]} {'—' if v is None else round(v,1)}" for b, v in s["buckets"].items()))
                for d in sorted(s["drivers"], key=lambda d: -d["pull"]):
                    print(f"   {d['id']:<4} {d['name']:<44} {d['bucket']} {d['type']:<10} value={d['value']:<8} score={d['score']:>3} W={d['w']:<5} pull={d['pull']:+.2f}")
                if s["flags"]: print("   flags: " + "; ".join(s["flags"]))
        if verbose and month == df.month.max() and n_lt[0] is not None:
            print(f"\nNifty 50 own look-through (reference): abs {n_lt[0]:.1f}, rel {n_lt[1]:.1f} (sector log {sec_m})")
    log = pd.DataFrame(rows).sort_values(["month", "absolute"])
    log.to_csv(LOG, index=False)
    return log

def table(log):
    m = log.month.max()
    last = log[log.month == m].sort_values("absolute")
    print(f"\nRANKED TABLE {m} (cheapest absolute first)")
    print(last[["index", "family", "absolute", "signal", "relative", "quadrant", "valuation", "factor_cycle",
                "timing", "filter", "lookthrough_abs", "lookthrough_rel", "coverage", "indicators"]].to_string(index=False))
    rot = last.dropna(subset=["relative"]).sort_values("relative")
    print(f"\nROTATION {m} (relative vs Nifty 50, lowest = most attractive factor)")
    for i, (_, r) in enumerate(rot.iterrows(), 1):
        print(f"  {i:>2}. {r['index']:<10} rel {r['relative']:>5}  abs {r['absolute']:>5}  {r['family']}")
    fam = last.groupby("family")[["absolute", "relative"]].mean().round(1).sort_values("relative")
    print("\nFAMILY AVERAGES (lowest relative first)")
    print(fam.to_string())
    print("\nFlags:")
    for _, r in last.iterrows():
        if isinstance(r["flags"], str) and r["flags"]: print(f"  {r['index']}: {r['flags']}")

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    log = run(sys.argv[2:], verbose=cmd in ("all", "drivers", "score"))
    if cmd in ("all", "table"): table(log)
