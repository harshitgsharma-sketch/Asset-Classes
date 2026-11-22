"""Bitcoin Entry/Exit Oscillator — v1 (21-Nov-2026, indicative) — "Asset Mgmt" project.

Small satellite allocation for an INR investor with a holding period of 5 years or less.
Same engine as the gold / Nifty models:
  per-indicator score = clamp(1 + 99*(x - cheap)/(rich - cheap), 1, 100)   (1 = cheap/buy, 100 = rich/sell)
  weight = Impact x Severity x Reliability x Stability; blank inputs skipped, weights re-normalised per bucket
  Oscillator = .45 Valuation (on-chain + cycle) + .35 Timing (trend, leverage, flows, sentiment)
             + .20 Filter (dollar and liquidity regime; shared DXY / real yield / Fed / M2 inputs)
  Filter >= 70 while Oscillator <= 35 -> "BUY - STAGED (macro filter high)": buy in tranches, not lump sum.
On top: an India tax/cost layer (30% + cess on VDA gains, 1% TDS, no loss set-off) applied to the
5-yr scenarios, an ETF-via-LRS comparison, and a position-size cap.

Files (project, under claude/):
  btc-inputs-monthly.csv   one row per month-end; i01..i15 indicator values + raw helper columns
  btc-scenarios.json       Bear/Base/Bull 5-yr paths, tax/cost assumptions, sizing rule
  btc-score-log.csv        output: scores for every month with enough inputs (regenerated)
Usage:
  python3 btc_oscillator.py score     # recompute log, print latest, month-end range, trend, drivers
  python3 btc_oscillator.py project   # 5-yr scenario score paths + after-tax INR returns + size cap
  python3 btc_oscillator.py chart     # PNG: history + scenarios
  python3 btc_oscillator.py all
"""
import json, sys
import numpy as np, pandas as pd

INPUTS, SCEN, LOG = "btc-inputs-monthly.csv", "btc-scenarios.json", "btc-score-log.csv"
CHART = "btc_oscillator_history_and_outlook.png"
ATH_USD = 126198.07            # 6-Oct-2025 intraday all-time high
PRE_ATH = 19783.0              # Dec-2017 intraday high (seed for reconstructed history)
HALVINGS = ["2016-07", "2020-05", "2024-04", "2028-04"]   # 2028 date is an estimate
BUCKET_W = {"Valuation": 0.45, "Timing": 0.35, "Filter": 0.20}
MIN_INPUTS = 6

# id: (name, bucket, type, impact, severity, reliability, stability, cheap->1, rich->100, unit)
SPEC = {
 1: ("MVRV (price / realized price)", "Valuation", "Leading", 5, 5, 1.0, 1.0, 0.9, 3.0, "x"),
 2: ("Price / 200-week MA", "Valuation", "Leading", 5, 4, 1.0, 1.0, 0.85, 2.5, "x"),
 3: ("Distance from ATH", "Valuation", "Coincident", 4, 4, 0.875, 1.0, -75, -5, "%"),
 4: ("Halving-cycle phase heat", "Valuation", "Leading", 4, 3, 0.75, 0.75, 1, 100, "0-100"),
 5: ("Puell multiple", "Valuation", "Coincident", 3, 3, 0.75, 0.75, 0.5, 3.0, "x"),
 6: ("Price / 200-day MA (Mayer)", "Timing", "Coincident", 4, 4, 1.0, 1.0, 0.7, 1.6, "x"),
 7: ("Perp funding, 30-d annualised", "Timing", "Coincident", 3, 4, 0.875, 1.0, -5, 25, "%"),
 8: ("US spot ETF net flow, month", "Timing", "Coincident", 4, 3, 0.75, 1.0, -4, 6, "$bn"),
 9: ("Crypto Fear & Greed", "Timing", "Coincident", 3, 3, 0.75, 1.0, 10, 90, "index"),
 10: ("Monthly RSI(14)", "Timing", "Lagging", 2, 4, 0.75, 1.0, 30, 85, "RSI"),
 11: ("Stablecoin supply, 3-m change", "Timing", "Leading", 3, 3, 0.75, 0.75, 10, -5, "%"),
 12: ("Dollar index (DXY)", "Filter", "Leading", 4, 4, 0.875, 1.0, 92, 110, "index"),
 13: ("US 10-yr real yield (TIPS)", "Filter", "Leading", 4, 4, 1.0, 0.75, 0.0, 3.0, "%"),
 14: ("Expected Fed change next ~6m", "Filter", "Leading", 4, 4, 1.0, 1.0, -100, 75, "bp"),
 15: ("US M2 YoY (liquidity proxy)", "Filter", "Leading", 3, 3, 0.75, 0.75, 10, 0, "%"),
}
COLS = [f"i{k:02d}" for k in SPEC]
WEIGHT = {k: v[3]*v[4]*v[5]*v[6] for k, v in SPEC.items()}
TOTAL_W = sum(WEIGHT.values())

def band(x):
    return ("STRONG BUY" if x <= 20 else "BUY" if x <= 35 else "ACCUMULATE SLOWLY" if x <= 50
            else "HOLD" if x <= 65 else "TRIM" if x <= 80 else "EXIT")

def ind_score(k, x):
    c, r = SPEC[k][7], SPEC[k][8]
    return float(np.clip(1 + 99*(x - c)/(r - c), 1, 100))

def score_row(row):
    out, cov = {}, 0.0
    for b in BUCKET_W:
        num = den = 0.0
        for k, v in SPEC.items():
            x = row.get(f"i{k:02d}", np.nan)
            if v[1] != b or x is None or pd.isna(x):
                continue
            num += WEIGHT[k]*ind_score(k, float(x)); den += WEIGHT[k]; cov += WEIGHT[k]
        out[b] = num/den if den else np.nan
    live = {b: w for b, w in BUCKET_W.items() if not pd.isna(out[b])}
    out["Oscillator"] = sum(w*out[b] for b, w in live.items())/sum(live.values())
    out["Coverage"] = cov/TOTAL_W
    out["Signal"] = band(out["Oscillator"])
    if not pd.isna(out["Filter"]) and out["Filter"] >= 70 and out["Oscillator"] <= 35:
        out["Signal"] = "BUY - STAGED (macro filter high)"
    return out

def months_since_halving(month):
    p = pd.Period(month, "M")
    past = [pd.Period(h, "M") for h in HALVINGS if pd.Period(h, "M") <= p]
    return (p - past[-1]).n

def phase_heat(m):
    """Cycle heat from months since the last halving: 50 at the halving, 100 at ~18 m (past cycle tops),
    1 at ~31 m (past cycle lows), back to 50 by 48 m."""
    if m <= 18: return 50 + 50*m/18
    if m <= 31: return 100 - 99*(m - 18)/13
    return 1 + 49*min(m - 31, 17)/17

def rsi_monthly(px, n=14):
    d = px.diff(); up = d.clip(lower=0); dn = -d.clip(upper=0)
    au = up.ewm(alpha=1/n, adjust=False, min_periods=n).mean()
    ad = dn.ewm(alpha=1/n, adjust=False, min_periods=n).mean()
    return 100 - 100/(1 + au/ad)

def ath_series(df):
    p = df["btc_usd"]
    ath = np.maximum(p.cummax(), PRE_ATH)
    ath[pd.PeriodIndex(df["month"], freq="M") >= pd.Period("2025-10", "M")] = ATH_USD
    return ath

def fill_derived(df):
    """Fill price-derived indicators where blank. Live MAs/realized price win over month-end proxies."""
    p = df["btc_usd"]
    wma = df["wma200_usd"].fillna(p.rolling(46).mean())      # ~200 weeks of month-end closes
    dma = df["dma200_usd"].fillna(p.rolling(7).mean())       # ~200 days
    df["i01"] = df["i01"].fillna((p/df["realized_usd"]).round(3))
    df["i02"] = df["i02"].fillna((p/wma).round(3))
    df["i03"] = df["i03"].fillna(((p/ath_series(df) - 1)*100).round(1))
    df["i04"] = df["i04"].fillna(df["month"].map(lambda m: round(phase_heat(months_since_halving(m)), 1)))
    df["i06"] = df["i06"].fillna((p/dma).round(3))
    df["i10"] = df["i10"].fillna(rsi_monthly(p).round(1))
    df["i11"] = df["i11"].fillna(((df["stable_bn"]/df["stable_bn"].shift(3) - 1)*100).round(1))
    df["i15"] = df["i15"].fillna(((df["m2_tn"]/df["m2_tn"].shift(12) - 1)*100).round(1))
    return df

def reprice(row, raw, f):
    """Row with price-derived indicators recomputed at price x f (month-end range)."""
    r = dict(row); p = raw["btc_usd"]*f
    for k, base in (("i01", raw.get("realized_usd")), ("i02", raw.get("wma200_usd")), ("i06", raw.get("dma200_usd"))):
        if base and not pd.isna(base): r[k] = p/base
    r["i03"] = (p/ATH_USD - 1)*100
    return r

def cmd_score():
    df = fill_derived(pd.read_csv(INPUTS))
    has = df[COLS].notna().sum(axis=1) >= MIN_INPUTS
    rows = []
    for _, r in df[has].iterrows():
        s = score_row(r.to_dict())
        rows.append({"month": r["month"], "btc_usd": r["btc_usd"], "btc_inr_lakh": round(r["btc_usd"]*r["usdinr"]/1e5, 2),
                     "oscillator": round(s["Oscillator"], 1), "valuation": round(s["Valuation"], 1),
                     "timing": round(s["Timing"], 1), "filter": round(s["Filter"], 1),
                     "coverage": round(s["Coverage"], 2), "signal": s["Signal"], "source": r["source"]})
    log = pd.DataFrame(rows); log.to_csv(LOG, index=False)
    last = log.iloc[-1]; prev = log.iloc[-2]
    log["year"] = log.month.str[:4]
    print("LATEST", {k: last[k] for k in ["month", "btc_usd", "btc_inr_lakh", "oscillator", "valuation", "timing", "filter", "coverage", "signal"]})
    print(f"Change vs prior month: {last.oscillator - prev.oscillator:+.1f}")
    r = df[has].iloc[-1]
    rng = [round(score_row(reprice(r.to_dict(), r, f))["Oscillator"], 1) for f in (0.85, 1.15)]
    print(f"Month-end range if BTC closes -15% / +15% from here (${r.btc_usd*0.85:,.0f} / ${r.btc_usd*1.15:,.0f}): {rng[0]} / {rng[1]}")
    print("Yearly averages:", log.groupby("year").oscillator.mean().round(1).to_dict())
    print("12-mo avg:", log.oscillator.tail(12).mean().round(1),
          "| 3-mo slope/month:", round(np.polyfit(range(3), log.oscillator.tail(3), 1)[0], 1))
    i = log.oscillator.idxmax(); j = log.oscillator.idxmin()
    print(f"High {log.oscillator[i]} ({log.month[i]}), Low {log.oscillator[j]} ({log.month[j]})")
    print("Last 12 months:", list(zip(log.month.tail(12), log.oscillator.tail(12), log.signal.tail(12))))
    drv = []
    for k, v in SPEC.items():
        x = r.get(f"i{k:02d}")
        if pd.isna(x): continue
        sc = ind_score(k, float(x))
        drv.append((k, v[0], v[1], v[2], x, round(sc), round(WEIGHT[k]*(sc - 50)/TOTAL_W, 2)))
    drv.sort(key=lambda t: -abs(t[6]))
    print("\nDrivers (pull vs 50, + = towards SELL):")
    for t in drv: print(f"  #{t[0]:>2} {t[1]:<32} {t[2]:<9} {t[3]:<10} value={t[4]:<8} score={t[5]:>3} pull={t[6]:+.2f}")
    missing = [f"#{k} {SPEC[k][0]}" for k in SPEC if pd.isna(r.get(f'i{k:02d}'))]
    print("Missing inputs:", "; ".join(missing) or "none")
    return log

def after_tax(mult_inr, yrs, tx, route):
    """Post-tax, post-cost INR wealth multiple for one rupee invested."""
    if route == "VDA":
        net = mult_inr*(1 - tx["vda_roundtrip_cost_pct"]/100); g = net - 1
        if g > 0: return 1 + g*(1 - tx["vda_rate_pct"]/100)
        tds_drag = tx["tds_pct"]/100*net*tx["opportunity_rate_pct"]/100*tx["tds_refund_lag_yrs"]
        return 1 + g - tds_drag                       # full loss, no set-off; TDS refund arrives late
    net = mult_inr*(1 - tx["etf_cost_pa_pct"]/100)**yrs; g = net - 1
    t = tx["etf_ltcg_pct"]/100
    return 1 + g*(1 - t) if (g > 0 or tx["etf_loss_offset"]) else 1 + g

def cagr(m, yrs): return (m**(1/yrs) - 1)*100 if m > 0 else -100.0

def cmd_project():
    sc = json.load(open(SCEN)); tx = sc["tax"]; years = sc["years"]; st = sc["start"]
    months = [f"20{y[-2:]}-11" for y in years]
    res = {}
    for name, s in sc["scenarios"].items():
        path, ath = [], ATH_USD
        for t, m in enumerate(months):
            p = s["btc_usd"][t]; ath = max(ath, p)
            row = {k: v[t] for k, v in s["drivers"].items()}
            prevp = s["btc_usd"][t-1] if t else st["dma200_usd"]
            row.update({"i01": p/s["realized_usd"][t], "i02": p/s["wma200_usd"][t], "i03": (p/ath - 1)*100,
                        "i04": phase_heat(months_since_halving(m)), "i06": p/(0.5*p + 0.5*prevp)})
            if t == 0: row.update({"i06": p/st["dma200_usd"]})
            path.append(round(score_row(row)["Oscillator"]))
        # INR returns: hold to Nov-31, and exit on the first Trim/Exit reading (>=66)
        d = s["inr_depr_pa"]/100; p0 = s["btc_usd"][0]
        def ret(t):
            mult = s["btc_usd"][t]/p0*(1 + d)**t
            return {"pre": cagr(mult, t), "vda": cagr(after_tax(mult, t, tx, "VDA"), t),
                    "etf": cagr(after_tax(mult, t, tx, "ETF"), t), "mult": mult}
        T = len(years) - 1
        ex = next((t for t in range(1, len(path)) if path[t] >= 66), T)
        res[name] = {"prob": s["prob"], "score": path, "btc_usd": s["btc_usd"], "story": s["story"],
                     "hold": ret(T), "exit_year": years[ex], "exit": ret(ex)}
    out = pd.DataFrame({n: v["score"] for n, v in res.items()}, index=years).T
    print("5-yr score paths:"); print(out.to_string())
    pw = sum(v["prob"]*np.array(v["score"]) for v in res.values())
    print("Prob-weighted score path:", np.round(pw).astype(int).tolist())
    print(f"\nINR returns, % p.a. (USD/INR {st['usdinr']} start; costs and Indian tax applied)")
    print(f"{'':6}{'prob':>5}{'BTC Nov-31':>12}{'INR x':>7}{'pre-tax':>9}{'VDA net':>9}{'ETF/LRS net':>12}   exit on first score>=66 (VDA net, % p.a. over that shorter hold)")
    agg = {"pre": 0, "vda": 0, "etf": 0, "exit": 0}
    for n, v in res.items():
        h, e = v["hold"], v["exit"]
        print(f"{n:6}{v['prob']:>5.2f}{v['btc_usd'][-1]:>12,.0f}{h['mult']:>7.2f}{h['pre']:>9.1f}{h['vda']:>9.1f}{h['etf']:>12.1f}   {v['exit_year']}: {e['vda']:.1f}")
        for k in ("pre", "vda", "etf"): agg[k] += v["prob"]*h[k]
        agg["exit"] += v["prob"]*e["vda"]
    print(f"{'Prob-weighted':<23}{'':>7}{agg['pre']:>9.1f}{agg['vda']:>9.1f}{agg['etf']:>12.1f}   {agg['exit']:.1f} (mixed holding periods; not comparable)")
    print(f"Tax+cost drag, VDA route: {agg['pre'] - agg['vda']:.1f} pp p.a.; ETF/LRS route: {agg['pre'] - agg['etf']:.1f} pp p.a.")
    # Position-size cap
    sz = sc["sizing"]; log = pd.read_csv(LOG); last = log.iloc[-1]
    key = "BUY" if last.signal.startswith("BUY - STAGED") else last.signal
    bc = sz["band_cap_pct"][key]; dd = sz["stress_drawdown_pct"]/100
    cap_vda = min(bc, sz["loss_budget_pct"]/dd)
    cap_etf = min(bc, sz["loss_budget_pct"]/(dd*(1 - tx["etf_ltcg_pct"]/100)))
    print(f"\nPosition cap (% of investable portfolio) at {last.oscillator} {last.signal}: band cap {bc:.1f}%; "
          f"loss-budget cap {sz['loss_budget_pct']}% / {sz['stress_drawdown_pct']:.0f}% stress fall -> "
          f"VDA {cap_vda:.1f}% | ETF/LRS {cap_etf:.1f}%; build it in {sz['tranches']} tranches")
    json.dump(res, open("btc-projection-latest.json", "w"), indent=1)
    return res

def cmd_chart():
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    h = pd.read_csv(LOG); h["d"] = pd.to_datetime(h.month)
    res = json.load(open("btc-projection-latest.json")); sc = json.load(open(SCEN))
    px = pd.to_datetime([f"20{y[-2:]}-11" for y in sc["years"]])
    fig, ax = plt.subplots(figsize=(12, 6), dpi=150)
    for lo, hi, c, l in [(0,20,"#1a7f37","Strong buy"),(20,35,"#4caf50","Buy"),(35,50,"#c8e6c9","Accumulate"),
                         (50,65,"#eeeeee","Hold"),(65,80,"#ffcc80","Trim"),(80,100,"#ef6c00","Exit")]:
        ax.axhspan(lo, hi, color=c, alpha=.35, lw=0)
        ax.text(px[-1] + pd.Timedelta(days=40), (lo+hi)/2, l, va="center", fontsize=8, color="#444")
    ax.plot(h.d, h.oscillator, color="#1f3b73", lw=2.2, label="Oscillator (month-end)")
    ax.plot(h.d, h.oscillator.rolling(12).mean(), color="#1f3b73", lw=1, ls=":", label="12-mo average")
    col = {"Bear": "#c62828", "Base": "#555555", "Bull": "#b8860b"}
    for n, v in res.items():
        ax.plot(px, v["score"], ls="--", marker="o", ms=4, color=col[n], label=f"{n} ({int(v['prob']*100)}%)")
    ax2 = ax.twinx(); ax2.plot(h.d, h.btc_usd, color="#f7931a", lw=1, alpha=.8, label="BTC $ (rhs, log)")
    ax2.set_yscale("log"); ax2.set_ylim(10000, 400000); ax2.set_ylabel("BTC $ (log)")
    ax.set_ylim(0, 100); ax.set_ylabel("Oscillator (1 cheap … 100 rich)")
    ax.axvline(h.d.iloc[-1], color="#999", lw=.8)
    ax.set_title(f"Bitcoin Entry/Exit Oscillator v1 (indicative) — history to {h.month.iloc[-1]} and 5-yr scenarios")
    a, b = ax.get_legend_handles_labels(); c2, d2 = ax2.get_legend_handles_labels()
    ax.legend(a+c2, b+d2, loc="upper left", fontsize=8)
    plt.tight_layout(); plt.savefig(CHART); print("saved", CHART)

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    if cmd in ("score", "all"): cmd_score()
    if cmd in ("project", "all"): print(); cmd_project()
    if cmd in ("chart", "all"): cmd_chart()
