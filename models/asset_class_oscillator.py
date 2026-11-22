"""Asset-Class Valuation Model (INR investor) — v1 — "Asset Mgmt" project.

Rates every main asset class open to someone living in India from 1 (cheap vs its own history)
to 100 (rich), with the same engine as the other project models:
  per-indicator score = clamp(1 + 99*(x - cheap)/(rich - cheap), 1, 100)   (high = expensive)
  weight W = Impact x Severity x Reliability x Stability; blank inputs skipped, weights re-normalised;
  an asset resting on a single live indicator moves only half-way from 50 (THIN_SHRINK).
Where the project already has a dedicated model (Nifty 50, sectors, global, gold), its Valuation
bucket is imported as one indicator, so this model never contradicts them; cross-asset indicators
(yield vs G-sec, real yields, spreads, INR REER) are added on top.

Files (project, under claude/):
  asset-classes-config.json         assets, indicators, anchors, weights (editable)
  asset-classes-inputs-monthly.csv  one row per month of raw market inputs (wide format)
  asset-classes-score-log.csv       output (regenerated on every run)
Usage: python3 asset_class_oscillator.py [all|table|drivers|chart] [ASSET_KEY ...]
"""
import json, sys, math
import pandas as pd

CONFIG, INPUTS, LOG = "asset-classes-config.json", "asset-classes-inputs-monthly.csv", "asset-classes-score-log.csv"
THIN_SHRINK = 0.5

def num(v):
    try:
        f = float(v); return None if math.isnan(f) else f
    except (TypeError, ValueError):
        return None

def _f(*cols):
    """Decorator-free helper: return None if any input is blank."""
    def wrap(fn):
        def inner(r):
            vals = [num(r.get(c)) for c in cols]
            return None if None in vals else fn(*vals)
        return inner
    return wrap

# Formula for every 'derive' key in the config (raw CSV columns -> indicator value)
DERIVE = {
    "imp_nifty_v":   _f("imp_nifty_v")(lambda v: v),
    "imp_mid_v":     _f("imp_mid_v")(lambda v: v),
    "imp_small_v":   _f("imp_small_v")(lambda v: v),
    "imp_acwi_v":    _f("imp_acwi_v")(lambda v: v),
    "imp_sp500_v":   _f("imp_sp500_v")(lambda v: v),
    "imp_gold_v":    _f("imp_gold_v")(lambda v: v),
    "nifty_yield_gap": _f("nifty", "nifty_eps", "gsec10")(lambda p, e, y: 100*e/p - y),
    "mid_pe_rel":    _f("mid150_pe", "nifty", "nifty_eps")(lambda m, p, e: m/(p/e)),
    "small_pe_rel":  _f("small250_pe", "nifty", "nifty_eps")(lambda s, p, e: s/(p/e)),
    "mid_yield_gap": _f("mid150_pe", "gsec10")(lambda m, y: 100/m - y),
    "small_yield_gap": _f("small250_pe", "gsec10")(lambda s, y: 100/s - y),
    "sp_erp":        _f("sp500_fpe", "us10y")(lambda f, y: 100/f - y),
    "inr_reer":      _f("inr_reer")(lambda v: v),
    "gold_vs_36m":   _f("gold_usd", "usdinr", "gold_inr_36m_avg")(lambda g, fx, a: (g*fx/a - 1)*100),
    "silver_vs_36m": _f("silver_usd", "usdinr", "silver_inr_36m_avg")(lambda s, fx, a: (s*fx/a - 1)*100),
    "gsr":           _f("gold_usd", "silver_usd")(lambda g, s: g/s),
    "gsec_real":     _f("gsec10", "cpi_exp1y")(lambda y, c: y - c),
    "term_spread":   _f("gsec10", "repo")(lambda y, r: y - r),
    "gsec10":        _f("gsec10")(lambda v: v),
    "in_us_spread":  _f("gsec10", "us10y")(lambda a, b: a - b),
    "aaa5_real":     _f("aaa5y", "cpi_exp1y")(lambda y, c: y - c),
    "aaa5_spread":   _f("aaa5y", "gsec5")(lambda a, g: (a - g)*100),
    "aa3_real":      _f("aa3y", "cpi_exp1y")(lambda y, c: y - c),
    "aa3_spread":    _f("aa3y", "gsec3")(lambda a, g: (a - g)*100),
    "aaa1_minus_repo": _f("aaa1y", "repo")(lambda a, r: a - r),
    "aaa1_minus_repo_exp": _f("aaa1y", "repo_exp1y")(lambda a, r: a - r),
    "aaa1_real":     _f("aaa1y", "cpi_exp1y")(lambda y, c: y - c),
    "tbill_real":    _f("tbill91", "cpi_exp1y")(lambda y, c: y - c),
    "fd_real":       _f("fd1y", "cpi_exp1y")(lambda y, c: y - c),
    "reit_yield":    _f("reit_yield")(lambda v: v),
    "reit_spread":   _f("reit_yield", "gsec10")(lambda r, y: r - y),
    "rent_minus_loan": _f("rent_yield", "home_loan")(lambda r, l: r - l),
    "rent_yield":    _f("rent_yield")(lambda v: v),
    "px_vs_income":  _f("house_px_cagr", "income_cagr")(lambda p, i: p - i),
    "tips10":        _f("tips10")(lambda v: v),
    "real_diff":     _f("tips10", "gsec10", "cpi_exp1y")(lambda t, y, c: t - (y - c)),
}
# Running income / yield of each asset (information only, not scored), %
CARRY = {
    "NIFTY50": _f("nifty", "nifty_eps")(lambda p, e: 100*e/p),
    "MIDCAP": _f("mid150_pe")(lambda m: 100/m), "SMALLCAP": _f("small250_pe")(lambda s: 100/s),
    "US_EQ": _f("sp500_fpe")(lambda f: 100/f), "GLOBAL_EQ": _f("acwi_fpe")(lambda f: 100/f),
    "GOLD": lambda r: 0.0, "SILVER": lambda r: 0.0,
    "GSEC_LONG": _f("gsec10")(lambda v: v), "CORP_AAA": _f("aaa5y")(lambda v: v),
    "CREDIT_AA": _f("aa3y")(lambda v: v), "SHORT_DEBT": _f("aaa1y")(lambda v: v),
    "CASH": _f("tbill91")(lambda v: v), "REIT": _f("reit_yield")(lambda v: v),
    "RESI_RE": _f("rent_yield")(lambda v: v), "US_TREASURY": _f("us10y")(lambda v: v),
}
OSC = {"NIFTY50": "osc_nifty", "MIDCAP": "osc_mid", "SMALLCAP": "osc_small", "GLOBAL_EQ": "osc_acwi",
       "US_EQ": "osc_sp500", "GOLD": "osc_gold"}

def ind_score(c, r, x):
    return max(1.0, min(100.0, 1 + 99*(x - c)/(r - c)))

def val_band(x):
    return ("Very cheap" if x <= 20 else "Cheap" if x <= 35 else "Fair, cheap side" if x <= 50
            else "Fair, rich side" if x <= 65 else "Expensive" if x <= 80 else "Very expensive")

def tilt(x):
    return ("Overweight (add)" if x <= 35 else "Neutral, lean add" if x <= 50 else
            "Neutral, lean trim" if x <= 65 else "Underweight (trim)")

def osc_band(x):
    return ("STRONG BUY" if x <= 20 else "BUY" if x <= 35 else "ACCUMULATE" if x <= 50
            else "HOLD" if x <= 65 else "TRIM" if x <= 80 else "EXIT")

def score_asset(a, row):
    drivers, n_ = [], 0.0; d_ = 0.0; w_all = 0.0
    for ind in a["indicators"]:
        w = ind["I"]*ind["S"]*ind["R"]*ind["St"]; w_all += w
        x = DERIVE[ind["derive"]](row)
        if x is None: continue
        s = ind_score(ind["cheap"], ind["rich"], x)
        n_ += w*s; d_ += w
        drivers.append({"id": ind["id"], "name": ind["name"], "type": ind["type"], "value": round(x, 2),
                        "unit": ind.get("unit", ""), "score": round(s, 1), "w": round(w, 1)})
    if not d_: return None
    sc = n_/d_
    thin = len(drivers) == 1
    if thin: sc = 50 + (sc - 50)*THIN_SHRINK
    for dd in drivers:
        dd["pull"] = round((dd["w"]/d_)*(dd["score"] - 50)*(THIN_SHRINK if thin else 1), 2)
    return {"score": sc, "drivers": drivers, "coverage": d_/w_all, "live": f"{len(drivers)}/{len(a['indicators'])}", "thin": thin}

def run(keys=None, verbose=True):
    cfg = json.load(open(CONFIG))
    df = pd.read_csv(INPUTS, dtype={"month": str})
    rows = []
    for _, r in df.iterrows():
        row = r.to_dict(); month = row["month"]
        for a in cfg["assets"]:
            s = score_asset(a, row)
            if s is None: continue
            carry = CARRY.get(a["key"], lambda _: None)(row)
            osc = num(row.get(OSC.get(a["key"], ""), None)) if a["key"] in OSC else None
            rows.append({"month": month, "asset": a["key"], "name": a["name"], "family": a["family"],
                         "valuation_score": round(s["score"], 1), "valuation_read": val_band(s["score"]),
                         "tilt": tilt(s["score"]), "income_yield_pct": None if carry is None else round(carry, 2),
                         "own_model_oscillator": osc, "own_model_signal": osc_band(osc) if osc is not None else None,
                         "indicators_live": s["live"], "coverage": round(s["coverage"], 2),
                         "drivers": "; ".join(f"{d['id']} {d['value']}{d['unit'] if d['unit'] in ('%','x') else ' '+d['unit']}->{d['score']:.0f}" for d in s["drivers"]),
                         "access": a.get("access", "")})
            if verbose and month == df.month.max() and (not keys or a["key"] in keys):
                print(f"\n=== {a['name']} ({a['key']}) {month}: VALUATION {s['score']:.1f} -> {val_band(s['score'])} | "
                      f"{tilt(s['score'])} | live {s['live']}, weight coverage {s['coverage']:.0%}"
                      + (f" | own-model oscillator {osc} {osc_band(osc)}" if osc is not None else ""))
                for d in sorted(s["drivers"], key=lambda d: -d["pull"]):
                    print(f"   {d['id']:<3} {d['name']:<55} {d['type']:<10} value={d['value']:<8} {d['unit']:<5} score={d['score']:>5} W={d['w']:<5} pull={d['pull']:+.2f}")
    log = pd.DataFrame(rows).sort_values(["month", "valuation_score"]).reset_index(drop=True)
    log.insert(2, "rank", log.groupby("month").cumcount() + 1)
    log.to_csv(LOG, index=False)
    return log

def table(log):
    last = log[log.month == log.month.max()]
    print(f"\nASSET-CLASS VALUATION RANKING {log.month.max()} (1 = cheapest vs own history, 100 = richest)")
    print(last[["rank", "asset", "family", "valuation_score", "valuation_read", "tilt", "income_yield_pct",
                "own_model_oscillator", "indicators_live"]].to_string(index=False))
    fam = last.groupby("family")["valuation_score"].mean().sort_values().round(1)
    print("\nBy family (simple average):"); print(fam.to_string())

CHART = "asset-classes-valuation.png"
def chart(log):
    """Horizontal bar ranking: blue = cheap (<=35), gray = fair (36-65), red = rich (>=66)."""
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    last = log[log.month == log.month.max()].sort_values("valuation_score", ascending=False)
    col = ["#2a78d6" if v <= 35 else "#e34948" if v >= 66 else "#a8a6a0" for v in last.valuation_score]
    fig, ax = plt.subplots(figsize=(8, 6.2), facecolor="#fcfcfb"); ax.set_facecolor("#fcfcfb")
    ax.barh(last["name"], last["valuation_score"], color=col, height=0.62, edgecolor="#fcfcfb", linewidth=2)
    for y, v in enumerate(last.valuation_score):
        ax.text(v + 1.2, y, f"{v:.0f}", va="center", fontsize=9, color="#2b2b29")
    for x in (35, 50, 65):
        ax.axvline(x, color="#d8d6d0", lw=0.8, zorder=0)
    ax.set_xlim(0, 100); ax.tick_params(labelsize=9, colors="#55544f", length=0)
    for s in ("top", "right", "left"): ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color("#d8d6d0")
    ax.set_xlabel("Valuation score (1 = cheap vs own history, 100 = rich)", fontsize=9, color="#55544f")
    ax.set_title(f"Asset classes for an INR investor — valuation, {log.month.max()}\nblue = cheap (≤35) · gray = fair · red = expensive (≥66)",
                 fontsize=10.5, color="#2b2b29", loc="left")
    fig.tight_layout(); fig.savefig(CHART, dpi=160); plt.close(fig)
    print(f"\nchart -> {CHART}")

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    keys = sys.argv[2:]
    log = run(keys, verbose=cmd in ("all", "drivers"))
    if cmd in ("all", "table"): table(log)
    if cmd in ("all", "chart"): chart(log)
