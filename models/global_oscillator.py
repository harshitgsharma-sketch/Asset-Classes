"""Global Indices (Top-20 Economies) Entry/Exit Oscillator — v1.0 (21-Nov-2026) — "Asset Mgmt" project.

Engine family as nifty_oscillator.py / sector_oscillator.py:
  per-indicator score = clamp(1 + 99*(x - cheap)/(rich - cheap), 1, 100)   (high = expensive / headwind)
  weight W = Impact x Severity x Reliability x Stability; blanks skipped, weights re-normalised per bucket;
  a bucket resting on one indicator moves only half-way from 50 (THIN_SHRINK).
Buckets: Valuation (V) / Macro & policy (M) / Currency for an INR investor (X) / Timing (T) / Filter-quality (F).

HEADLINE OUTPUTS (v1.0, user preference: absolute, local currency, Nifty 50 ranked like any market)
  5-YR SCORE     = V 75% + F 15% + M 10%  -> signal band (the entry/exit decision for a <=5-yr hold)
  ENTRY TIMING   = T 60% + M 40%          -> how to enter/exit (lump sum vs tranches), with the staging rule
  EXPECTED RETURN= rough 5-yr return, % p.a. in INR: yield + real growth + half CAPE mean-reversion
                   + India inflation (PPP), minus access cost; +/-3 pp range. Needs CAPE history.
Secondary (logged): ABSOLUTE blend (v0.4 family weights, V/M/T/F), INR blend (incl. X), RELATIVE (G4, F4 vs ACWI).

v1.0 changes: G5 CAPE and G7 dividend yield vs own history, G3 forward PE vs own 10-yr average computed from
global-indices-valuation-history.csv (measured, replaces estimates); earnings-cycle check (CAPE vs trailing PE);
T4 now momentum (under-performance = headwind); staging rule; access/cost layer.

Files (project, under claude/):
  global-indices-config.json            per-index set-up: family, access route, cost, flags, overrides
  global-indices-inputs-monthly.csv     long format, one row per (month, index) + GLOBAL + ACWI rows
  global-indices-valuation-history.csv  raw year-end fwd PE / CAPE / dividend-yield history (norms computed here)
  global-indices-score-log.csv          output (regenerated); global-indices-valuation-log.csv (valuation command)
Usage: python3 global_oscillator.py [all|drivers|table] [inr|blend] [INDEX_KEY ...]   (default ranking = 5-yr score)
       python3 global_oscillator.py valuation
"""
import json, sys, math
from statistics import NormalDist, mean, stdev
import pandas as pd

CONFIG, INPUTS, LOG = "global-indices-config.json", "global-indices-inputs-monthly.csv", "global-indices-score-log.csv"
HIST, VAL_LOG = "global-indices-valuation-history.csv", "global-indices-valuation-log.csv"

# id: (name, bucket, type, I, S, R, St, cheap, rich, rel)
SPEC = {
 # ---- Valuation
 "G1": ("Trailing PE vs own 10-yr history (z)",            "V", "Leading", 5, 5, 1.0, 0.75, -2, 2, False),
 "G2": ("Equity risk premium vs its 10-yr norm (pp)",      "V", "Leading", 5, 4, 0.875, 1.0, 3, -4, False),
 "G3": ("Forward PE vs own 10-yr average (%)",             "V", "Leading", 5, 4, 0.875, 0.75, -25, 25, False),
 "G4": ("Fwd PE / ACWI fwd PE vs 10-yr norm (%)",          "V", "Leading", 4, 4, 0.875, 1.0, -30, 30, True),
 "G5": ("CAPE vs own 10-yr history (z)",                   "V", "Leading", 5, 4, 0.875, 1.0, -2, 2, False),
 "G6": ("P/B, own-history pctl",                           "V", "Leading", 3, 3, 0.75, 0.75, 0, 100, False),
 "G7": ("Dividend yield vs own 10-yr history (z, high=cheap)", "V", "Leading", 3, 3, 0.75, 0.75, 2, -2, False),
 # ---- Macro & policy
 "M1": ("Expected policy-rate change, 6 m (bp)",           "M", "Leading", 5, 4, 0.875, 1.0, -100, 75, False),
 "M2": ("Local 10-yr yield, 6-m change (bp)",              "M", "Coincident", 4, 4, 0.875, 1.0, -75, 75, False),
 "M3": ("Manufacturing PMI",                               "M", "Leading", 2, 3, 0.75, 1.0, 58, 47, False),
 "M4": ("CPI distance from central-bank target (pp)",      "M", "Coincident", 2, 3, 0.75, 1.0, 0, 3, False),
 "M5": ("GDP consensus revision, 3 m (pp)",                "M", "Leading", 3, 3, 0.75, 1.0, 0.5, -0.5, False),
 # ---- Currency (INR investor)
 "X1": ("Currency REER vs 10-yr average (%)",              "X", "Leading", 3, 4, 0.875, 1.0, -10, 10, False),
 "X2": ("Local currency vs INR, 12-m change (%)",          "X", "Coincident", 3, 3, 0.75, 1.0, -10, 15, False),
 "X3": ("Policy-rate gap vs RBI repo (pp)",                "X", "Leading", 2, 3, 0.75, 1.0, 2, -4, False),
 # ---- Timing
 "T1": ("Index / 200-day MA",                              "T", "Leading", 3, 5, 1.0, 1.0, 0.88, 1.15, False),
 "T2": ("Forward EPS revision, ~3 m (%)",                  "T", "Leading", 5, 4, 0.875, 0.75, 4, -4, False),
 "T3": ("Global risk block (HY spread, DXY, Fed, Brent)",  "T", "Leading", 4, 4, 0.875, 1.0, 1, 100, False),
 "T4": ("1-yr USD return minus ACWI (pp, momentum)",       "T", "Leading", 3, 4, 0.875, 1.0, 20, -20, False),
 "T5": ("Monthly RSI(14)",                                 "T", "Leading", 2, 4, 0.75, 1.0, 35, 80, False),
 "T6": ("Foreign equity flows, 3 m (pctl)",                "T", "Coincident", 3, 3, 0.75, 0.75, 0, 100, False),
 # ---- Filter / quality
 "F1": ("Index / 200-week MA",                             "F", "Lagging", 2, 4, 1.0, 1.0, 0.95, 1.60, False),
 "F2": ("EPS growth, TTM or current yr (%)",               "F", "Lagging", 3, 3, 0.75, 0.75, 20, -5, False),
 "F3": ("ROE vs own 10-yr range (pctl)",                   "F", "Lagging", 3, 3, 0.75, 0.75, 100, 0, False),
 "F4": ("3-yr USD CAGR minus ACWI (pp/yr, contrarian)",    "F", "Lagging", 2, 3, 0.75, 1.0, -10, 10, True),
}
T3_PARTS = {"hy_spread": (6.0, 2.5), "dxy": (90, 110), "fed_exp6m": (-100, 75), "brent": (55, 110)}
FAMILY_BUCKETS = {   # v0.4 blend (secondary output)
 "developed": {"V": .40, "M": .20, "X": .10, "T": .20, "F": .10},
 "emerging":  {"V": .35, "M": .20, "X": .20, "T": .15, "F": .10},
}
FIVE_YR = {"V": .75, "F": .15, "M": .10}
TIMING = {"T": .60, "M": .40}
THIN_SHRINK = 0.5
CYCLE_GAP = 1.0          # |CAPE z - trailing PE z| >= this -> earnings off-trend: halve G1 and G3 weights
REAL_GROWTH = {"developed": 1.5, "emerging": 2.5}   # long-run real EPS growth, % p.a. (judgment)
INDIA_INFL = 4.0         # RBI target; PPP converts local real return into INR nominal
DESIGN_N = 26
BUCKET_NAME = {"V": "Valuation", "M": "Macro", "X": "Currency", "T": "Timing", "F": "Filter"}

def band(x):
    return ("STRONG BUY" if x <= 20 else "BUY" if x <= 35 else "ACCUMULATE" if x <= 50
            else "HOLD" if x <= 65 else "TRIM" if x <= 80 else "EXIT")

def ind_score(c, r, x):
    return max(1.0, min(100.0, 1 + 99*(x - c)/(r - c)))

def num(v):
    try:
        f = float(v); return None if math.isnan(f) else f
    except (TypeError, ValueError):
        return None

def r1(x): return None if x is None else round(x, 1)

def global_block(g):
    parts = [ind_score(c, r, num(g.get(k))) for k, (c, r) in T3_PARTS.items() if num(g.get(k)) is not None]
    return sum(parts)/len(parts) if parts else None

def load_history():
    """{index: {metric: (current, mean, sd, n)}} from year-end history (current = most recent row)."""
    try:
        h = pd.read_csv(HIST)
    except FileNotFoundError:
        return {}
    out = {}
    for (k, m), g in h.groupby(["index", "metric"], sort=False):
        vals = [num(v) for v in g["value"]]
        cur, hist = vals[0], [v for v in vals[1:] if v is not None]
        if cur is None or len(hist) < 5: continue
        out.setdefault(k, {})[m] = (cur, mean(hist), stdev(hist), len(hist))
    return out

def derive(row, acwi, g, ci=None, hist=None):
    o = {}; ci = ci or {}; hk = (hist or {}).get(row.get("index"), {})
    z, pct = num(row.get("pe_z10")), num(row.get("pe_pct"))
    if z is None and pct is not None:
        z = NormalDist().inv_cdf(min(max(pct, 0.5), 99.5)/100)
    if z is not None: o["G1"] = z
    fpe, y10, erpn = num(row.get("fpe")), num(row.get("y10")), num(row.get("erp_avg10"))
    if None not in (fpe, y10, erpn): o["G2"] = (100/fpe - y10) - erpn
    if "fpe" in hk:                                   # measured history wins over CSV estimates
        cur, mu, _, _ = hk["fpe"]; o["G3"] = (cur/mu - 1)*100
    else:
        favg = num(row.get("fpe_avg10"))
        if None not in (fpe, favg): o["G3"] = (fpe/favg - 1)*100
    a_fpe, reln = num(acwi.get("fpe")), num(row.get("rel_avg10"))
    if None not in (fpe, a_fpe, reln): o["G4"] = ((fpe/a_fpe)/reln - 1)*100
    if "cape" in hk:
        cur, mu, sd, _ = hk["cape"]; o["G5"] = (cur - mu)/sd if sd else 0
    if "dy" in hk:
        cur, mu, sd, _ = hk["dy"]; o["G7"] = (cur - mu)/sd if sd else 0
    for k, col in (("G6", "pb_pct"), ("M1", "policy_exp6m"), ("M2", "y10_chg6m"), ("M3", "pmi"),
                   ("M5", "gdp_rev3m"), ("X1", "reer_dev"), ("X2", "fx_inr_12m"), ("T1", "dma200"),
                   ("T2", "eps_rev3m"), ("T5", "rsi_m"), ("T6", "flows_pct"), ("F1", "wma200"),
                   ("F2", "eps_g"), ("F3", "roe_pct")):
        v = num(row.get(col))
        if v is not None: o[k] = v
    cpi, tgt = num(row.get("cpi")), num(row.get("cpi_target"))
    if None not in (cpi, tgt): o["M4"] = abs(cpi - tgt)
    pr, repo = num(row.get("policy_rate")), num(g.get("repo_india"))
    if None not in (pr, repo): o["X3"] = pr - repo
    icpi = num(g.get("india_cpi"))
    if ci.get("high_inflation") and None not in (cpi, icpi):   # judge currency in real terms
        if "X2" in o: o["X2"] = ((1 + o["X2"]/100)*(1 + cpi/100)/(1 + icpi/100) - 1)*100
        if None not in (pr, repo): o["X3"] = (pr - cpi) - (repo - icpi)
    o["T3"] = global_block(g)
    ra, aa = num(row.get("ret1y")), num(acwi.get("ret1y"))
    if None not in (ra, aa) and row.get("index") != "ACWI": o["T4"] = ra - aa
    rb, ab = num(row.get("ret3y")), num(acwi.get("ret3y"))
    if None not in (rb, ab) and row.get("index") != "ACWI": o["F4"] = rb - ab
    return {k: v for k, v in o.items() if v is not None}

def cycle_check(ind):
    """Earnings-cycle check (#5): CAPE smooths 10 yrs of earnings; trailing PE uses the latest year."""
    if "G1" in ind and "G5" in ind:
        gap = ind["G5"] - ind["G1"]
        if gap >= CYCLE_GAP:
            return gap, f"earnings above trend (CAPE z {ind['G5']:+.1f} vs PE z {ind['G1']:+.1f}): trailing/forward PE flatter; G1, G3 weights halved"
        if gap <= -CYCLE_GAP:
            return gap, f"earnings below trend (CAPE z {ind['G5']:+.1f} vs PE z {ind['G1']:+.1f}): trailing/forward PE overstate richness; G1, G3 weights halved"
    return None, None

def weight(k, ci, ind=None):
    _, b, _, I, S, R, St, *_ = SPEC[k]
    w = I*S*R*St
    m = ci.get("weight_mult", {}).get(k)
    if m: w *= m
    if ind is not None and k in ("G1", "G3") and cycle_check(ind)[0] is not None: w *= 0.5
    return w

def anchors(k, ci):
    ov = ci.get("anchors", {}).get(k)
    return (ov[0], ov[1]) if ov else (SPEC[k][7], SPEC[k][8])

def combine(res, bw):
    have = {b: v for b, v in res.items() if v is not None and b in bw}
    tot = sum(bw[b] for b in have)
    return (sum(bw[b]*v for b, v in have.items())/tot if tot else None), tot

def expected_return(row, ci, hk):
    """Rough 5-yr expected return, % p.a. in INR (#4). None without CAPE history."""
    if ci.get("high_inflation"): return None                  # nominal-inflation CAPE not meaningful
    note = ""
    if "cape" in hk:
        cape, mu, _, _ = hk["cape"]
        rev = ((mu/cape)**(0.5/5) - 1)*100                      # half the CAPE gap closes over 5 yrs
    elif num(row.get("cape_now")) is not None:
        cape, rev, note = num(row["cape_now"]), 0.0, " (no CAPE history: reversion term = 0)"
    else:
        return None
    dy = hk["dy"][0] if "dy" in hk else num(row.get("dy_now"))
    y = dy if dy is not None else 0.5*100/cape                  # payout ~50% of CAPE earnings if no DY
    g = ci.get("real_growth", REAL_GROWTH[ci["family"]])
    real = y + g + rev
    return {"exp_real_local": round(real, 1), "exp_inr": round(real + INDIA_INFL, 1),
            "exp_inr_net": round(real + INDIA_INFL - (ci.get("cost_pct") or 0), 1),
            "exp_parts": f"yield {y:.1f} + real growth {g:.1f} + CAPE reversion {rev:+.1f} + India inflation {INDIA_INFL:.1f} - cost {ci.get('cost_pct') or 0:.1f}{note}"}

def entry_plan(sig5, timing, dma, investable=True):
    """Staging rule (#8)."""
    if not investable: return "Not investable for Indian investors (watch only)"
    deep = dma is not None and dma < 0.85
    if sig5 in ("STRONG BUY", "BUY", "ACCUMULATE"):
        if deep:
            plan = "Enter in thirds over 6-12 m (price >15% below 200-DMA); speed up once it recrosses the 200-DMA"
        elif timing is None or timing <= 45:
            plan = "Enter now (lump sum acceptable)"
        elif timing <= 60:
            plan = "Enter in 3 tranches over ~6 m"
        else:
            plan = "Enter slowly: 6 monthly tranches (timing headwinds)"
    elif sig5 == "HOLD":
        plan = "Hold; no new lump sum (SIPs may continue)"
    else:
        plan = "Trim now" if (timing or 0) >= 60 else "Trim into rallies (timing not yet against it)"
    return plan

def score_index(ind, ci):
    bw_all = FAMILY_BUCKETS[ci["family"]]
    res, drivers, cov_have, cov_all = {}, [], 0.0, 0.0
    rel_n = rel_d = 0.0
    for b in bw_all:
        n_ = d_ = 0.0; cnt = 0
        for k in SPEC:
            if SPEC[k][1] != b or k in ci.get("skip", []): continue
            w = weight(k, ci, ind); cov_all += weight(k, ci)
            x = ind.get(k)
            if x is None: continue
            c, r = anchors(k, ci); s = ind_score(c, r, x)
            n_ += w*s; d_ += w; cov_have += weight(k, ci); cnt += 1
            drivers.append({"id": k, "name": SPEC[k][0], "bucket": b, "type": SPEC[k][2],
                            "value": round(x, 2), "score": round(s), "w": round(w, 1)})
            if SPEC[k][9]: rel_n += w*s; rel_d += w
        res[b] = n_/d_ if d_ else None
        if cnt == 1:
            res[b] = 50 + (res[b] - 50)*THIN_SHRINK
            for dd in drivers:
                if dd["bucket"] == b: dd["thin"] = True
    five, tot5 = combine(res, FIVE_YR)
    timing, _ = combine(res, TIMING)
    blend, _ = combine(res, {b: v for b, v in bw_all.items() if b != "X"})
    inr, _ = combine(res, bw_all)
    for dd in drivers:     # pull on the 5-yr score (T/X drivers pull on timing/INR only -> 0 here)
        b = dd["bucket"]; bden = sum(x["w"] for x in drivers if x["bucket"] == b)
        share = FIVE_YR.get(b, 0)/tot5 if tot5 else 0
        dd["pull"] = round(share*(dd["w"]/bden)*(dd["score"] - 50)*(THIN_SHRINK if dd.get("thin") else 1), 2)
    rel = rel_n/rel_d if rel_d else None
    sig5 = band(five) if five is not None else "n/a"
    flags = list(ci.get("flags", []))
    gap, msg = cycle_check(ind)
    if msg: flags.insert(0, msg)
    if five is not None and five <= 35 and ((res.get("F") or 0) >= 70 or (ind.get("T2") is not None and ind["T2"] <= -3)):
        sig5 = "BUY VETOED - wait (falling knife)"
    lim = 1.20 if ci["family"] == "emerging" else 1.15
    if five is not None and five >= 66 and (ind.get("T1") or 0) >= lim:
        sig5 = "TRIM (euphoria veto)"
    core = sum(1 for k in SPEC if ind.get(k) is not None)
    return {"five": five, "timing": timing, "blend": blend, "inr": inr, "rel": rel, "buckets": res,
            "signal": sig5, "plan": entry_plan(sig5, timing, ind.get("T1"), ci.get("access") != "Not investable"),
            "coverage": cov_have/cov_all if cov_all else 0, "core": f"{core}/{DESIGN_N}",
            "n_val": sum(1 for d in drivers if d["bucket"] == "V"), "cycle_gap": None if gap is None else round(gap, 2),
            "drivers": drivers, "flags": flags}

def run(keys=None, verbose=True):
    cfg = json.load(open(CONFIG))
    df = pd.read_csv(INPUTS, dtype={"month": str})
    idx = {c["key"]: c for c in cfg["indices"]}
    hist = load_history()
    rows = []
    for month, gdf in df.groupby("month"):
        gdf = gdf.set_index("index", drop=False)
        if "GLOBAL" not in gdf.index or "ACWI" not in gdf.index: continue
        g = gdf.loc["GLOBAL"].to_dict(); acwi = gdf.loc["ACWI"].to_dict()
        latest = month == df.month.max()
        for key, r in gdf.iterrows():
            if key not in idx or idx[key].get("valuation_only"): continue
            ci = idx[key]; rd = r.to_dict()
            ind = derive(rd, acwi, g, ci, hist if latest else None)
            s = score_index(ind, ci)
            if s["five"] is None: continue
            er = expected_return(rd, ci, hist.get(key, {}) if latest else {}) or {}
            rows.append({"month": month, "index": key, "name": ci["name"], "economy": ci.get("economy"), "family": ci["family"],
                         "five_yr": r1(s["five"]), "signal": s["signal"], "entry_timing": r1(s["timing"]), "entry_plan": s["plan"],
                         "exp_inr_net": er.get("exp_inr_net"), "exp_inr_range": None if not er else f"{er['exp_inr_net']-3:.0f} to {er['exp_inr_net']+3:.0f}",
                         "access": ci.get("access"), "cost_pct": ci.get("cost_pct"),
                         **{BUCKET_NAME[b].lower(): r1(v) for b, v in s["buckets"].items()},
                         "blend_abs_v04": r1(s["blend"]), "inr_blend": r1(s["inr"]), "relative": r1(s["rel"]),
                         "val_indicators": s["n_val"], "cycle_gap": s["cycle_gap"],
                         "coverage": round(s["coverage"], 2), "core_of_26": s["core"],
                         "exp_parts": er.get("exp_parts"), "flags": "; ".join(s["flags"]), "source": rd.get("source")})
            if verbose and (not keys or key in keys) and latest:
                print(f"\n=== {ci['name']} ({key}) {month}: 5-YR {s['five']:.1f} {s['signal']} | TIMING {r1(s['timing'])} -> {s['plan']} | "
                      f"exp. {er.get('exp_inr_net','n/a')}% p.a. INR net | design {s['core']}")
                print("   buckets: " + " | ".join(f"{BUCKET_NAME[b]} {'—' if v is None else round(v,1)}" for b, v in s["buckets"].items()))
                for d in sorted(s["drivers"], key=lambda d: (d["bucket"] not in FIVE_YR, -abs(d["pull"]))):
                    print(f"   {d['id']:<3} {d['name']:<52} {d['bucket']} {d['type']:<10} value={d['value']:<8} score={d['score']:>3} W={d['w']:<5} pull5y={d['pull']:+.2f}{' (thin)' if d.get('thin') else ''}")
                if er: print("   expected return: " + er["exp_parts"])
                if s["flags"]: print("   flags: " + "; ".join(s["flags"]))
        if verbose and latest:
            print(f"\nGlobal risk block T3 {month}: {global_block(g):.1f}")
    log = pd.DataFrame(rows).sort_values(["month", "five_yr"])
    log.to_csv(LOG, index=False)
    return log

def table(log, by="five_yr"):
    last = log[log.month == log.month.max()].sort_values(by)
    print(f"\nRANKED TABLE {log.month.max()} (cheapest first, by {by}; local currency)")
    cols = ["index", "five_yr", "signal", "entry_timing", "exp_inr_net", "valuation", "val_indicators", "cycle_gap", "access", "core_of_26"]
    if by != "five_yr": cols = ["index", by] + [c for c in cols if c not in ("index", by)]
    print(last[cols].to_string(index=False))
    print("\nEntry plans:")
    for _, r in last.iterrows(): print(f"  {r['index']:<8} {r['entry_plan']}")
    print("\nFlags:")
    for _, r in last.iterrows():
        if isinstance(r["flags"], str) and r["flags"]: print(f"  {r['index']}: {r['flags']}")

def val_band(x):
    return ("Very cheap" if x <= 20 else "Cheap" if x <= 35 else "Fair, cheap side" if x <= 50
            else "Fair, rich side" if x <= 65 else "Expensive" if x <= 80 else "Very expensive")

def valuation():
    """Valuation-only ranking. Uniform score = G1 (trailing PE vs own 10-yr history); the full Valuation
    bucket (all available of G1-G7, cycle-adjusted) is shown alongside."""
    cfg = json.load(open(CONFIG))
    df = pd.read_csv(INPUTS, dtype={"month": str}); hist = load_history()
    month = df.month.max(); gdf = df[df.month == month].set_index("index", drop=False)
    g = gdf.loc["GLOBAL"].to_dict(); acwi = gdf.loc["ACWI"].to_dict()
    rows = []
    for ci in cfg["indices"]:
        k = ci["key"]
        if k not in gdf.index: continue
        r = gdf.loc[k].to_dict(); ind = derive(r, acwi, g, ci, hist)
        if "G1" not in ind: continue
        c, rr = anchors("G1", ci); g1 = ind_score(c, rr, ind["G1"])
        s = score_index(ind, ci)
        rows.append({"month": month, "index": k, "name": ci["name"], "economy": ci.get("economy", ""),
                     "pe": num(r.get("pe")), "pe_z5": num(r.get("pe_z5")), "pe_z10": round(ind["G1"], 2),
                     "pe_z20": num(r.get("pe_z20")), "cape_z": r1(ind.get("G5")), "fpe_vs_avg_pct": r1(ind.get("G3")),
                     "dy_z": r1(ind.get("G7")), "valuation_score": round(g1, 1), "valuation_read": val_band(g1),
                     "full_valuation_bucket": r1(s["buckets"].get("V")), "val_indicators": s["n_val"],
                     "vs_200dma_pct": None if num(r.get("dma200")) is None else round((num(r["dma200"]) - 1)*100, 1),
                     "flags": "; ".join(s["flags"]), "source": r.get("source")})
    out = pd.DataFrame(rows).sort_values("full_valuation_bucket").reset_index(drop=True)
    out.insert(1, "rank", range(1, len(out) + 1))
    out.to_csv(VAL_LOG, index=False)
    print(f"\nVALUATION RANKING {month} (by full valuation bucket; 1 = cheapest vs own history)")
    print(out[["rank", "index", "economy", "pe_z10", "cape_z", "fpe_vs_avg_pct", "dy_z", "valuation_score",
               "full_valuation_bucket", "val_indicators"]].to_string(index=False))
    return out

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    if cmd == "valuation":
        valuation(); sys.exit()
    args = sys.argv[2:]
    by = "inr_blend" if "inr" in args else "blend_abs_v04" if "blend" in args else "five_yr"
    args = [a for a in args if a not in ("inr", "blend")]
    log = run(args, verbose=cmd in ("all", "drivers"))
    if cmd in ("all", "table"): table(log, by)
