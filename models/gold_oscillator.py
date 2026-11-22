"""Gold Entry/Exit Oscillator — canonical engine for the "Asset Mgmt" project.

Mirrors the live Claude Sheet (Oscillator tab, revision 7, 19-Nov-2026) exactly:
per-indicator score = clamp(1 + 99*(x - cheap)/(rich - cheap), 1, 100)
weight = Impact x Severity x Reliability x Stability; blank inputs skipped and
weights re-normalised within each bucket; Oscillator = .35 V + .45 T + .20 F.

Files (all stored in the project under claude/):
  gold-inputs-monthly.csv   one row per month-end; columns i01..i30 = indicator values
                            (units as in SPEC below), plus raw helper columns.
  gold-scenarios.json       Bear/Base/Bull driver paths for the 5-yr projection.
  gold-score-log.csv        output: scores for every month with inputs (regenerated).

Usage:
  python3 gold_oscillator.py score     # recompute log, print latest + trend stats
  python3 gold_oscillator.py project   # 5-yr scenario score paths
  python3 gold_oscillator.py chart     # PNG: history + scenarios
  python3 gold_oscillator.py all
"""
import json, sys
import numpy as np, pandas as pd

INPUTS, SCEN, LOG = "gold-inputs-monthly.csv", "gold-scenarios.json", "gold-score-log.csv"
CHART = "gold_oscillator_history_and_outlook.png"
ATH_USD = 5589.38          # 28-Jan-2026 intraday all-time high
BUCKET_W = {"Valuation": 0.35, "Timing": 0.45, "Filter": 0.20}

# id: (name, bucket, impact, severity, reliability, stability, cheap->1, rich->100, unit)
SPEC = {
 1: ("US 10-yr real yield (TIPS)", "Timing", 5, 5, 1.0, 0.75, -0.5, 3.0, "%"),
 2: ("Expected Fed change next ~6m", "Timing", 5, 4, 1.0, 1.0, -100, 75, "bp"),
 3: ("Central-bank buying, last qtr", "Filter", 5, 4, 0.75, 0.75, 350, 50, "t"),
 4: ("Dollar index (DXY)", "Timing", 4, 4, 0.875, 1.0, 90, 110, "index"),
 5: ("Gold / US CPI index", "Valuation", 4, 4, 1.0, 1.0, 3, 16, "ratio"),
 6: ("Gold ETF flow, last month", "Timing", 4, 4, 0.875, 1.0, 50, -50, "t"),
 7: ("Gold / 200-day MA", "Timing", 3, 5, 1.0, 1.0, 0.85, 1.30, "ratio"),
 8: ("10-yr term premium (ACM)", "Valuation", 4, 3, 0.75, 0.75, 1.5, -0.5, "%"),
 9: ("CFTC managed-money net long", "Timing", 3, 4, 0.875, 1.0, 5, 40, "% OI"),
 10: ("Gold per $1T US M2", "Valuation", 3, 3, 0.75, 0.75, 85, 250, "$/T"),
 11: ("Gold / industry AISC", "Filter", 3, 3, 0.75, 1.0, 1.2, 3.2, "x"),
 12: ("Dow / Gold", "Valuation", 3, 3, 0.75, 1.0, 30, 2, "ratio"),
 13: ("USD/INR 12-mo change", "Timing", 3, 3, 1.0, 1.0, 8, -3, "%"),
 14: ("Yield curve 10y-2y", "Timing", 3, 3, 0.875, 0.75, -1.0, 2.5, "pp"),
 15: ("China physical premium", "Timing", 3, 3, 0.75, 1.0, 20, -20, "$/oz"),
 16: ("Gold share of CB reserves", "Filter", 4, 2, 0.75, 1.0, 10, 35, "%"),
 17: ("Monthly RSI(14)", "Timing", 2, 4, 0.75, 1.0, 30, 85, "RSI"),
 18: ("Geopolitical Risk Index", "Timing", 2, 4, 0.625, 0.75, 60, 250, "index"),
 19: ("Gold / 200-week MA", "Filter", 2, 4, 1.0, 1.0, 0.95, 1.8, "ratio"),
 20: ("US CPI YoY", "Filter", 3, 2, 0.5, 0.5, 6, 0, "%"),
 21: ("Gold share of global fin. assets", "Filter", 3, 2, 0.625, 0.75, 1, 6, "%"),
 22: ("Gold volatility (GVZ)", "Timing", 2, 3, 0.75, 1.0, 40, 14, "index"),
 23: ("GDX/GLD 3-mo change", "Timing", 2, 3, 0.75, 0.75, 15, -15, "%"),
 24: ("Distance from ATH", "Timing", 2, 3, 0.75, 1.0, -45, 0, "%"),
 25: ("Z-score vs 3-yr trend", "Timing", 2, 3, 0.75, 1.0, -2, 2.5, "z"),
 26: ("Hulbert Gold Newsletter Sentiment", "Timing", 2, 3, 0.75, 1.0, -20, 70, "%"),
 27: ("Gold / silver", "Timing", 2, 2, 0.625, 0.75, 45, 100, "ratio"),
 28: ("Gold miners Bullish % Index", "Timing", 1, 3, 0.5, 0.75, 5, 95, "%"),
 29: ("JM Bullion Fear & Greed", "Timing", 1, 2, 0.5, 0.5, 0, 100, "index"),
 30: ("Gold / Brent", "Timing", 1, 2, 0.5, 0.5, 10, 60, "ratio"),
}
COLS = [f"i{k:02d}" for k in SPEC]
WEIGHT = {k: v[2]*v[3]*v[4]*v[5] for k, v in SPEC.items()}
TOTAL_W = sum(WEIGHT.values())

def band(x):
    return ("STRONG BUY" if x <= 20 else "BUY" if x <= 35 else "ACCUMULATE SLOWLY" if x <= 50
            else "HOLD" if x <= 65 else "TRIM" if x <= 80 else "EXIT")

def ind_score(k, x):
    c, r = SPEC[k][6], SPEC[k][7]
    return float(np.clip(1 + 99*(x - c)/(r - c), 1, 100))

def score_row(row):
    """row: mapping with keys i01..i30 (NaN = missing). Returns dict."""
    out, cov = {}, 0.0
    for b in BUCKET_W:
        num = den = 0.0
        for k, v in SPEC.items():
            x = row.get(f"i{k:02d}", np.nan)
            if v[1] != b or x is None or pd.isna(x):
                continue
            num += WEIGHT[k]*ind_score(k, float(x)); den += WEIGHT[k]; cov += WEIGHT[k]
        out[b] = num/den if den else np.nan
    out["Oscillator"] = sum(BUCKET_W[b]*out[b] for b in BUCKET_W)
    out["Coverage"] = cov/TOTAL_W
    out["Signal"] = band(out["Oscillator"])
    if out["Filter"] >= 70 and out["Oscillator"] <= 35:
        out["Signal"] = "BUY VETOED - wait"
    return out

def fill_derived(df):
    """Fill price-derived indicators from gold_usd where blank (month-end conventions)."""
    g = df["gold_usd"]
    ma10, ma46 = g.rolling(10).mean(), g.rolling(46).mean()          # ~200-day, ~200-week
    df["i07"] = df["i07"].fillna((g/ma10).round(3))
    df["i19"] = df["i19"].fillna((g/ma46).round(3))
    ath = np.maximum(g.cummax(), 2075.0)
    ath[pd.PeriodIndex(df["month"], freq="M") >= pd.Period("2026-01", "M")] = ATH_USD
    df["i24"] = df["i24"].fillna(((g/ath - 1)*100).round(1))
    if "silver_usd" in df: df["i27"] = df["i27"].fillna((g/df["silver_usd"]).round(1))
    if "brent_usd" in df: df["i30"] = df["i30"].fillna((g/df["brent_usd"]).round(1))
    if "cpi_index" in df: df["i05"] = df["i05"].fillna((g/df["cpi_index"]).round(3))
    if "dow" in df: df["i12"] = df["i12"].fillna((df["dow"]/g).round(2))
    return df

def cmd_score():
    df = fill_derived(pd.read_csv(INPUTS))
    has = df[COLS].notna().sum(axis=1) >= 10
    rows = []
    for _, r in df[has].iterrows():
        s = score_row(r.to_dict())
        rows.append({"month": r["month"], "gold_usd": r["gold_usd"],
                     "oscillator": round(s["Oscillator"], 1), "valuation": round(s["Valuation"], 1),
                     "timing": round(s["Timing"], 1), "filter": round(s["Filter"], 1),
                     "coverage": round(s["Coverage"], 2), "signal": s["Signal"], "source": r["source"]})
    log = pd.DataFrame(rows); log.to_csv(LOG, index=False)
    last = log.iloc[-1]; prev = log.iloc[-2]
    log["year"] = log.month.str[:4]
    print("LATEST", last.to_dict())
    print(f"Change vs prior month: {last.oscillator - prev.oscillator:+.1f}")
    print("Yearly averages:", log.groupby("year").oscillator.mean().round(1).to_dict())
    print("12-mo avg:", log.oscillator.tail(12).mean().round(1),
          "| 3-mo slope/month:", round(np.polyfit(range(3), log.oscillator.tail(3), 1)[0], 1))
    i = log.oscillator.idxmax(); j = log.oscillator.idxmin()
    print(f"High {log.oscillator[i]} ({log.month[i]}), Low {log.oscillator[j]} ({log.month[j]})")
    # driver table for latest month
    r = df[has].iloc[-1]
    drv = []
    for k, v in SPEC.items():
        x = r.get(f"i{k:02d}")
        if pd.isna(x): continue
        sc = ind_score(k, float(x))
        drv.append((k, v[0], v[1], x, round(sc), round(WEIGHT[k]*(sc - 50)/TOTAL_W, 2)))
    drv.sort(key=lambda t: -abs(t[5]))
    print("\nTop drivers (pull vs 50, + = towards SELL):")
    for t in drv[:8]: print(f"  #{t[0]:>2} {t[1]:<34} {t[2]:<9} value={t[3]:<8} score={t[4]:>3} pull={t[5]:+.2f}")
    missing = [f"#{k} {SPEC[k][0]}" for k in SPEC if pd.isna(r.get(f'i{k:02d}'))]
    print("Missing inputs:", "; ".join(missing))
    return log

def cmd_project():
    sc = json.load(open(SCEN))
    years = sc["years"]; base_row = sc["start"]
    res = {}
    for name, s in sc["scenarios"].items():
        path = []
        for t in range(len(years)):
            row = dict(base_row) if t == 0 else {}
            if t > 0:
                g = s["gold_usd"][t]
                for key, vals in s["drivers"].items(): row[key] = vals[t]
                row["i05"] = g/(sc["cpi_index_now"]*(1+sc["cpi_growth"])**t)
                row["i10"] = g/(sc["m2_now"]*(1+s["m2_growth"])**t)
                row["i11"] = g/(sc["aisc_now"]*(1+sc["aisc_growth"])**t)
                row["i12"] = sc["dow_now"]*(1+sc["dow_growth"])**t/g
                row["i16"] = 0.14*(g/1800)/(0.86+0.14*g/1800)*100
                row["i24"] = (g/max(ATH_USD, max(s["gold_usd"][:t+1])) - 1)*100
                prev = s["gold_usd"][t-1]
                row["i07"] = g/((g+prev)/2*0.97 + 0.03*g)  # trend proxy: price vs ~10-mo average
                row["i19"] = g/np.mean(s["gold_usd"][max(0, t-4):t+1] + [base_row["gold_usd"]]*max(0, 4-t))
            path.append(round(score_row(row)["Oscillator"]))
        res[name] = {"prob": s["prob"], "score": path, "gold_usd": s["gold_usd"], "story": s["story"]}
    out = pd.DataFrame({n: v["score"] for n, v in res.items()}, index=years).T
    print(out.to_string())
    pw = sum(v["prob"]*np.array(v["score"]) for v in res.values())
    print("Prob-weighted score path:", np.round(pw).astype(int).tolist())
    json.dump(res, open("gold-projection-latest.json", "w"), indent=1)
    return res

def cmd_chart():
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    h = pd.read_csv(LOG); h["d"] = pd.to_datetime(h.month)
    res = json.load(open("gold-projection-latest.json")); sc = json.load(open(SCEN))
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
    ax2 = ax.twinx(); ax2.plot(h.d, h.gold_usd, color="#d4a017", lw=1, alpha=.7, label="Gold $/oz (rhs)")
    ax2.set_ylim(1000, 7000); ax2.set_ylabel("Gold $/oz")
    ax.set_ylim(0, 100); ax.set_ylabel("Oscillator (1 cheap … 100 rich)")
    ax.axvline(h.d.iloc[-1], color="#999", lw=.8)
    ax.set_title(f"Gold Entry/Exit Oscillator — history to {h.month.iloc[-1]} and 5-yr scenarios")
    a, b = ax.get_legend_handles_labels(); c2, d2 = ax2.get_legend_handles_labels()
    ax.legend(a+c2, b+d2, loc="upper left", fontsize=8)
    plt.tight_layout(); plt.savefig(CHART); print("saved", CHART)

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    if cmd in ("score", "all"): cmd_score()
    if cmd in ("project", "all"): print(); cmd_project()
    if cmd in ("chart", "all"): cmd_chart()
