"""Credit & Fixed-Income Entry/Exit Oscillator (INR investor) — v1, indicative — "Asset Mgmt" project.

Answers "when should I lock in rates, and at what duration?" for G-secs (10-yr, 5-yr), AAA corporate
bonds, AA credit, 1-yr money-market debt, 5-yr bank FDs and RBI Floating Rate Savings Bonds.
Same engine family as the gold / Nifty / sector / global / asset-class models:
  per-indicator score = clamp(1 + 99*(x - cheap)/(rich - cheap), 1, 100)   (high = rich / headwind)
  W = Impact x Severity x Reliability x Stability; blank inputs skipped, weights re-normalised per bucket;
  Oscillator = Valuation / Timing / Filter mix set by the instrument's profile (config bucket_weights).
  1 = yields high vs history and likely to fall (lock in, add duration); 100 = yields low or rising (stay short).
For the floating-rate bond (invert_timing) the Timing and Filter scores are flipped (101 - s):
rising rates are a tailwind for a floater.

Files (project, under claude/):
  fixed-income-config.json          instruments, indicators, anchors, weights, horizon shocks, 5-yr lock-in paths
  fixed-income-inputs-monthly.csv   one row per month of raw inputs (wide format)
  fixed-income-score-log.csv        output (regenerated on every run)
Usage: python3 fixed_income_oscillator.py [all|table|drivers|call|ladder|lockin|chart] [INSTRUMENT_KEY ...]
"""
import json, sys, math
import pandas as pd

CONFIG, INPUTS, LOG = "fixed-income-config.json", "fixed-income-inputs-monthly.csv", "fixed-income-score-log.csv"
CHART = "fixed-income-oscillator.png"

def num(v):
    try:
        f = float(v); return None if math.isnan(f) else f
    except (TypeError, ValueError):
        return None

def _f(*cols):
    def wrap(fn):
        def inner(r):
            vals = [num(r.get(c)) for c in cols]
            return None if None in vals else fn(*vals)
        return inner
    return wrap

DERIVE = {
    # shared rate-cycle timing
    "repo_chg_6m":   _f("repo_chg_6m")(lambda v: v),
    "real_repo":     _f("repo", "cpi_exp1y")(lambda r, c: r - c),
    "cpi_turn":      _f("cpi_exp1y", "cpi_yoy")(lambda e, c: e - c),
    "gsec10_6m_chg": _f("gsec10", "gsec10_6m_ago")(lambda a, b: (a - b)*100),
    "cpi_yoy":       _f("cpi_yoy")(lambda v: v),
    "liquidity":     _f("liquidity")(lambda v: v),
    "brent":         _f("brent")(lambda v: v),
    "fpi_debt_3m":   _f("fpi_debt_3m")(lambda v: v),
    "us10y":         _f("us10y")(lambda v: v),
    "hy_oas":        _f("hy_oas")(lambda v: v),
    "credit_dep_gap": _f("credit_growth", "deposit_growth")(lambda c, d: c - d),
    "fiscal_def":    _f("fiscal_def")(lambda v: v),
    # valuation (B1-B7 identical to asset_class_oscillator.py)
    "gsec_real":     _f("gsec10", "cpi_exp1y")(lambda y, c: y - c),
    "term_spread":   _f("gsec10", "repo")(lambda y, r: y - r),
    "gsec10":        _f("gsec10")(lambda v: v),
    "in_us_spread":  _f("gsec10", "us10y")(lambda a, b: a - b),
    "gsec5_real":    _f("gsec5", "cpi_exp1y")(lambda y, c: y - c),
    "gsec5_minus_repo": _f("gsec5", "repo")(lambda y, r: y - r),
    "gsec5":         _f("gsec5")(lambda v: v),
    "aaa5_real":     _f("aaa5y", "cpi_exp1y")(lambda y, c: y - c),
    "aaa5_spread":   _f("aaa5y", "gsec5")(lambda a, g: (a - g)*100),
    "aa3_real":      _f("aa3y", "cpi_exp1y")(lambda y, c: y - c),
    "aa3_spread":    _f("aa3y", "gsec3")(lambda a, g: (a - g)*100),
    "aaa1_minus_repo_exp": _f("aaa1y", "repo_exp1y")(lambda a, r: a - r),
    "aaa1_real":     _f("aaa1y", "cpi_exp1y")(lambda y, c: y - c),
    "fd5_real":      _f("fd5y", "cpi_exp1y")(lambda y, c: y - c),
    "fd5y":          _f("fd5y")(lambda v: v),
    "fd5_minus_gsec5": _f("fd5y", "gsec5")(lambda f, g: (f - g)*100),
    "frsb_real":     _f("frsb", "cpi_exp1y")(lambda y, c: y - c),
    "frsb_minus_gsec5": _f("frsb", "gsec5")(lambda f, g: f - g),
}

def ind_score(c, r, x):
    return max(1.0, min(100.0, 1 + 99*(x - c)/(r - c)))

def band(x):
    return ("STRONG BUY" if x <= 20 else "BUY" if x <= 35 else "ACCUMULATE" if x <= 50
            else "HOLD" if x <= 65 else "TRIM" if x <= 80 else "EXIT")

ACTION = {
    "duration": ["Lock in now (add duration)", "Lock in now (add duration)", "Accumulate in tranches",
                 "Hold; new money stays short", "Trim duration", "Exit to short / floating"],
    "credit":   ["Add credit", "Add credit", "Accumulate selectively", "Hold; no new credit",
                 "Trim credit", "Exit credit"],
    "short":    ["Park new money here", "Park new money here", "Use for cash needs", "Neutral",
                 "Yield thin; prefer FD / longer", "Yield thin; prefer FD / longer"],
    "floating": ["Buy floating", "Buy floating", "Accumulate floating", "Hold",
                 "Prefer fixed instead", "Prefer fixed instead"],
}
def action(profile, x):
    i = 0 if x <= 20 else 1 if x <= 35 else 2 if x <= 50 else 3 if x <= 65 else 4 if x <= 80 else 5
    return ACTION[profile][i]

def score_list(inds, row, bucket, invert=False):
    out, n_, d_, w_all = [], 0.0, 0.0, 0.0
    for ind in inds:
        w = ind["I"]*ind["S"]*ind["R"]*ind["St"]; w_all += w
        x = DERIVE[ind["derive"]](row)
        if x is None: continue
        s = ind_score(ind["cheap"], ind["rich"], x)
        if invert: s = 101 - s
        n_ += w*s; d_ += w
        out.append({"id": ind["id"], "name": ind["name"], "type": ind["type"], "bucket": bucket, "value": round(x, 2),
                    "unit": ind.get("unit", ""), "score": round(s, 1), "w": round(w, 2)})
    return out, n_, d_, w_all

def score_inst(inst, row, cfg):
    inv = inst.get("invert_timing", False)
    buckets, drivers, w_live, w_total = {}, [], 0.0, 0.0
    groups = {"Valuation": (inst["valuation"], False),
              "Timing": ([i for g in inst["timing"] for i in cfg["shared"][g]], inv),
              "Filter": ([i for g in inst["filter"] for i in cfg["shared"][g]], inv)}
    for b, (inds, flip) in groups.items():
        d, n_, d_, wa = score_list(inds, row, b, flip)
        w_live += d_; w_total += wa
        if d_:
            buckets[b] = {"score": n_/d_, "wsum": d_}
            drivers += d
    if "Valuation" not in buckets: return None
    bw = cfg["bucket_weights"][inst["profile"]]
    tot = sum(bw[b] for b in buckets)
    osc = sum(bw[b]*buckets[b]["score"] for b in buckets)/tot
    for dd in drivers:
        b = dd["bucket"]
        dd["pull"] = round(bw[b]/tot * dd["w"]/buckets[b]["wsum"] * (dd["score"] - 50), 2)
    veto = None
    t = buckets.get("Timing", {}).get("score")
    if osc <= 35 and t is not None and t >= 70:
        veto = "Lock-in vetoed: rate cycle still against you (Timing >=70); stagger in thirds"
    return {"osc": osc, "V": buckets["Valuation"]["score"], "T": t,
            "F": buckets.get("Filter", {}).get("score"), "drivers": drivers,
            "coverage": w_live/w_total, "live": f"{len(drivers)}", "veto": veto}

def run(keys=None, verbose=True):
    cfg = json.load(open(CONFIG))
    df = pd.read_csv(INPUTS, dtype={"month": str})
    rows, latest = [], {}
    for _, r in df.iterrows():
        row = r.to_dict(); month = row["month"]
        for inst in cfg["instruments"]:
            s = score_inst(inst, row, cfg)
            if s is None: continue
            y = num(row.get(inst["yield_col"]))
            rec = {"month": month, "instrument": inst["key"], "name": inst["name"], "family": inst["family"],
                   "oscillator": round(s["osc"], 1), "signal": band(s["osc"]), "action": action(inst["profile"], s["osc"]),
                   "valuation": round(s["V"], 1), "timing": None if s["T"] is None else round(s["T"], 1),
                   "filter": None if s["F"] is None else round(s["F"], 1), "yield_pct": y,
                   "veto": s["veto"] or "", "coverage": round(s["coverage"], 2), "indicators_live": s["live"],
                   "drivers": "; ".join(f"{d['id']} {d['value']} {d['unit']}->{d['score']:.0f}" for d in s["drivers"]),
                   "access": inst["access"], "tax": inst["tax"]}
            rows.append(rec)
            if month == df.month.max():
                latest[inst["key"]] = (inst, s, rec)
                if verbose and (not keys or inst["key"] in keys):
                    print(f"\n=== {inst['name']} ({inst['key']}) {month}: OSC {s['osc']:.1f} -> {band(s['osc'])} | "
                          f"{rec['action']} | V {s['V']:.1f} / T {s['T']:.1f} / F {s['F']:.1f} | yield {y}% | coverage {s['coverage']:.0%}"
                          + (" | inverted timing (floater)" if inst.get("invert_timing") else "")
                          + (f"\n    VETO: {s['veto']}" if s["veto"] else ""))
                    for d in sorted(s["drivers"], key=lambda d: -d["pull"]):
                        print(f"   {d['id']:<3} {d['bucket'][0]} {d['name']:<62} {d['type']:<10} value={d['value']:<8} {d['unit']:<5} score={d['score']:>5} W={d['w']:<5} pull={d['pull']:+.2f}")
    log = pd.DataFrame(rows).sort_values(["month", "oscillator"]).reset_index(drop=True)
    log.insert(2, "rank", log.groupby("month").cumcount() + 1)
    log.to_csv(LOG, index=False)
    return log, latest, cfg, df[df.month == df.month.max()].iloc[0].to_dict()

def table(log):
    last = log[log.month == log.month.max()]
    print(f"\nFIXED-INCOME OSCILLATOR {log.month.max()} (1 = lock in / add, 100 = stay short)")
    print(last[["rank", "instrument", "oscillator", "signal", "action", "valuation", "timing", "filter", "yield_pct", "veto"]].to_string(index=False))

def rate_cycle(cfg, row):
    d, n_, d_, _ = score_list(cfg["shared"]["rate_cycle_timing"], row, "Timing")
    return n_/d_ if d_ else None

def call(latest, cfg, row):
    rc = rate_cycle(cfg, row)
    o = {k: latest[k][1]["osc"] for k in latest}
    print(f"\nDURATION CALL {row['month']}")
    print(f"  Rate-cycle Timing score (shared, 1 = easing ahead, 100 = tightening ahead): {rc:.1f} -> "
          + ("tightening / rates still rising" if rc >= 66 else "late tightening / pause" if rc > 50 else
             "pause, easing ahead" if rc > 35 else "easing cycle"))
    s, m, l = o.get("SHORT_1Y"), o.get("GSEC_5Y"), o.get("GSEC_10Y")
    print(f"  Short 1-yr {s:.1f} | Medium 5-yr {m:.1f} | Long 10-yr {l:.1f} | FRSB {o.get('FRSB', float('nan')):.1f} | 5-yr FD {o.get('BANK_FD_5Y', float('nan')):.1f}")
    if l <= 35 and rc < 66:   verdict = "LOCK IN LONG: buy 7-10+ yr duration now"
    elif l <= 35:             verdict = "LONG IS CHEAP BUT RATES STILL RISING: start long duration in thirds"
    elif m <= 40:             verdict = "LOCK IN MEDIUM: 3-5 yr ladder / target-maturity now; add long later"
    elif min(o.values()) == s or (s <= 35):
                              verdict = "STAY SHORT: park in 1-yr / money market, keep FRSB for floating; extend when the trigger below fires"
    elif l >= 66:             verdict = "SHORTEN: rates low vs history, move to short / floating"
    else:                     verdict = "NEUTRAL: ladder 1-5 yr, no strong duration bet"
    print(f"  VERDICT: {verdict}")
    best = min(o, key=o.get)
    print(f"  Cheapest sleeve: {best} {o[best]:.1f}")
    print("  Extend-duration triggers: rate-cycle Timing <=50 (RBI pause priced / expected repo change <=0), "
          "or 10-yr G-sec oscillator <=35, or CPI turn <= -0.75 pp with liquidity in surplus.")
    return rc, verdict

def ladder(latest, cfg, row):
    cash = num(row.get("tbill91"))
    shocks = cfg["horizon_shocks_bp"]
    print(f"\nRATE LADDER & 12-M HORIZON RETURNS {row['month']} (vs 91-d T-bill {cash}%; return ~ yield - mod.dur x shock; FD/FRSB not marked to market)")
    hdr = f"  {'instrument':<13}{'yield%':>7}{'mod.dur':>8}{'carry bp':>9}{'b/e rise bp':>12}  " + "".join(f"{s:+d}bp".rjust(8) for s in shocks)
    print(hdr)
    out = []
    for k, (inst, s, rec) in latest.items():
        y, D = rec["yield_pct"], inst["mod_dur"]
        if y is None: continue
        carry = (y - cash)*100
        be = carry/D if D > 0 else float("inf")
        rets = [y - D*sh/100 for sh in shocks]
        out.append((k, y, D, carry, be, rets))
        print(f"  {k:<13}{y:>7.2f}{D:>8.1f}{carry:>9.0f}{('n/a' if be == float('inf') else f'{be:.0f}'):>12}  " + "".join(f"{r:>8.2f}" for r in rets))
    for extra, col in (("FD_1Y (SBI)", "fd1y"), ("SFB_FD_5Y*", "sfb5y")):
        v = num(row.get(col))
        if v is not None:
            print(f"  {extra:<13}{v:>7.2f}{0.0:>8.1f}{(v-cash)*100:>9.0f}{'n/a':>12}  " + "".join(f"{v:>8.2f}" for _ in shocks))
    print("  * small-finance-bank 'up to' rate; credit risk above the Rs 5 lakh DICGC cover. Pre-tax; all of these are taxed at slab.")
    return out

def lockin(latest, cfg, row):
    sc = cfg["lockin_scenarios"]; loss = sc["credit_loss"]
    s1 = num(row.get("aaa1y")); g10 = num(row.get("gsec10"))
    fixed = {"Lock 5-yr G-sec": num(row.get("gsec5")),
             "Lock 5-yr AAA (net of loss)": num(row.get("aaa5y")) - loss["CORP_AAA_5Y"],
             "Lock 5-yr bank FD": 100*((1 + num(row.get("fd5y"))/400)**4 - 1)}
    print(f"\n5-YR LOCK-IN vs ROLL vs FLOAT {row['month']} (annualised, pre-tax, coupons not reinvested; judgment paths)")
    res = {}
    for name, p in sc["paths"].items():
        path = [s1] + p["short1y"][1:]
        r = dict(fixed)
        r["Roll 1-yr AAA/CD"] = sum(path)/len(path)
        r["FRSB (NSC + 0.35)"] = sum(n + 0.35 for n in p["nsc"])/len(p["nsc"])
        r["10-yr G-sec, sell at yr 5"] = g10 - 4.2*(p["gsec5_end"] - g10)/5
        res[name] = r
    strategies = list(next(iter(res.values())).keys())
    names = list(res)
    print(f"  {'strategy':<30}" + "".join(n.split(' (')[0].rjust(9) for n in names) + "  p-wtd")
    pw = {}
    for st in strategies:
        w = sum(sc["paths"][n]["p"]*res[n][st] for n in names); pw[st] = w
        print(f"  {st:<30}" + "".join(f"{res[n][st]:>9.2f}" for n in names) + f"{w:>7.2f}")
    print("  Probabilities: " + ", ".join(f"{n} {sc['paths'][n]['p']:.0%}" for n in names))
    best = max(pw, key=pw.get)
    print(f"  Best probability-weighted: {best} {pw[best]:.2f}% | worst-case (Bear) best: {max(res[names[0]], key=res[names[0]].get)}")
    print("  Note: FRSB has a 7-yr lock-in (early exit only for investors aged 60+), longer than the 5-yr horizon; "
          "10-yr G-sec sold at yr 5 carries price risk; AAA assumes 0.10 pp/yr loss. Pre-tax: all are slab-taxed.")
    return res, pw

def chart(log, latest, row):
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    last = log[log.month == log.month.max()].sort_values("oscillator", ascending=False)
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 4.8), facecolor="#fcfcfb", gridspec_kw={"width_ratios": [1.25, 1]})
    for a in (a1, a2):
        a.set_facecolor("#fcfcfb"); a.tick_params(labelsize=8.5, colors="#55544f", length=0)
        for s in ("top", "right"): a.spines[s].set_visible(False)
        for s in ("left", "bottom"): a.spines[s].set_color("#d8d6d0")
    col = ["#2a78d6" if v <= 35 else "#e34948" if v >= 66 else "#a8a6a0" for v in last.oscillator]
    a1.barh(last["instrument"], last["oscillator"], color=col, height=0.6)
    for y, v in enumerate(last.oscillator): a1.text(v + 1.2, y, f"{v:.0f}", va="center", fontsize=9, color="#2b2b29")
    for x in (35, 50, 65): a1.axvline(x, color="#d8d6d0", lw=0.8, zorder=0)
    a1.set_xlim(0, 100); a1.spines["left"].set_visible(False)
    a1.set_title(f"Oscillator {log.month.max()}: 1 = lock in, 100 = stay short\nblue ≤35 · gray fair · red ≥66", fontsize=10, loc="left", color="#2b2b29")
    tenors = [("T-bill", 0.25, "tbill91"), ("G-sec 3y", 3, "gsec3"), ("G-sec 5y", 5, "gsec5"), ("G-sec 10y", 10, "gsec10")]
    xs = [t[1] for t in tenors]; ys = [num(row.get(t[2])) for t in tenors]
    a2.plot(xs, ys, color="#2a78d6", marker="o", lw=2, label="G-sec curve")
    pts = [("AAA 1y", 1, "aaa1y"), ("AAA 5y", 5, "aaa5y"), ("AA 3y", 3, "aa3y"), ("FD 5y", 5, "fd5y"), ("FRSB", 7, "frsb"), ("Repo", 0, "repo")]
    for lab, x, c in pts:
        v = num(row.get(c))
        if v is None: continue
        a2.scatter([x], [v], color="#e34948" if lab.startswith("A") else "#55544f", zorder=3, s=22)
        a2.annotate(f"{lab} {v:.2f}", (x, v), textcoords="offset points", xytext=(5, 4), fontsize=8, color="#2b2b29")
    a2.set_xlabel("Tenor (years)", fontsize=8.5, color="#55544f"); a2.set_ylabel("Yield %", fontsize=8.5, color="#55544f")
    a2.set_title("Rate ladder (pre-tax)", fontsize=10, loc="left", color="#2b2b29")
    fig.tight_layout(); fig.savefig(CHART, dpi=160); plt.close(fig)
    print(f"\nchart -> {CHART}")

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    keys = sys.argv[2:]
    log, latest, cfg, row = run(keys, verbose=cmd in ("all", "drivers"))
    if cmd in ("all", "table"): table(log)
    if cmd in ("all", "call"): call(latest, cfg, row)
    if cmd in ("all", "ladder"): ladder(latest, cfg, row)
    if cmd in ("all", "lockin"): lockin(latest, cfg, row)
    if cmd in ("all", "chart"): chart(log, latest, row)
