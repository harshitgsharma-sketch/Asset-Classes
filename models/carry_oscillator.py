"""Low-Risk Carry Model (INR investor) — v1, indicative — "Asset Mgmt" project.

Scores how attractive two low-risk carry trades on the Nifty are right now, for the months when most
assets score Hold and new money needs a parking place that beats a liquid fund after tax:
  ARBITRAGE     arbitrage mutual fund (long cash equity + short futures; earns the futures basis)
  COVERED_CALL  long Nifty (ETF / futures) + short 1-month ~2% OTM Nifty call, rolled monthly
Same engine as the other project models, same direction:
  per-indicator score = clamp(1 + 99*(x - cheap)/(rich - cheap), 1, 100)
  here 'cheap' = the attractive end, so 1 = carry very attractive (use it), 100 = carry poor (stay in liquid / hold Nifty uncapped)
  weight W = Impact x Severity x Reliability x Stability; blank inputs skipped, weights re-normalised;
  a strategy resting on a single live indicator moves only half-way from 50 (THIN_SHRINK).
The covered-call premium is priced with Black-Scholes from ATM IV (falls back to India VIX), so only
market levels are needed as inputs. Post-tax numbers use the tax scenario in carry-config.json.

Files (project, under claude/):
  carry-config.json           strategies, indicators, anchors, weights, tax scenarios, call strike/tenor
  carry-inputs-monthly.csv    one row per month of raw inputs
  carry-score-log.csv         output (regenerated on every run)
Usage: python3 carry_oscillator.py [all|table|drivers|tax|sens|chart] [STRATEGY_KEY ...]
"""
import json, sys, math
import pandas as pd

CONFIG, INPUTS, LOG, CHART = "carry-config.json", "carry-inputs-monthly.csv", "carry-score-log.csv", "carry-oscillator.png"
THIN_SHRINK = 0.5
SWEET_SPOT = 58.0   # Nifty oscillator level where covered calls pay best (range-bound Hold market)

def num(v):
    try:
        f = float(v); return None if math.isnan(f) else f
    except (TypeError, ValueError):
        return None

def ncdf(x):
    return 0.5*(1 + math.erf(x/math.sqrt(2)))

def bs_call_pct(vol_pct, days, otm_pct, r_pct, q_pct):
    """Black-Scholes call premium as % of spot, strike = spot*(1+otm). Returns (premium %, N(d2))."""
    s, k = 1.0, 1 + otm_pct/100; t = days/365; v = vol_pct/100; r = r_pct/100; q = q_pct/100
    d1 = (math.log(s/k) + (r - q + v*v/2)*t)/(v*math.sqrt(t)); d2 = d1 - v*math.sqrt(t)
    c = s*math.exp(-q*t)*ncdf(d1) - k*math.exp(-r*t)*ncdf(d2)
    return 100*c, ncdf(d2)

def ann(simple_pct, months):
    return 100*((1 + simple_pct/100)**(12/months) - 1)

class Ctx:
    """All derived quantities for one input row under one tax scenario."""
    def __init__(self, row, cfg, scen=None):
        g = lambda c: num(row.get(c))
        tax = cfg["tax"]; t = tax["scenarios"][scen or tax["scenario"]]
        self.t = t; self.row = row
        self.liq = None if g("liquid_ytm") is None else g("liquid_ytm") - (g("liquid_ter") or 0)
        self.liq_pt = None if self.liq is None else self.liq*(1 - t["slab"]/100)
        self.arb3 = None if g("arb_ret_3m") is None else ann(g("arb_ret_3m"), 3)
        self.arb1 = None if g("arb_ret_1m") is None else ann(g("arb_ret_1m"), 1)
        arb_tax = t["equity_st"] if tax.get("arb_holding", "short") == "short" else t["equity_lt"]
        self.arb_pt = None if self.arb3 is None else self.arb3*(1 - arb_tax/100)
        cc = cfg["covered_call"]
        vol = g("atm_iv") if g("atm_iv") is not None else g("vix")
        self.vix, self.vol, self.rv = g("vix"), vol, g("rv20")
        self.prem = self.p_call = self.cc_gross = self.cc_pt = self.sd_move = None
        if vol is not None:
            r = g("tbill91") if g("tbill91") is not None else (g("repo") or 6.0)
            self.prem, self.p_call = bs_call_pct(vol - cc.get("call_skew_vol_pts", 0), cc["days"], cc["otm_pct"], r, g("nifty_div_yield") or 0)
            self.cc_gross = self.prem*365/cc["days"] - cc["cost_bp_pa"]/100
            prem_tax = t["slab"] if tax.get("cc_premium_taxed_at", "slab") == "slab" else t["equity_st"]
            self.cc_pt = self.cc_gross*(1 - prem_tax/100)
            self.sd_move = (self.vix or vol)*math.sqrt(cc["days"]/365)
        self.repo_exp, self.cpi_exp, self.osc = g("repo_exp1y"), g("cpi_exp1y"), g("osc_nifty")
        self.div = g("nifty_div_yield")

def _need(*vals):
    return None in vals

DERIVE = {
    "arb_post_tax_edge": lambda c: None if _need(c.arb_pt, c.liq_pt) else c.arb_pt - c.liq_pt,
    "arb_gross_spread":  lambda c: None if _need(c.arb3, c.liq) else c.arb3 - c.liq,
    "arb_1m_spread":     lambda c: None if _need(c.arb1, c.liq) else c.arb1 - c.liq,
    "arb_minus_repo_exp": lambda c: None if _need(c.arb3, c.repo_exp) else c.arb3 - c.repo_exp,
    "arb_real_post_tax": lambda c: None if _need(c.arb_pt, c.cpi_exp) else c.arb_pt - c.cpi_exp,
    "cc_post_tax_yield": lambda c: c.cc_pt,
    "vix":               lambda c: c.vix,
    "vrp":               lambda c: None if _need(c.vol, c.rv) else c.vol - c.rv,
    "cc_regime_gap":     lambda c: None if c.osc is None else abs(c.osc - SWEET_SPOT),
    "cc_cushion":        lambda c: None if _need(c.prem, c.sd_move) else 100*c.prem/c.sd_move,
}

def ind_score(c, r, x):
    return max(1.0, min(100.0, 1 + 99*(x - c)/(r - c)))

def band(x):
    return ("STRONG BUY" if x <= 20 else "BUY" if x <= 35 else "ACCUMULATE" if x <= 50
            else "HOLD" if x <= 65 else "TRIM" if x <= 80 else "EXIT")

ACTION = {
    "ARBITRAGE": [(35, "Park idle and 3-12 m money in arbitrage funds"),
                  (50, "Prefer arbitrage over liquid for money parked 3 m or more"),
                  (65, "Either works; liquid for money needed within 3 m"),
                  (101, "Prefer liquid / money-market funds")],
    "COVERED_CALL": [(35, "Write 2% OTM calls on the whole core Nifty holding"),
                     (50, "Write calls on about half of the Nifty holding"),
                     (65, "Optional: small overlay only"),
                     (101, "Don't cap the upside; hold the Nifty uncapped (or trim it per the Nifty model)")],
}
def action(key, x):
    return next(t for lim, t in ACTION[key] if x <= lim)

def score_strategy(s, ctx):
    drivers, n_, d_, w_all = [], 0.0, 0.0, 0.0
    for ind in s["indicators"]:
        w = ind["I"]*ind["S"]*ind["R"]*ind["St"]; w_all += w
        x = DERIVE[ind["derive"]](ctx)
        if x is None: continue
        sc = ind_score(ind["cheap"], ind["rich"], x)
        n_ += w*sc; d_ += w
        drivers.append({"id": ind["id"], "name": ind["name"], "type": ind["type"], "value": round(x, 2),
                        "unit": ind.get("unit", ""), "score": round(sc, 1), "w": round(w, 2)})
    if not d_: return None
    sc = n_/d_; thin = len(drivers) == 1
    if thin: sc = 50 + (sc - 50)*THIN_SHRINK
    for dd in drivers:
        dd["pull"] = round((dd["w"]/d_)*(dd["score"] - 50)*(THIN_SHRINK if thin else 1), 2)
    return {"score": sc, "drivers": drivers, "coverage": d_/w_all, "live": f"{len(drivers)}/{len(s['indicators'])}"}

def info(key, ctx):
    """Yield / risk columns shown next to the score (not scored)."""
    if key == "ARBITRAGE":
        return {"gross_yield_pct": ctx.arb3, "post_tax_yield_pct": ctx.arb_pt,
                "edge_vs_liquid_post_tax_pp": None if _need(ctx.arb_pt, ctx.liq_pt) else ctx.arb_pt - ctx.liq_pt,
                "downside_note": "no market downside; flat/negative spread month possible"}
    if ctx.cc_gross is None: return {}
    one_sd_loss = None if ctx.sd_move is None else -(ctx.sd_move - ctx.prem)
    return {"gross_yield_pct": ctx.cc_gross, "post_tax_yield_pct": ctx.cc_pt,
            "edge_vs_liquid_post_tax_pp": None if _need(ctx.cc_pt, ctx.liq_pt) else ctx.cc_pt + (ctx.div or 0)*(1 - ctx.t["slab"]/100) - ctx.liq_pt,
            "premium_1m_pct": ctx.prem, "prob_called_away_pct": 100*ctx.p_call,
            "one_sd_down_month_pct": one_sd_loss,
            "downside_note": f"keeps full Nifty downside less premium; 1-SD down month {one_sd_loss:.1f}%" if one_sd_loss is not None else ""}

def run(keys=None, verbose=True):
    cfg = json.load(open(CONFIG))
    df = pd.read_csv(INPUTS, dtype={"month": str})
    rows, last = [], df.month.max()
    for _, r in df.iterrows():
        row = r.to_dict(); ctx = Ctx(row, cfg)
        for s in cfg["strategies"]:
            res = score_strategy(s, ctx)
            if res is None: continue
            inf = info(s["key"], ctx)
            rnd = lambda v: None if v is None else round(v, 2)
            rows.append({"month": row["month"], "strategy": s["key"], "name": s["name"],
                         "oscillator": round(res["score"], 1), "signal": band(res["score"]),
                         "action": action(s["key"], res["score"]),
                         "gross_yield_pct": rnd(inf.get("gross_yield_pct")),
                         "post_tax_yield_pct": rnd(inf.get("post_tax_yield_pct")),
                         "liquid_post_tax_pct": rnd(ctx.liq_pt),
                         "edge_vs_liquid_post_tax_pp": rnd(inf.get("edge_vs_liquid_post_tax_pp")),
                         "premium_1m_pct": rnd(inf.get("premium_1m_pct")),
                         "prob_called_away_pct": rnd(inf.get("prob_called_away_pct")),
                         "one_sd_down_month_pct": rnd(inf.get("one_sd_down_month_pct")),
                         "tax_scenario": cfg["tax"]["scenario"],
                         "indicators_live": res["live"], "coverage": round(res["coverage"], 2),
                         "drivers": "; ".join(f"{d['id']} {d['value']}{d['unit'] if d['unit'] in ('%','pp') else ' '+d['unit']}->{d['score']:.0f}" for d in res["drivers"]),
                         "source": row.get("source", "")})
            if verbose and row["month"] == last and (not keys or s["key"] in keys):
                print(f"\n=== {s['name']} ({s['key']}) {row['month']}: CARRY OSCILLATOR {res['score']:.1f} -> {band(res['score'])} | "
                      f"{action(s['key'], res['score'])} | live {res['live']}, weight coverage {res['coverage']:.0%}")
                for d in sorted(res["drivers"], key=lambda d: -d["pull"]):
                    print(f"   {d['id']:<3} {d['name']:<76} {d['type']:<10} value={d['value']:<7} {d['unit']:<5} score={d['score']:>5} W={d['w']:<5} pull={d['pull']:+.2f}")
                for k, v in inf.items():
                    print(f"   · {k}: {round(v, 2) if isinstance(v, float) else v}")
    log = pd.DataFrame(rows).sort_values(["month", "oscillator"]).reset_index(drop=True)
    log.to_csv(LOG, index=False)
    return log, cfg, df

def table(log):
    last = log[log.month == log.month.max()]
    print(f"\nLOW-RISK CARRY {log.month.max()} (1 = carry very attractive, 100 = poor; tax scenario {last.tax_scenario.iloc[0]})")
    print(last[["strategy", "oscillator", "signal", "gross_yield_pct", "post_tax_yield_pct", "liquid_post_tax_pct",
                "edge_vs_liquid_post_tax_pp", "indicators_live"]].to_string(index=False))
    print(f"\nBest carry now: {last.iloc[0].strategy} ({last.iloc[0].oscillator}) -> {last.iloc[0].action}")

def tax_table(cfg, df):
    row = df[df.month == df.month.max()].iloc[0].to_dict()
    print(f"\nPOST-TAX YIELDS BY TAX SLAB {row['month']} (% a year; covered call excludes Nifty price change)")
    out = []
    for name in cfg["tax"]["scenarios"]:
        c = Ctx(row, cfg, name)
        out.append({"scenario": name, "liquid_post_tax": round(c.liq_pt, 2), "arbitrage_post_tax": round(c.arb_pt, 2),
                    "arb_edge_pp": round(c.arb_pt - c.liq_pt, 2),
                    "cc_premium_post_tax": None if c.cc_pt is None else round(c.cc_pt, 2)})
    print(pd.DataFrame(out).to_string(index=False))

def sens(cfg, df):
    """Covered-call oscillator if India VIX (and ATM IV, same shift) were at other levels; arbitrage unchanged."""
    row = df[df.month == df.month.max()].iloc[0].to_dict()
    s = next(x for x in cfg["strategies"] if x["key"] == "COVERED_CALL")
    v0, iv0 = num(row.get("vix")), num(row.get("atm_iv"))
    print(f"\nCOVERED-CALL SENSITIVITY TO INDIA VIX ({row['month']}, now {v0}; realised vol and Nifty oscillator held)")
    print(f"{'VIX':>5} {'ATM IV':>7} {'prem 1m %':>9} {'post-tax %':>10} {'score':>6}  signal")
    for v in (11, 13, 15, v0, 18, 20, 22, 25):
        r2 = dict(row); r2["vix"] = v
        if iv0 is not None: r2["atm_iv"] = iv0 + (v - v0)
        c = Ctx(r2, cfg); res = score_strategy(s, c)
        print(f"{v:>5} {(r2.get('atm_iv') or v):>7.1f} {c.prem:>9.2f} {c.cc_pt:>10.2f} {res['score']:>6.1f}  {band(res['score'])}")

def chart(log):
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    last = log[log.month == log.month.max()]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(10, 3.4), facecolor="#fcfcfb", gridspec_kw={"width_ratios": [1.1, 1]})
    for ax in (a1, a2):
        ax.set_facecolor("#fcfcfb"); ax.tick_params(labelsize=9, colors="#55544f", length=0)
        for sp in ("top", "right", "left"): ax.spines[sp].set_visible(False)
        ax.spines["bottom"].set_color("#d8d6d0")
    names = ["Arbitrage fund" if k == "ARBITRAGE" else "Nifty covered call" for k in last.strategy]
    col = ["#2a78d6" if v <= 35 else "#e34948" if v >= 66 else "#a8a6a0" for v in last.oscillator]
    a1.barh(names, last.oscillator, color=col, height=0.5)
    for y, v in enumerate(last.oscillator): a1.text(v + 1.5, y, f"{v:.0f} {band(v)}", va="center", fontsize=9, color="#2b2b29")
    for x in (20, 35, 50, 65, 80): a1.axvline(x, color="#d8d6d0", lw=0.8, zorder=0)
    a1.set_xlim(0, 100); a1.set_xlabel("Carry oscillator (1 = very attractive, 100 = poor)", fontsize=9, color="#55544f")
    a1.set_title(f"Low-risk carry, {log.month.max()} (v1, indicative)", fontsize=10.5, color="#2b2b29", loc="left")
    labels = ["Liquid fund"] + names; vals = [last.liquid_post_tax_pct.iloc[0]] + list(last.post_tax_yield_pct)
    a2.bar(labels, vals, color=["#a8a6a0", "#2a78d6", "#7c5cc4"], width=0.55)
    for x, v in enumerate(vals): a2.text(x, v + 0.1, f"{v:.1f}%", ha="center", fontsize=9, color="#2b2b29")
    a2.set_ylabel("Post-tax yield, % a year", fontsize=9, color="#55544f")
    a2.set_title(f"Post-tax carry ({last.tax_scenario.iloc[0]}); covered call = premium only", fontsize=9.5, color="#2b2b29", loc="left")
    fig.tight_layout(); fig.savefig(CHART, dpi=160); plt.close(fig)
    print(f"\nchart -> {CHART}")

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    keys = sys.argv[2:]
    log, cfg, df = run(keys, verbose=cmd in ("all", "drivers"))
    if cmd in ("all", "table"): table(log)
    if cmd in ("all", "tax"): tax_table(cfg, df)
    if cmd in ("all", "sens"): sens(cfg, df)
    if cmd in ("all", "chart"): chart(log)
