#!/usr/bin/env python3
"""
Market Cap Rotation Model - point-in-time backtest (pure Python, no dependencies).

Inputs (put in ./data, any of the niftyindices.com "Historical Data" CSV exports work):
  tri_large.csv  tri_mid.csv  tri_small.csv   -> Date + Total Returns Index
  pe_large.csv   pe_mid.csv   pe_small.csv    -> Date + P/E (+ P/B optional)
  Large = NIFTY 50, Mid = NIFTY MIDCAP 150, Small = NIFTY SMALLCAP 250.

What it does, month by month, using only data known at each month-end:
  A  relative valuation gap   (premium vs Nifty against its rolling median premium)
  B  own-history valuation    (P/E vs rolling median of its own P/E)
  C  relative momentum        (6m relative return + ratio vs ~200-DMA, here 10-month avg)
  D  earnings growth gap      (YoY trailing-EPS growth, EPS = TRI-proxy price / P/E)
  E  rates                    (RBI stance table below; 10y yield and FII terms not available historically)
  F  flows                    (not available before 2018 recategorisation -> 0 in backtest)
Scores -> weights with target = base * (1 + k*score), applied to NEXT month's returns.

Usage: python3 rotation_backtest.py [data_dir] [--json out.json]
"""
import csv, json, math, os, re, sys, statistics
from datetime import date, datetime

# ---------------------------------------------------------------- RBI stance
# Approximate policy-rate regimes (+1 cutting, -1 hiking, 0 on hold). Month granularity.
RBI_REGIMES = [
    ((2005, 10), (2008, 8), -1),
    ((2008, 10), (2009, 4), +1),
    ((2010, 3), (2011, 10), -1),
    ((2012, 4), (2013, 5), +1),
    ((2013, 9), (2014, 1), -1),
    ((2015, 1), (2017, 8), +1),
    ((2018, 6), (2018, 8), -1),
    ((2019, 2), (2020, 5), +1),
    ((2022, 5), (2023, 2), -1),
    ((2025, 2), (2025, 12), +1),
    ((2026, 10), (2026, 12), -1),
]
STANCE_MEMORY = 6  # a move keeps influencing for 6 months after the last change


def rbi_stance(y, m):
    idx = y * 12 + m
    for (y0, m0), (y1, m1), s in RBI_REGIMES:
        a, b = y0 * 12 + m0, y1 * 12 + m1 + STANCE_MEMORY
        if a <= idx <= b:
            return s
    return 0


# ---------------------------------------------------------------- loading
DATE_FMTS = ["%d %b %Y", "%d-%b-%Y", "%d-%m-%Y", "%Y-%m-%d", "%d/%m/%Y", "%d-%b-%y", "%b %d, %Y", "%d %B %Y"]


def parse_date(s):
    s = s.strip().strip('"')
    for f in DATE_FMTS:
        try:
            return datetime.strptime(s, f).date()
        except ValueError:
            pass
    return None


def to_float(s):
    s = (s or "").replace(",", "").strip().strip('"')
    if s in ("", "-", "NA", "N/A"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def load_series(path, want):
    """want: list of header substrings tried in order (case-insensitive). Returns {date: value}."""
    with open(path, newline="", encoding="utf-8-sig") as fh:
        rows = list(csv.reader(fh))
    hdr_i = next(i for i, r in enumerate(rows) if any("date" in c.lower() for c in r))
    hdr = [c.strip().lower() for c in rows[hdr_i]]
    dcol = next(i for i, c in enumerate(hdr) if "date" in c)
    vcol = None
    for w in want:
        for i, c in enumerate(hdr):
            if w in c.replace(" ", ""):
                vcol = i
                break
        if vcol is not None:
            break
    if vcol is None:
        raise SystemExit(f"{path}: none of {want} in header {hdr}")
    out = {}
    for r in rows[hdr_i + 1:]:
        if len(r) <= max(dcol, vcol):
            continue
        d, v = parse_date(r[dcol]), to_float(r[vcol])
        if d and v is not None and v > 0:
            out[d] = v
    return out


def month_end(series):
    """Last observation in each calendar month -> {(y,m): value}."""
    out = {}
    for d in sorted(series):
        out[(d.year, d.month)] = series[d]
    return out


# ---------------------------------------------------------------- model
W = dict(A=0.30, B=0.15, C=0.20, D=0.15, E=0.10, F=0.10)
BETA = dict(mid=0.75, small=1.0)


def _corr(x, y):
    mx, my = sum(x) / len(x), sum(y) / len(y)
    sx = math.sqrt(sum((a - mx) ** 2 for a in x))
    sy = math.sqrt(sum((b - my) ** 2 for b in y))
    return sum((a - mx) * (b - my) for a, b in zip(x, y)) / (sx * sy) if sx and sy else 0.0


if not hasattr(statistics, "correlation"):
    statistics.correlation = _corr


def clamp(x, a=-2.0, b=2.0):
    return max(a, min(b, x))


def rolling_median(vals, i, lookback, min_n):
    window = [v for v in vals[max(0, i - lookback + 1): i + 1] if v is not None]
    return statistics.median(window) if len(window) >= min_n else None


PE_MAX = 80.0  # index P/E above this (or negative/missing) = earnings collapse, treat as unknown


def build(data, lookback=120, min_hist=36, metric="pb"):
    months = sorted(set(data["tri_large"]) & set(data["tri_mid"]) & set(data["tri_small"]))
    n = len(months)
    cleanpe = lambda v: v if (v is not None and 0 < v <= PE_MAX) else None
    pe = {k: [cleanpe(data["pe_" + k].get(m)) for m in months] for k in ("large", "mid", "small")}
    pb = {k: [data.get("pb_" + k, {}).get(m) for m in months] for k in ("large", "mid", "small")}
    val = pb if metric == "pb" else pe
    tri = {k: [data["tri_" + k][m] for m in months] for k in ("large", "mid", "small")}
    eps = {k: [(tri[k][i] / pe[k][i]) if pe[k][i] else None for i in range(n)] for k in tri}
    prem = {k: [(val[k][i] / val["large"][i] - 1) if val[k][i] and val["large"][i] else None
                for i in range(n)] for k in ("mid", "small")}
    rows = []
    for i, m in enumerate(months):
        if i < 12:
            continue
        row = {"month": f"{m[0]}-{m[1]:02d}", "pillars": {}, "live": {}}
        for k in ("mid", "small"):
            norm_prem = rolling_median(prem[k], i, lookback, min_hist)
            own_med = rolling_median(val[k], i, lookback, min_hist)
            live = prem[k][i] is not None and norm_prem is not None and own_med is not None
            row["live"][k] = live
            if not live:
                row["pillars"][k] = dict(A=0.0, B=0.0, C=0.0, D=0.0, E=0.0, F=0.0)
                continue
            A = clamp(-(prem[k][i] - norm_prem) * 100 / 10)
            B = clamp(-(val[k][i] / own_med - 1) * 100 / 10)
            rel6 = (tri[k][i] / tri[k][i - 6] - tri["large"][i] / tri["large"][i - 6]) * 100
            ratio = [tri[k][j] / tri["large"][j] for j in range(i - 9, i + 1)]
            above = 1 if ratio[-1] > sum(ratio) / len(ratio) else -1
            C = (clamp(rel6 / 7.5) + above) / 2
            g = lambda kk: (eps[kk][i] / eps[kk][i - 12] - 1) * 100 if eps[kk][i] and eps[kk][i - 12] else None
            gs, gl = g(k), g("large")
            D = clamp((gs - gl) / 10) if gs is not None and gl is not None else 0.0
            E = clamp(rbi_stance(*m)) * BETA[k]
            row["pillars"][k] = dict(A=A, B=B, C=C, D=D, E=E, F=0.0)
        if row["live"]["mid"]:
            rows.append((i, row))
    return months, tri, rows


def run(months, tri, rows, base=(55, 28, 17), k=0.4, weights=None, use=("A", "B", "C", "D", "E"),
        band=0.0, step=1.0, small_cap=30.0, cost_bps=10, guard=True):
    weights = weights or W
    wsum = sum(weights[p] for p in use) or 1
    bL, bM, bS = base
    cur = None
    nav, bench, navs, turnover = 1.0, 1.0, [], 0.0
    hist = []
    for idx, (i, row) in enumerate(rows):
        if i + 1 >= len(months):
            break
        sc = {}
        for seg in ("mid", "small"):
            p = row["pillars"][seg]
            # renormalise so a dropped pillar does not shrink the score range
            sc[seg] = sum(p[x] * weights[x] for x in use) / wsum
        tM = max(0.0, min(100.0, bM * (1 + k * sc["mid"])))
        tS = max(0.0, min(small_cap, bS * (1 + k * sc["small"])))
        if guard:
            pS = row["pillars"]["small"]
            if row["live"]["small"] and pS["A"] <= -2.0 and pS["C"] < 0:  # premium >= ~20pp above normal and falling
                tS = min(tS, bS * 0.2)
        target = [100 - tM - tS, tM, tS]
        if cur is None:
            new = target
        else:
            gap = max(abs(a - b) for a, b in zip(target, cur))
            new = [c + step * (t - c) for c, t in zip(cur, target)] if gap >= band else cur
        if cur is not None:
            turnover += sum(abs(a - b) for a, b in zip(new, cur)) / 2 / 100
        cost = (sum(abs(a - b) for a, b in zip(new, cur)) / 2 / 100 * cost_bps / 1e4) if cur else 0
        r = [tri[s][i + 1] / tri[s][i] - 1 for s in ("large", "mid", "small")]
        port = sum(w / 100 * x for w, x in zip(new, r)) - cost
        b = sum(w / 100 * x for w, x in zip(base, r))
        # drift weights with returns
        grown = [w * (1 + x) for w, x in zip(new, r)]
        tot = sum(grown)
        cur = [g / tot * 100 for g in grown]
        nav *= 1 + port
        bench *= 1 + b
        navs.append((months[i + 1], nav, bench))
        hist.append(dict(month=row["month"], mid=round(sc["mid"], 3), small=round(sc["small"], 3),
                         w=[round(x, 1) for x in new]))
    return navs, hist, turnover


def stats(series):
    if len(series) < 2:
        return {}
    yrs = len(series) / 12
    v = [s for s in series]
    rets = [v[i] / v[i - 1] - 1 for i in range(1, len(v))]
    cagr = (v[-1] / 1.0) ** (1 / yrs) - 1
    vol = statistics.pstdev(rets) * math.sqrt(12)
    peak, mdd = -1, 0
    for x in v:
        peak = max(peak, x)
        mdd = min(mdd, x / peak - 1)
    return dict(cagr=cagr, vol=vol, mdd=mdd, sharpe_like=(cagr / vol if vol else 0))


def fixed(months, tri, start_i, end_i, w):
    nav, out = 1.0, []
    for i in range(start_i, end_i):
        r = [tri[s][i + 1] / tri[s][i] - 1 for s in ("large", "mid", "small")]
        nav *= 1 + sum(a / 100 * b for a, b in zip(w, r))  # monthly rebalanced
        out.append(nav)
    return out


def forward_ic(months, tri, rows, horizon=12):
    """Rank-free information check: correlation of score with next-12m relative return."""
    res = {}
    for seg in ("mid", "small"):
        xs, ys = [], []
        for i, row in rows:
            if i + horizon >= len(months) or not row["live"][seg]:
                continue
            p = row["pillars"][seg]
            s = sum(p[x] * W[x] for x in "ABCDE") / sum(W[x] for x in "ABCDE")
            rel = tri[seg][i + horizon] / tri[seg][i] - tri["large"][i + horizon] / tri["large"][i]
            xs.append(s)
            ys.append(rel)
        if len(xs) > 24:
            res[seg] = dict(n=len(xs), corr=statistics.correlation(xs, ys))
        for pil in "ABCDE":
            xs2, ys2 = [], []
            for i, row in rows:
                if i + horizon >= len(months) or not row["live"][seg]:
                    continue
                xs2.append(row["pillars"][seg][pil])
                ys2.append(tri[seg][i + horizon] / tri[seg][i] - tri["large"][i + horizon] / tri["large"][i])
            if len(set(xs2)) > 2:
                res[f"{seg}_{pil}"] = round(statistics.correlation(xs2, ys2), 3)
    return res


def main():
    args, skip = [], False
    for a in sys.argv[1:]:
        if skip: skip = False; continue
        if a in ("--json", "--metric"): skip = True; continue
        if not a.startswith("--"): args.append(a)
    ddir = args[0] if args else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "models", "nse-history")
    out_json = sys.argv[sys.argv.index("--json") + 1] if "--json" in sys.argv else None
    import glob
    data = {}

    def load_all(prefix, want):
        files = sorted(glob.glob(os.path.join(ddir, prefix + "*.csv")))
        if not files:
            raise SystemExit(f"Missing {prefix}*.csv in {ddir}")
        merged = {}
        for f in files:  # chunks may overlap; later files win
            merged.update(load_series(f, want))
        return month_end(merged)

    for seg in ("large", "mid", "small"):
        data["tri_" + seg] = load_all(f"tri_{seg}", ["totalreturnsindex", "totalreturn", "tri", "close"])
        data["pe_" + seg] = load_all(f"pe_{seg}", ["p/e", "pe"])
        try:
            data["pb_" + seg] = load_all(f"pe_{seg}", ["p/b", "pb"])
        except SystemExit:
            data["pb_" + seg] = {}
    metric = sys.argv[sys.argv.index("--metric") + 1] if "--metric" in sys.argv else "pb"
    months, tri, rows = build(data, metric=metric)
    small_start = next((r["month"] for _, r in rows if r["live"]["small"]), None)
    if not rows:
        raise SystemExit("Not enough overlapping history (need 3+ years of P/E before the first signal).")
    first_i, last_i = rows[0][0], len(months) - 1
    report = {"period": [rows[0][1]["month"], f"{months[-1][0]}-{months[-1][1]:02d}"], "runs": {},
              "metric": metric, "small_signals_from": small_start}

    def add(name, navs, turnover=None):
        st = stats([n for _, n, _ in navs]) if isinstance(navs[0], tuple) else stats(navs)
        if turnover is not None:
            st["turnover_per_yr"] = turnover / (len(navs) / 12)
        report["runs"][name] = st

    for name, w in [("Fixed 55/28/17", (55, 28, 17)), ("Market-ish 70/20/10", (70, 20, 10)),
                    ("All Nifty 50", (100, 0, 0)), ("All Midcap 150", (0, 100, 0)), ("All Smallcap 250", (0, 0, 100))]:
        add(name, fixed(months, tri, first_i, last_i, w))
    navs, hist, to = run(months, tri, rows)
    add("Model (A-E, monthly)", navs, to)
    navs_b, hist_b, to_b = run(months, tri, rows, band=5.0, step=1 / 3)
    add("Model (A-E, 5pp band, 1/3 steps)", navs_b, to_b)
    for drop in "ABCDE":
        use = tuple(x for x in "ABCDE" if x != drop)
        n, _, t = run(months, tri, rows, use=use)
        add(f"Model without {drop}", n, t)
    for kk in (0.2, 0.6, 0.8):
        n, _, t = run(months, tri, rows, k=kk)
        add(f"Model k={kk}", n, t)
    n, _, t = run(months, tri, rows, guard=False)
    add("Model, no guardrail", n, t)
    # sub-periods
    split = next((j for j, (i, r) in enumerate(rows) if r["month"] >= "2017-01"), None)
    if split:
        for label, sl in (("pre-2017", rows[:split]), ("2017+", rows[split:])):
            n, _, t = run(months, tri, sl)
            report["runs"][f"Model {label}"] = stats([x for _, x, _ in n])
            report["runs"][f"Fixed 55/28/17 {label}"] = stats([x for _, _, x in n])
    report["forward_12m_corr"] = forward_ic(months, tri, rows)
    report["history"] = hist
    report["nav"] = [dict(m=f"{m[0]}-{m[1]:02d}", model=round(a, 4), fixed=round(b, 4)) for m, a, b in navs_b]
    w = max(len(k) for k in report["runs"])
    print(f"Backtest {report['period'][0]} -> {report['period'][1]}  valuation={metric}  smallcap signals from {small_start}")
    print(f"{'run':<{w}}  {'CAGR':>7} {'Vol':>7} {'MaxDD':>8} {'CAGR/Vol':>8} {'Turn/yr':>8}")
    for kname, st in report["runs"].items():
        print(f"{kname:<{w}}  {st['cagr']*100:6.2f}% {st['vol']*100:6.2f}% {st['mdd']*100:7.2f}% "
              f"{st['sharpe_like']:8.2f} {st.get('turnover_per_yr', float('nan'))*100:7.1f}%")
    print("Score vs next-12m relative return correlation:", json.dumps(report["forward_12m_corr"]))
    if out_json:
        with open(out_json, "w") as fh:
            json.dump(report, fh, indent=1)


if __name__ == "__main__":
    main()
