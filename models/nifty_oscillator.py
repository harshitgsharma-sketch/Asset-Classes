"""Nifty 50 Entry/Exit Oscillator — canonical engine for the "Asset Mgmt" project.

Same method as gold_oscillator.py:
  per-indicator score = clamp(1 + 99*(x - cheap)/(rich - cheap), 1, 100)
  weight = Impact x Severity x Reliability x Stability; blank inputs skipped and
  weights re-normalised within each bucket; Oscillator = .40 V + .40 T + .20 F.
  High score = expensive / headwind; low score = cheap / tailwind.

Files (all stored in the project under claude/):
  nifty-inputs-monthly.csv  one row per month-end; raw columns + i01..i40 (units as in SPEC).
                            Price/rate-derived indicators are computed here when blank.
  nifty-scenarios.json      Bear/Base/Bull paths for the 5-yr projection.
  nifty-score-log.csv       output: scores for every month with inputs (regenerated).

Usage:
  python3 nifty_oscillator.py score     # recompute log, print latest + trend + drivers
  python3 nifty_oscillator.py fair      # PE-band fair value + entry/exit rule check
  python3 nifty_oscillator.py project   # 5-yr scenario score paths
  python3 nifty_oscillator.py chart     # PNG: history + scenarios
  python3 nifty_oscillator.py trend     # yearly table (avg/high/low/year-end Nifty) + last 12 months
  python3 nifty_oscillator.py sens      # month-end score range if Nifty closes -5%..+5% from latest
  python3 nifty_oscillator.py all
"""
import json, sys
import numpy as np, pandas as pd

INPUTS, SCEN, LOG = "nifty-inputs-monthly.csv", "nifty-scenarios.json", "nifty-score-log.csv"
CHART = "nifty_oscillator_history_and_outlook.png"
ATHS = {"2021-10": 18604.45, "2024-09": 26277.35, "2026-01": 26373.20}   # intraday ATHs, effective from month
BUCKET_W = {"Valuation": 0.40, "Timing": 0.40, "Filter": 0.20}
FV_PE = {"Low": 16, "Mid": 20, "High": 24}

# id: (name, bucket, type, impact, severity, reliability, stability, cheap->1, rich->100, unit)
SPEC = {
 1: ("BEER (10y G-sec / earnings yield)", "Valuation", "Leading", 5, 4, 1.0, 1.0, 1.0, 1.9, "x"),
 2: ("Nifty trailing PE", "Valuation", "Leading", 5, 5, 1.0, 0.75, 14, 28, "x"),
 3: ("Expected RBI repo change ~6m", "Timing", "Leading", 5, 4, 0.875, 1.0, -75, 75, "bp"),
 4: ("Nifty / 200-day MA", "Timing", "Leading", 3, 5, 1.0, 1.0, 0.88, 1.15, "ratio"),
 5: ("10y G-sec 6-m change", "Timing", "Coincident", 4, 4, 0.875, 1.0, -75, 75, "bp"),
 6: ("12-m forward PE", "Valuation", "Leading", 5, 4, 0.875, 0.75, 13, 23, "x"),
 7: ("EPS revisions 3-m (FY+1)", "Timing", "Leading", 5, 4, 0.875, 0.75, 4, -4, "%"),
 8: ("India VIX", "Timing", "Coincident", 3, 4, 0.875, 1.0, 25, 10, "index"),
 9: ("% Nifty 500 above 200-DMA", "Timing", "Leading", 3, 4, 0.875, 1.0, 15, 85, "%"),
 10: ("FII net flow, 3 m", "Timing", "Coincident", 4, 4, 0.75, 0.75, -80, 60, "Rs '000 cr"),
 11: ("Nifty / 200-week MA", "Filter", "Lagging", 2, 4, 1.0, 1.0, 0.95, 1.60, "ratio"),
 12: ("Dollar index (DXY)", "Timing", "Coincident", 3, 3, 0.875, 1.0, 90, 110, "index"),
 13: ("Brent crude", "Timing", "Coincident", 4, 3, 0.75, 0.75, 55, 110, "$/bbl"),
 14: ("India-US 10y spread", "Timing", "Leading", 3, 3, 0.75, 1.0, 3.5, 1.5, "pp"),
 15: ("FII ownership (Nifty 500)", "Valuation", "Leading", 3, 3, 0.75, 1.0, 15, 23, "%"),
 16: ("Midcap 150 PE / Nifty PE", "Timing", "Leading", 3, 3, 0.75, 1.0, 0.9, 1.8, "ratio"),
 17: ("India fwd-PE premium to MSCI EM", "Valuation", "Leading", 3, 3, 0.75, 1.0, 15, 100, "%"),
 18: ("US high-yield OAS", "Timing", "Leading", 3, 3, 0.75, 1.0, 6.0, 2.5, "%"),
 19: ("Monthly RSI(14)", "Timing", "Leading", 2, 4, 0.75, 1.0, 35, 80, "RSI"),
 20: ("India CPI YoY", "Timing", "Coincident", 3, 3, 0.875, 0.75, 2, 7, "%"),
 21: ("Market cap / GDP", "Valuation", "Leading", 4, 3, 0.625, 0.75, 60, 150, "%"),
 22: ("Shiller CAPE", "Valuation", "Leading", 3, 3, 0.625, 1.0, 16, 36, "x"),
 23: ("Nifty price-to-book", "Valuation", "Leading", 3, 3, 0.75, 0.75, 2.2, 4.2, "x"),
 24: ("Equity MF net inflow, 3-m avg", "Timing", "Coincident", 3, 3, 0.75, 0.75, 8, 45, "Rs '000 cr"),
 25: ("System liquidity (LAF % NDTL)", "Timing", "Leading", 3, 3, 0.75, 0.75, 1.5, -1.0, "%"),
 26: ("Nifty EPS growth, TTM YoY", "Filter", "Lagging", 3, 3, 0.75, 0.75, 25, -5, "%"),
 27: ("Real GDP growth YoY", "Filter", "Lagging", 3, 3, 0.75, 0.75, 8.5, 4.5, "%"),
 28: ("Manufacturing PMI", "Timing", "Leading", 2, 3, 0.75, 1.0, 59, 49, "index"),
 29: ("Nifty 3-yr CAGR", "Filter", "Lagging", 2, 3, 0.75, 1.0, 0, 25, "%"),
 30: ("Distance from ATH", "Timing", "Coincident", 2, 3, 0.75, 1.0, -30, 0, "%"),
 31: ("Rupee REER (40-ccy)", "Valuation", "Leading", 2, 3, 0.75, 1.0, 90, 108, "index"),
 32: ("Primary issuance, 3 m", "Timing", "Leading", 3, 3, 0.625, 0.75, 15, 90, "Rs '000 cr"),
 33: ("MTF book YoY", "Timing", "Leading", 3, 3, 0.625, 0.75, -10, 60, "%"),
 34: ("Nifty dividend yield", "Valuation", "Leading", 2, 3, 0.75, 0.75, 2.0, 1.0, "%"),
 35: ("Corporate profit / GDP", "Filter", "Lagging", 3, 2, 0.625, 0.75, 2, 6, "%"),
 36: ("Bank credit growth YoY", "Timing", "Coincident", 2, 3, 0.625, 0.75, 18, 8, "%"),
 37: ("Promoter holding chg, 4 qtrs", "Filter", "Lagging", 3, 2, 0.625, 0.75, 1.0, -2.0, "pp"),
 38: ("Bank Nifty / Nifty 3-m rel.", "Timing", "Leading", 2, 3, 0.625, 0.75, 6, -6, "%"),
 39: ("Nifty put-call ratio (OI)", "Timing", "Coincident", 2, 3, 0.625, 0.5, 0.7, 1.4, "ratio"),
 40: ("Nifty / Gold (Rs/10 g parity)", "Valuation", "Leading", 2, 2, 0.625, 0.75, 0.15, 0.50, "ratio"),
}
COLS = [f"i{k:02d}" for k in SPEC]
WEIGHT = {k: v[3]*v[4]*v[5]*v[6] for k, v in SPEC.items()}
TOTAL_W = sum(WEIGHT.values())

def band(x):
    return ("STRONG BUY" if x <= 20 else "BUY" if x <= 35 else "ACCUMULATE" if x <= 50
            else "HOLD" if x <= 65 else "TRIM" if x <= 80 else "EXIT")

def ind_score(k, x):
    c, r = SPEC[k][7], SPEC[k][8]
    return float(np.clip(1 + 99*(x - c)/(r - c), 1, 100))

def score_row(row):
    """row: mapping with keys i01..i40 (NaN = missing). Returns dict incl. veto logic."""
    out, cov = {}, 0.0
    for b in BUCKET_W:
        num = den = 0.0
        for k, v in SPEC.items():
            x = row.get(f"i{k:02d}", np.nan)
            if v[1] != b or x is None or pd.isna(x):
                continue
            num += WEIGHT[k]*ind_score(k, float(x)); den += WEIGHT[k]; cov += WEIGHT[k]
        out[b] = num/den if den else np.nan
    osc = sum(BUCKET_W[b]*out[b] for b in BUCKET_W)
    out["Oscillator"], out["Coverage"], out["Signal"] = osc, cov/TOTAL_W, band(osc)
    rev, dma, br = row.get("i07", np.nan), row.get("i04", np.nan), row.get("i09", np.nan)
    if osc <= 35 and (out["Filter"] >= 70 or (not pd.isna(rev) and rev <= -3)):
        out["Signal"] = "BUY VETOED - wait (falling knife)"
    if osc >= 66 and not pd.isna(dma) and dma >= 1.12 and (pd.isna(br) or br >= 80):
        out["Signal"] = "TRIM (euphoria rule)" if osc <= 80 else out["Signal"]
    return out

def rsi(close, n=14):
    d = close.diff(); up = d.clip(lower=0); dn = -d.clip(upper=0)
    au = up.ewm(alpha=1/n, adjust=False).mean(); ad = dn.ewm(alpha=1/n, adjust=False).mean()
    return 100 - 100/(1 + au/ad)

def fill_derived(df):
    """Compute price/rate-derived indicators where blank (month-end conventions)."""
    p, e = df["nifty"], df["eps_ttm"]
    pe = p/e
    def fill(col, s): df[col] = df[col].fillna(s.round(3))
    fill("i02", pe)
    fill("i01", df["gsec10"]*pe/100)                                    # 10y yield / (100/PE)
    fill("i04", p/p.rolling(10).mean())                                 # ~200-day MA
    fill("i05", (df["gsec10"] - df["gsec10"].shift(6))*100)
    fill("i10", df["fii_net_kcr"].rolling(3).sum())
    fill("i11", p/p.rolling(46).mean())                                 # ~200-week MA
    fill("i12", df["dxy"]); fill("i13", df["brent_usd"])
    fill("i14", df["gsec10"] - df["us10y"])
    fill("i19", rsi(p))
    fill("i24", df["mf_net_kcr"].rolling(3).mean())
    fill("i26", (e/e.shift(12) - 1)*100)
    fill("i29", ((p/p.shift(36))**(1/3) - 1)*100)
    ath = p.cummax().copy()
    for m, v in ATHS.items():
        ath[df["month"] >= m] = np.maximum(ath[df["month"] >= m], v)
    fill("i30", (p/ath - 1)*100)
    gold_inr_10g = df["gold_usd"]/31.1035*10*df["usdinr"]
    fill("i40", p/gold_inr_10g)
    return df

def load():
    return fill_derived(pd.read_csv(INPUTS, dtype={"month": str}))

def cmd_score():
    df = load()
    has = df[COLS].notna().sum(axis=1) >= 12
    rows = []
    for _, r in df[has].iterrows():
        s = score_row(r.to_dict())
        rows.append({"month": r["month"], "nifty": r["nifty"], "oscillator": round(s["Oscillator"], 1),
                     "valuation": round(s["Valuation"], 1), "timing": round(s["Timing"], 1),
                     "filter": round(s["Filter"], 1), "coverage": round(s["Coverage"], 2),
                     "signal": s["Signal"], "source": r["source"]})
    log = pd.DataFrame(rows); log.to_csv(LOG, index=False)
    last, prev = log.iloc[-1], log.iloc[-2]
    log["year"] = log.month.str[:4]
    print("LATEST", last.to_dict())
    print(f"Change vs prior month: {last.oscillator - prev.oscillator:+.1f}")
    a, b = df[has].iloc[-2].to_dict(), df[has].iloc[-1].to_dict()
    common = [c for c in COLS if not pd.isna(a.get(c)) and not pd.isna(b.get(c))]
    la = score_row({c: a[c] for c in common})["Oscillator"]; lb = score_row({c: b[c] for c in common})["Oscillator"]
    added = [c for c in COLS if pd.isna(a.get(c)) and not pd.isna(b.get(c))]
    print(f"  like-for-like change (same {len(common)} indicators): {lb - la:+.1f} | "
          f"from coverage change: {(last.oscillator - prev.oscillator) - (lb - la):+.1f} (newly filled: {', '.join(added) or 'none'})")
    print("Yearly averages:", log.groupby("year").oscillator.mean().round(1).to_dict())
    print("12-mo avg:", log.oscillator.tail(12).mean().round(1),
          "| 3-mo slope/month:", round(np.polyfit(range(3), log.oscillator.tail(3), 1)[0], 1))
    i, j = log.oscillator.idxmax(), log.oscillator.idxmin()
    print(f"High {log.oscillator[i]} ({log.month[i]}), Low {log.oscillator[j]} ({log.month[j]})")
    fwd = log.nifty.shift(-12)/log.nifty - 1
    ok = fwd.notna()
    if ok.sum() > 12:
        print("In-sample corr(score, next-12m Nifty return):", round(np.corrcoef(log.oscillator[ok], fwd[ok])[0, 1], 2))
    r = df[has].iloc[-1]
    drv = []
    for k, v in SPEC.items():
        x = r.get(f"i{k:02d}")
        if pd.isna(x): continue
        sc = ind_score(k, float(x))
        drv.append((k, v[0], v[1][0], v[2], round(float(x), 2), round(sc), round(WEIGHT[k]*(sc - 50)/TOTAL_W, 2)))
    drv.sort(key=lambda t: -t[6])
    print("\nTop pulls towards SELL:")
    for t in drv[:5]: print(f"  #{t[0]:>2} {t[1]:<34} {t[2]} {t[3]:<10} value={t[4]:<9} score={t[5]:>3} pull={t[6]:+.2f}")
    print("Top pulls towards BUY:")
    for t in drv[::-1][:5]: print(f"  #{t[0]:>2} {t[1]:<34} {t[2]} {t[3]:<10} value={t[4]:<9} score={t[5]:>3} pull={t[6]:+.2f}")
    missing = [f"#{k} {SPEC[k][0]}" for k in SPEC if pd.isna(r.get(f'i{k:02d}'))]
    print("Missing inputs:", "; ".join(missing))
    return log

def cmd_fair():
    df = load(); r = df.iloc[-1]
    sc = json.load(open(SCEN)); fwd_eps = sc["fwd12m_eps_now"]
    fv = {k: round(fwd_eps*v) for k, v in FV_PE.items()}
    p = r["nifty"]
    print(f"Fair value on 12-m fwd EPS {fwd_eps}: Low {fv['Low']:,} / Mid {fv['Mid']:,} / High {fv['High']:,}")
    print(f"Nifty {p:,.0f} = {100*(p/fv['Mid']-1):+.1f}% vs Mid; BEER-implied fair PE = {100/r['gsec10']/1.0:.1f}x at BEER 1.0, "
          f"{100*1.45/r['gsec10']:.1f}x at BEER 1.45 (mid-range)")
    log = pd.read_csv(LOG); osc = log.oscillator.iloc[-1]
    print("Entry rules: T1 Osc<=35:", osc <= 35, "| T2 Nifty<=FV Mid:", p <= fv["Mid"],
          "| T3 RBI pivot (exp repo chg <= -25bp):", r["i03"] <= -25,
          "| Accelerate (Nifty<=FV Low*1.05 or VIX>=25):", p <= fv["Low"]*1.05 or r["i08"] >= 25)
    print("Exit rules: Osc>=66 two reviews:", (log.oscillator.tail(2) >= 66).all(), "| Nifty>=FV High:", p >= fv["High"],
          "| BEER>=1.75:", r["i01"] >= 1.75, "| MTF YoY>=60 & Osc>=60:", r.get("i33", 0) >= 60 and osc >= 60)
    return fv

def cmd_project():
    sc = json.load(open(SCEN)); years = sc["years"]; base = dict(sc["start"])
    hist = {y: v for y, v in sc["nifty_history_nov"].items()}
    res = {}
    for name, s in sc["scenarios"].items():
        path, prices = [], []
        for t in range(len(years)):
            row = dict(base)
            if t > 0:
                for key, vals in s["drivers"].items(): row[key] = vals[t]
                p, e = s["nifty"][t], s["eps"][t]; pe = p/e; prev = s["nifty"][t-1]
                g_next = s["eps_growth"][min(t+1, len(years)-1)]
                row["i02"] = pe; row["i01"] = row["gsec10"]*pe/100; row["i06"] = pe/(1+g_next/100)
                row["i23"] = 0.143*pe; row["i34"] = 27.3/pe
                row["i26"] = (e/s["eps"][t-1] - 1)*100
                row["i05"] = (row["gsec10"] - s["drivers"]["gsec10"][t-1])*100/2
                row["i14"] = row["gsec10"] - row["us10y"]
                row["i04"] = p/((p+prev)/2*0.97 + 0.03*p)
                seq = [hist["2023"], hist["2024"], hist["2025"]] + s["nifty"][:t+1]
                row["i11"] = p/np.mean(seq[-4:])
                row["i29"] = ((p/seq[-4])**(1/3) - 1)*100
                row["i19"] = float(np.clip(50 + 1.0*(p/prev - 1)*100, 25, 85))
                row["i30"] = (p/max(26373.2, max(s["nifty"][:t+1])) - 1)*100
                gold_inr = sc["gold_inr_10g_now"]*(1+sc["gold_inr_growth"])**t
                row["i40"] = p/gold_inr
            path.append(round(score_row(row)["Oscillator"]))
        cagr = ((s["nifty"][-1]/s["nifty"][0])**(1/5) - 1)*100
        res[name] = {"prob": s["prob"], "score": path, "nifty": s["nifty"], "eps": s["eps"],
                     "exit_pe": round(s["nifty"][-1]/s["eps"][-1], 1), "price_cagr": round(cagr, 1), "story": s["story"]}
    out = pd.DataFrame({n: v["score"] for n, v in res.items()}, index=years).T
    print(out.to_string())
    pw = sum(v["prob"]*np.array(v["score"]) for v in res.values())
    pn = sum(v["prob"]*np.array(v["nifty"]) for v in res.values())
    print("Prob-weighted score path:", np.round(pw).astype(int).tolist())
    print("Prob-weighted Nifty path:", np.round(pn, -1).astype(int).tolist(),
          f"| price CAGR {((pn[-1]/pn[0])**0.2-1)*100:.1f}% (+~1.3%/yr dividends)")
    for n, v in res.items(): print(f"  {n}: exit {v['nifty'][-1]:,} (PE {v['exit_pe']}), price CAGR {v['price_cagr']}%")
    json.dump(res, open("nifty-projection-latest.json", "w"), indent=1)
    return res

def cmd_trend():
    l = pd.read_csv(LOG); l["year"] = l.month.str[:4]
    g = l.groupby("year").agg(avg=("oscillator", "mean"), high=("oscillator", "max"), low=("oscillator", "min"),
                              nifty_end=("nifty", "last"), months=("month", "count")).round(1)
    print("Yearly trend:\n" + g.to_string())
    print("\nLast 12 months:\n" + l[["month", "nifty", "oscillator", "valuation", "timing", "filter", "signal"]].tail(12).to_string(index=False))
    return g

def cmd_sens():
    base = pd.read_csv(INPUTS, dtype={"month": str}); i = base.index[-1]; p0 = base.loc[i, "nifty"]
    print(f"Month-end score if Nifty closes at (latest {p0:,.0f}, other inputs fixed):")
    for f in [-0.05, -0.025, 0, 0.025, 0.05]:
        df = base.copy(); lvl = p0*(1+f); df.loc[i, "nifty"] = lvl
        for c in ("i06", "i23"):                       # price-proportional ratios entered directly
            if not pd.isna(base.loc[i, c]): df.loc[i, c] = base.loc[i, c]*(1+f)
        if not pd.isna(base.loc[i, "i34"]): df.loc[i, "i34"] = base.loc[i, "i34"]/(1+f)
        s = score_row(fill_derived(df).iloc[-1].to_dict())
        print(f"  {f:+.1%}  Nifty {lvl:>7,.0f}: Osc {s['Oscillator']:.1f} (V {s['Valuation']:.1f} T {s['Timing']:.1f} F {s['Filter']:.1f}) {s['Signal']}")

def cmd_chart():
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    h = pd.read_csv(LOG); h["d"] = pd.to_datetime(h.month)
    res = json.load(open("nifty-projection-latest.json")); sc = json.load(open(SCEN))
    px = pd.to_datetime([f"20{y[-2:]}-11" for y in sc["years"]])
    fig, ax = plt.subplots(figsize=(12, 6), dpi=150)
    for lo, hi, c, l in [(0,20,"#1a7f37","Strong buy"),(20,35,"#4caf50","Buy"),(35,50,"#c8e6c9","Accumulate"),
                         (50,65,"#eeeeee","Hold"),(65,80,"#ffcc80","Trim"),(80,100,"#ef6c00","Exit")]:
        ax.axhspan(lo, hi, color=c, alpha=.35, lw=0)
        ax.text(px[-1] + pd.Timedelta(days=40), (lo+hi)/2, l, va="center", fontsize=8, color="#444")
    ax.plot(h.d, h.oscillator, color="#1f3b73", lw=2.2, label="Oscillator (month-end)")
    ax.plot(h.d, h.oscillator.rolling(12).mean(), color="#1f3b73", lw=1, ls=":", label="12-mo average")
    col = {"Bear": "#c62828", "Base": "#555555", "Bull": "#2e7d32"}
    for n, v in res.items():
        ax.plot(px, v["score"], ls="--", marker="o", ms=4, color=col[n], label=f"{n} ({int(v['prob']*100)}%)")
    ax2 = ax.twinx(); ax2.plot(h.d, h.nifty, color="#8e44ad", lw=1, alpha=.7, label="Nifty 50 (rhs)")
    for n, v in res.items(): ax2.plot(px, v["nifty"], color=col[n], lw=.8, alpha=.5)
    ax2.set_ylim(10000, 65000); ax2.set_ylabel("Nifty 50")
    ax.set_ylim(0, 100); ax.set_ylabel("Oscillator (1 cheap … 100 rich)")
    ax.axvline(h.d.iloc[-1], color="#999", lw=.8)
    ax.set_title(f"Nifty 50 Entry/Exit Oscillator — history to {h.month.iloc[-1]} and 5-yr scenarios")
    a, b = ax.get_legend_handles_labels(); c2, d2 = ax2.get_legend_handles_labels()
    ax.legend(a+c2, b+d2, loc="upper left", fontsize=8)
    plt.tight_layout(); plt.savefig(CHART); print("saved", CHART)

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    if cmd in ("score", "all"): cmd_score()
    if cmd in ("trend", "all"): print(); cmd_trend()
    if cmd in ("sens", "all"): print(); cmd_sens()
    if cmd in ("fair", "all"): print(); cmd_fair()
    if cmd in ("project", "all"): print(); cmd_project()
    if cmd in ("chart", "all"): cmd_chart()
