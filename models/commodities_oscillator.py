"""Silver & Commodities Entry/Exit Oscillator (v1, indicative) — "Asset Mgmt" project.

Same engine as gold_oscillator.py / sector_oscillator.py:
  per-indicator score = clamp(1 + 99*(x - cheap)/(rich - cheap), 1, 100)   (high = rich / headwind)
  weight W = Impact x Severity x Reliability x Stability; blank inputs skipped and weights
  re-normalised inside each bucket; a bucket resting on ONE live indicator moves only half-way
  from 50 (THIN_SHRINK). Oscillator = sum(bucket weight x bucket score) over buckets with data.
Commodities: SILVER (full model), BRENT and COPPER (indicative, MCX-futures access only).

Files (project, under claude/):
  commodities-config.json          commodities, indicators, anchors, weights (editable)
  commodities-inputs-monthly.csv   one row per month-end of raw inputs (wide format)
  commodities-scenarios.json       silver Bear/Base/Bull 5-yr paths (tied to gold-scenarios.json)
  commodities-score-log.csv        output (regenerated on every run)

Price-derived inputs are computed here from the monthly price history, never typed in:
  px_ma10  price / mean of last 10 month-ends (~200-DMA)     px_ma46  price / mean of last 46 (~200-WMA)
  rsi14    Wilder RSI(14) on month-end closes                chg12    12-month % change
  dist_ath % below the all-time high in the config            silver_inr_vs_36m  INR price vs 36-m avg

Usage: python3 commodities_oscillator.py [score|drivers|project|chart|all] [KEY ...]
"""
import json, sys, math
import numpy as np, pandas as pd

CONFIG, INPUTS, SCEN, LOG = ("commodities-config.json", "commodities-inputs-monthly.csv",
                             "commodities-scenarios.json", "commodities-score-log.csv")
CHART = "commodities_oscillator_history_and_outlook.png"
THIN_SHRINK = 0.5
MIN_LIVE = 6          # a month is scored for a commodity only with >= this many live indicators

def num(v):
    try:
        f = float(v); return None if math.isnan(f) else f
    except (TypeError, ValueError):
        return None

def band(x):
    return ("STRONG BUY" if x <= 20 else "BUY" if x <= 35 else "ACCUMULATE" if x <= 50
            else "HOLD" if x <= 65 else "TRIM" if x <= 80 else "EXIT")

def ind_score(c, r, x):
    return float(np.clip(1 + 99*(x - c)/(r - c), 1, 100))

# ---------- derived price columns ----------
def rsi(series, n=14):
    d = series.diff()
    up = d.clip(lower=0).ewm(alpha=1/n, adjust=False, min_periods=n).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1/n, adjust=False, min_periods=n).mean()
    return 100 - 100/(1 + up/dn)

def add_derived(df, cfg):
    for c in cfg["commodities"]:
        k, p = c["key"].lower(), df[c["price_col"]]
        df[f"{k}_px_ma10"] = (p/p.rolling(10).mean()).round(3)
        df[f"{k}_px_ma46"] = (p/p.rolling(46).mean()).round(3)
        df[f"{k}_rsi14"] = rsi(p).round(1)
        df[f"{k}_chg12"] = ((p/p.shift(12) - 1)*100).round(1)
        if c.get("ath"):
            df[f"{k}_dist_ath"] = ((p/np.maximum(c["ath"], p.cummax()) - 1)*100).round(1)
    inr = df["silver_usd"]*df["usdinr"]
    df["silver_inr_vs_36m"] = ((inr/inr.rolling(36).mean() - 1)*100).round(1)
    return df

# derive key -> function(row, commodity_key) ; None if an input is blank
def _col(name):
    return lambda r, k: num(r.get(name))
def _own(suffix):
    return lambda r, k: num(r.get(f"{k.lower()}_{suffix}"))
def _ratio(a, b, mult=1.0):
    def f(r, k):
        x, y = num(r.get(a)), num(r.get(b))
        return None if x is None or y is None or y == 0 else mult*x/y
    return f

DERIVE = {
    "gsr": _ratio("gold_usd", "silver_usd"),
    "silver_real": _ratio("silver_usd", "cpi_index", 100),
    "silver_inr_vs_36m": _col("silver_inr_vs_36m"),
    "imp_gold_v": _col("imp_gold_v"),
    "tips10": _col("tips10"), "fed_exp_bp": _col("fed_exp_bp"), "dxy": _col("dxy"),
    "usdinr_12m": _col("usdinr_12m"), "pmi_global": _col("pmi_global"),
    "px_ma10": _own("px_ma10"), "px_ma46": _own("px_ma46"), "rsi14": _own("rsi14"),
    "chg12": _own("chg12"), "dist_ath": _own("dist_ath"),
    "cftc_net_pct": _own("cftc_net_pct"), "etf_flow_moz": _own("etf_flow_moz"),
    "balance": lambda r, k: num(r.get({"SILVER": "silver_balance_moz", "COPPER": "copper_balance_kt"}.get(k, ""))),
    "balance_next": lambda r, k: num(r.get("copper_balance_next_kt")),
    "brent_real": _ratio("brent_usd", "cpi_index", 100),
    "gold_brent": _ratio("gold_usd", "brent_usd"),
    "curve_m1m12": _col("brent_curve_m1m12"),
    "stock_chg_mbd": _col("oil_stock_chg_mbd"),
    "copper_real": _ratio("copper_usd_t", "cpi_index"),
    "copper_gold": lambda r, k: (None if num(r.get("copper_usd_t")) is None or num(r.get("gold_usd")) is None
                                 else 1000*(num(r["copper_usd_t"])/2204.62)/num(r["gold_usd"])),
}

def score_row(c, row):
    """Score one commodity on one row. Returns dict or None if too few live inputs."""
    k = c["key"]; out = {"drivers": []}; live = 0; w_all = w_live = 0.0
    bsc = {}
    for b in c["buckets"]:
        num_ = den = 0.0; n_b = 0; drv = []
        for ind in c["indicators"]:
            if ind["bucket"] != b: continue
            w = ind["I"]*ind["S"]*ind["R"]*ind["St"]; w_all += w
            x = DERIVE[ind["derive"]](row, k)
            if x is None: continue
            s = ind_score(ind["cheap"], ind["rich"], x)
            num_ += w*s; den += w; n_b += 1; w_live += w
            drv.append({**ind, "value": round(x, 3), "score": s, "w": w})
        live += n_b
        if not den: continue
        sc = num_/den; thin = n_b == 1
        if thin: sc = 50 + (sc - 50)*THIN_SHRINK
        bsc[b] = sc
        for d in drv:
            d["pull_b"] = (d["w"]/den)*(d["score"] - 50)*(THIN_SHRINK if thin else 1)
        out["drivers"] += drv
    if live < MIN_LIVE or not bsc: return None
    wsum = sum(c["buckets"][b] for b in bsc)
    osc = sum(c["buckets"][b]*bsc[b] for b in bsc)/wsum
    for d in out["drivers"]:   # contribution to the oscillator, points vs 50 (+ = towards SELL)
        d["pull"] = round(c["buckets"][d["bucket"]]/wsum*d["pull_b"], 2)
    sig = band(osc)
    if bsc.get("Filter", 0) >= 70 and osc <= 35: sig = "BUY VETOED - wait"
    out.update({"Oscillator": osc, "buckets": bsc, "signal": sig, "live": live,
                "n_ind": len(c["indicators"]), "coverage": w_live/w_all})
    return out

def load():
    cfg = json.load(open(CONFIG))
    df = add_derived(pd.read_csv(INPUTS, dtype={"month": str}), cfg)
    return cfg, df

def cmd_score(keys, verbose_drivers=True):
    cfg, df = load(); rows = []
    for c in cfg["commodities"]:
        for _, r in df.iterrows():
            s = score_row(c, r.to_dict())
            if s is None: continue
            b = s["buckets"]
            rows.append({"month": r["month"], "commodity": c["key"], "price_usd": r[c["price_col"]],
                         "oscillator": round(s["Oscillator"], 1),
                         "valuation": round(b["Valuation"], 1) if "Valuation" in b else None,
                         "timing": round(b["Timing"], 1) if "Timing" in b else None,
                         "filter": round(b["Filter"], 1) if "Filter" in b else None,
                         "coverage": round(s["coverage"], 2), "live": f"{s['live']}/{s['n_ind']}",
                         "signal": s["signal"], "source": str(r["source"])[:60]})
    log = pd.DataFrame(rows).sort_values(["commodity", "month"]).reset_index(drop=True)
    log.to_csv(LOG, index=False)
    last_m = df.month.max()
    print(f"COMMODITIES OSCILLATOR {last_m} (1 = cheap/buy, 100 = rich/sell) — v1, indicative")
    print(log[log.month == last_m][["commodity", "price_usd", "oscillator", "valuation", "timing", "filter",
                                    "coverage", "live", "signal"]].to_string(index=False))
    for c in cfg["commodities"]:
        if keys and c["key"] not in keys: continue
        h = log[log.commodity == c["key"]].reset_index(drop=True)
        print(f"\n=== {c['name']} ({c['key']}) — {c['status']} | access: {c['access']}")
        if len(h) >= 2:
            print(f"Change vs prior month: {h.oscillator.iloc[-1] - h.oscillator.iloc[-2]:+.1f}")
            yr = h.assign(y=h.month.str[:4]).groupby("y").oscillator.mean().round(1).to_dict()
            print("Yearly averages:", yr)
            print("12-mo avg:", round(h.oscillator.tail(12).mean(), 1),
                  "| 3-mo slope/month:", round(np.polyfit(range(min(3, len(h))), h.oscillator.tail(3), 1)[0], 1) if len(h) >= 3 else "n/a")
            i, j = h.oscillator.idxmax(), h.oscillator.idxmin()
            print(f"High {h.oscillator[i]} ({h.month[i]}), Low {h.oscillator[j]} ({h.month[j]}), months scored {len(h)}")
            print("Last 12 months:", dict(zip(h.month.tail(12), h.oscillator.tail(12))))
        else:
            print("History: current month only (no back-fill yet).")
        if verbose_drivers:
            s = score_row(c, df[df.month == last_m].iloc[0].to_dict())
            print("Drivers (pull = points vs 50 on the oscillator, + = towards SELL):")
            for d in sorted(s["drivers"], key=lambda d: -abs(d["pull"])):
                print(f"  {d['id']:<5} {d['name'][:58]:<58} {d['bucket'][:5]:<5} {d['type'][:20]:<20} "
                      f"value={d['value']:<9} {d['unit']:<6} score={d['score']:>5.0f} pull={d['pull']:+.2f}")
            miss = [f"{i['id']} {i['name'][:40]}" for i in c["indicators"]
                    if i["id"] not in {d["id"] for d in s["drivers"]}]
            print("Missing inputs:", "; ".join(miss) if miss else "none")
    return log

def cmd_project():
    """Silver 5-yr scenarios: price paths tied to gold-scenarios.json gold paths / an assumed GSR path."""
    cfg, df = load(); sc = json.load(open(SCEN))
    c = next(x for x in cfg["commodities"] if x["key"] == "SILVER")
    now = df[df.month == df.month.max()].iloc[0].to_dict()
    hist_inr = list((df.silver_usd*df.usdinr).dropna().tail(36))
    hist_px = list(df.silver_usd.dropna())
    res = {}
    for name, s in sc["scenarios"].items():
        path, prices = [], []
        for t in range(len(sc["years"])):
            if t == 0:
                row = now; px = now["silver_usd"]
            else:
                g = s["gold_usd"][t]; px = g/s["gsr"][t]
                fx = sc["usdinr_now"]*(1 + s["inr_depr"])**t
                cpi = sc["cpi_index_now"]*(1 + sc["cpi_growth"])**t
                prev = prices[-1]
                ann = [hist_px[-1]] + prices[1:] + [px]          # annual points incl. today
                inr_pts = [p*sc["usdinr_now"]*(1 + s["inr_depr"])**i for i, p in enumerate(ann)]
                row = {"gold_usd": g, "silver_usd": px, "cpi_index": cpi, "usdinr": fx,
                       "silver_px_ma10": px/(0.5*px + 0.5*prev),            # trend proxy vs ~10-mo average
                       "silver_px_ma46": px/np.mean(ann[-4:]),
                       "silver_inr_vs_36m": (px*fx/np.mean(inr_pts[-4:-1]) - 1)*100,
                       "silver_chg12": (px/prev - 1)*100,
                       "silver_dist_ath": (px/max(c["ath"], max(ann)) - 1)*100}
                for key, vals in s["drivers"].items(): row[key] = vals[t]
            prices.append(px)
            path.append(round(score_row(c, row)["Oscillator"]))
        res[name] = {"prob": s["prob"], "score": path, "silver_usd": [round(p, 1) for p in prices], "story": s["story"]}
    out = pd.DataFrame({n: v["score"] for n, v in res.items()}, index=sc["years"]).T
    print("\nSILVER 5-yr scenario score paths (prices = gold-scenarios.json gold path / GSR path):")
    print(out.to_string())
    print(pd.DataFrame({n: v["silver_usd"] for n, v in res.items()}, index=sc["years"]).T.to_string())
    pw = sum(v["prob"]*np.array(v["score"]) for v in res.values())
    pwp = sum(v["prob"]*v["silver_usd"][-1] for v in res.values())
    print("Prob-weighted score path:", np.round(pw).astype(int).tolist(), f"| prob-weighted exit ${pwp:.1f}/oz")
    json.dump(res, open("commodities-projection-latest.json", "w"), indent=1)
    return res

def cmd_chart():
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    log = pd.read_csv(LOG); log["d"] = pd.to_datetime(log.month)
    res = json.load(open("commodities-projection-latest.json")); sc = json.load(open(SCEN))
    px = pd.to_datetime([f"20{y[-2:]}-11" for y in sc["years"]])
    fig, ax = plt.subplots(figsize=(12, 6), dpi=150)
    for lo, hi, col, l in [(0,20,"#1a7f37","Strong buy"),(20,35,"#4caf50","Buy"),(35,50,"#c8e6c9","Accumulate"),
                           (50,65,"#eeeeee","Hold"),(65,80,"#ffcc80","Trim"),(80,100,"#ef6c00","Exit")]:
        ax.axhspan(lo, hi, color=col, alpha=.35, lw=0)
        ax.text(px[-1] + pd.Timedelta(days=40), (lo+hi)/2, l, va="center", fontsize=8, color="#444")
    colors = {"SILVER": "#1f3b73", "BRENT": "#6d4c41", "COPPER": "#c26a1b"}
    for k, h in log.groupby("commodity"):
        if len(h) > 1:
            ax.plot(h.d, h.oscillator, color=colors[k], lw=2.2 if k == "SILVER" else 1.3, label=f"{k.title()} oscillator")
        else:
            ax.plot(h.d, h.oscillator, "D", color=colors[k], ms=7, label=f"{k.title()} (current month only)")
    sc_col = {"Bear": "#c62828", "Base": "#555555", "Bull": "#b8860b"}
    for n, v in res.items():
        ax.plot(px, v["score"], ls="--", marker="o", ms=4, color=sc_col[n], label=f"Silver {n} ({int(v['prob']*100)}%)")
    s = log[log.commodity == "SILVER"]
    ax2 = ax.twinx(); ax2.plot(s.d, s.price_usd, color="#9e9e9e", lw=1, alpha=.8, label="Silver $/oz (rhs)")
    ax2.set_ylim(0, 140); ax2.set_ylabel("Silver $/oz")
    ax.set_ylim(0, 100); ax.set_ylabel("Oscillator (1 cheap … 100 rich)")
    ax.axvline(s.d.iloc[-1], color="#999", lw=.8)
    ax.set_title(f"Silver & commodities Entry/Exit Oscillator (v1, indicative) — to {log.month.max()} and silver 5-yr scenarios")
    a, b = ax.get_legend_handles_labels(); c2, d2 = ax2.get_legend_handles_labels()
    ax.legend(a+c2, b+d2, loc="upper left", fontsize=7.5)
    plt.tight_layout(); plt.savefig(CHART); print("saved", CHART)

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    keys = sys.argv[2:]
    if cmd in ("score", "drivers", "all"): cmd_score(keys)
    if cmd in ("project", "all"): cmd_project()
    if cmd in ("chart", "all"): cmd_chart()
