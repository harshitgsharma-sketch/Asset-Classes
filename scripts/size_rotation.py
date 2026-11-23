#!/usr/bin/env python3
"""Market-cap (size) rotation: latest reading + back-test, for the Indian equities "Market cap" view.

Reads the NSE month-end history in models/nse-history (Nifty 50, Midcap 150, Smallcap 250 total
return; Nifty 50, Midcap 100, Smallcap 100 P/E and P/B) and reuses the engine in
research/market-cap-rotation/rotation_backtest.py, so the board and the research page agree.
Writes data/size_rotation.json; build_signals.py attaches it to data/signals.json.

Deterministic: same CSVs, same output. Run: python3 -I scripts/size_rotation.py
"""
import datetime
import glob
import json
import math
import os
import statistics
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "research", "market-cap-rotation"))
import rotation_backtest as bt  # noqa: E402

HIST = os.path.join(ROOT, "models", "nse-history")
OUT = os.path.join(ROOT, "data", "size_rotation.json")
BASE = (55, 28, 17)          # balanced strategic split, large / mid / small
K, BAND, STEP = 0.8, 5.0, 1 / 3   # tilt strength, act-only-if-gap band (pp), share of gap moved per month


def load():
    data = {}

    def la(prefix, want):
        merged = {}
        for f in sorted(glob.glob(os.path.join(HIST, prefix + ".csv"))):
            merged.update(bt.load_series(f, want))
        return bt.month_end(merged)
    for s in ("large", "mid", "small"):
        data["tri_" + s] = la(f"tri_{s}", ["totalreturnsindex"])
        data["pe_" + s] = la(f"pe_{s}", ["p/e"])
        data["pb_" + s] = la(f"pe_{s}", ["p/b"])
    return data


def r(x, d=2):
    return None if x is None or (isinstance(x, float) and math.isnan(x)) else round(x, d)


def main():
    data = load()
    months, tri, rows = bt.build(data, metric="pb")
    ym = lambda m: f"{m[0]}-{m[1]:02d}"

    # ---- headline back-test (same settings as the research page) ----
    navs, hist, turn = bt.run(months, tri, rows, base=BASE, k=K, band=BAND, step=STEP)
    model = bt.stats([a for _, a, _ in navs])
    fixed = bt.stats([b for _, _, b in navs])
    first_i, last_i = rows[0][0], len(months) - 1
    singles = {name: bt.stats(bt.fixed(months, tri, first_i, last_i, w))
               for name, w in (("Nifty 50", (100, 0, 0)), ("Midcap 150", (0, 100, 0)), ("Smallcap 250", (0, 0, 100)))}
    split = next(j for j, (i, rr) in enumerate(rows) if rr["month"] >= "2017-01")
    halves = {}
    for label, part in (("2008-2016", rows[:split]), ("2017-2026", rows[split:])):
        n, _, _ = bt.run(months, tri, part, base=BASE, k=K, band=BAND, step=STEP)
        a, b = bt.stats([x for _, x, _ in n]), bt.stats([y for _, _, y in n])
        halves[label] = {"model_cagr": r(a["cagr"] * 100), "fixed_cagr": r(b["cagr"] * 100),
                         "excess": r((a["cagr"] - b["cagr"]) * 100), "model_mdd": r(a["mdd"] * 100), "fixed_mdd": r(b["mdd"] * 100)}
    ic = bt.forward_ic(months, tri, rows)

    # calendar-year excess return, model minus fixed
    years, prev = {}, (1.0, 1.0)
    for (y, m), a, b in navs:
        years.setdefault(y, [prev[0], prev[1], a, b])
        years[y][2], years[y][3] = a, b
        prev = (a, b)
    yx = [[y, r((v[2] / v[0] - v[3] / v[1]) * 100, 1)] for y, v in sorted(years.items())]

    # ---- latest reading ----
    i_last, last = rows[-1]
    W = {p: bt.W[p] for p in "ABCDE"}
    wsum = sum(W.values())
    seg_score = {s: sum(last["pillars"][s][p] * W[p] for p in W) / wsum for s in ("mid", "small")}
    tM = max(0.0, min(100.0, BASE[1] * (1 + K * seg_score["mid"])))
    tS = max(0.0, min(30.0, BASE[2] * (1 + K * seg_score["small"])))
    target = [r(100 - tM - tS, 1), r(tM, 1), r(tS, 1)]
    holding = hist[-1]["w"] if hist else None

    # valuation context: P/B premium of mid/small proxies over Nifty 50, now vs 10-yr median
    def series(k):
        return [data[k].get(m) for m in months]
    val = {}
    for s in ("mid", "small"):
        prem = [(a / b - 1) * 100 if a and b else None for a, b in zip(series("pb_" + s), series("pb_large"))]
        win = [p for p in prem[-120:] if p is not None]
        val[s] = {"pb": r(data["pb_" + s].get(months[-1])), "pe": r(data["pe_" + s].get(months[-1])),
                  "pb_premium": r(prem[-1], 1), "pb_premium_med10": r(statistics.median(win), 1) if win else None}
    val["large"] = {"pb": r(data["pb_large"].get(months[-1])), "pe": r(data["pe_large"].get(months[-1]))}

    # relative-strength history: Midcap 150 and Smallcap 250 total return divided by Nifty 50, rebased to 100
    base_i = next(i for i, m in enumerate(months) if tri["mid"][i] and tri["small"][i])
    ratio = [[ym(months[i]),
              r(tri["mid"][i] / tri["large"][i] / (tri["mid"][base_i] / tri["large"][base_i]) * 100, 1),
              r(tri["small"][i] / tri["large"][i] / (tri["small"][base_i] / tri["large"][base_i]) * 100, 1)]
             for i in range(base_i, len(months))]

    out = {
        "built_at": datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat(),
        "asof": ym(months[-1]),
        "base": list(BASE),
        "settings": {"k": K, "band_pp": BAND, "step": round(STEP, 3), "valuation": "P/B",
                     "weights": {p: W[p] for p in W}, "small_signals_from": next((rr["month"] for _, rr in rows if rr["live"]["small"]), None)},
        "scores": {s: r(seg_score[s]) for s in seg_score},
        "pillars": {s: {p: r(last["pillars"][s][p]) for p in "ABCDE"} for s in ("mid", "small")},
        "target": target,
        "holding": holding,
        "valuation": val,
        "ratio": ratio,
        "backtest": {
            "period": [hist[0]["month"], ym(months[-1])] if hist else None,
            "model": {k: r(v * 100) for k, v in model.items() if k != "sharpe_like"},
            "fixed": {k: r(v * 100) for k, v in fixed.items() if k != "sharpe_like"},
            "singles": {n: {"cagr": r(s["cagr"] * 100), "mdd": r(s["mdd"] * 100)} for n, s in singles.items()},
            "turnover_pct_yr": r(turn / (len(navs) / 12) * 100, 1),
            "halves": halves,
            "corr12": {"mid": r(ic.get("mid", {}).get("corr")), "small": r(ic.get("small", {}).get("corr")),
                       "mid_valuation_gap": ic.get("mid_A")},
            "years": yx,
            "nav": [[ym(m), r(a, 3), r(b, 3)] for m, a, b in navs],
            "weights": [[h["month"], *h["w"]] for h in hist],
        },
        "notes": ["Valuation uses Nifty Midcap 100 and Smallcap 100 P/B as proxies: NSE publishes Midcap 150 and Smallcap 250 valuations only from Apr 2016.",
                  "Point-in-time: rolling 10-year medians, weights applied to the next month's return, 0.1% cost per unit of turnover, no taxes.",
                  "Not investment advice."],
        "research": "research/market-cap-rotation/",
    }
    json.dump(out, open(OUT, "w"), separators=(",", ":"), allow_nan=False)
    print(f"size rotation {out['asof']}: mid {out['scores']['mid']} small {out['scores']['small']} target {target} "
          f"| back-test {out['backtest']['model']['cagr']}% vs {out['backtest']['fixed']['cagr']}% -> {os.path.relpath(OUT, ROOT)}")


if __name__ == "__main__":
    main()
